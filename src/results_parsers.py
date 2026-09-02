"""
Parsers for official results formats beyond the classic Hy-Tek section layout
(`src/hytek_parser.py`). Both return the same shape as `parse_section`:
(info, [HytekEntry], problems) — so `entries_to_raw_rows` and the ingest
pipeline are shared, and malformed input refuses loudly.

Formats:

- **lap_times** (e.g. PASA meet-program style): entry line
  `place Name, First M  age  TEAM  final`, followed by four INDIVIDUAL lap
  times. Laps are converted to cumulative splits; the lap sum must equal the
  final time to the hundredth or the entry is a problem, which is the built-in
  transcription check.

- **hs_championship** (CIF/NCS style): entry line
  `place First Last  GRADE  School  final  [tag]` with GRADE in
  {FR, SO, JR, SR, --}, followed by
  `s50   c100 (lap2)   c150 (lap3)   c200 (lap4)` — cumulative with lap times
  in parentheses. Every parenthesized lap must equal the difference of its
  cumulatives and the last cumulative must equal the final time, so each row
  is internally redundant and self-verifying. Grades are NOT ages: entries get
  `age = None` (the pipeline's age gate then excludes them from the primary
  population) and the grade is carried in the tags.
"""

from __future__ import annotations

import re

from .hytek_parser import HytekEntry

_TIME = r"(?:\d+:)?\d{2}\.\d{2}"


def _seconds(t: str) -> float:
    if ":" in t:
        m, s = t.split(":")
        return 60 * int(m) + float(s)
    return float(t)


def _fmt_cum(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds - 60 * m
    return f"{m}:{s:05.2f}" if m else f"{s:.2f}"


_LAP_HEADER = re.compile(r"^#?\d*\s*(Boys|Girls|Men|Women)\s+.*?(\d{2,4}\s+Yard\s+\w+)")
_LAP_ENTRY = re.compile(
    rf"^\s*(\*?\d+)\s+(.+?)\s{{2,}}(\d{{1,2}})\s{{2,}}(\S+)\s{{2,}}({_TIME})\s*$")
_LAP_SPLITS = re.compile(rf"^\s+({_TIME})\s+({_TIME})\s+({_TIME})\s+({_TIME})\s*$")

_HS_ENTRY = re.compile(
    rf"^\s*(\*?\d+)\s+(.+?)\s{{2,}}(FR|SO|JR|SR|--)\s{{2,}}(.+?)\s{{2,}}({_TIME})(?:\s{{2,}}(\S+))?\s*$")
_HS_SPLITS = re.compile(
    rf"^\s+({_TIME})\s+({_TIME})\s+\(({_TIME})\)\s+({_TIME})\s+\(({_TIME})\)\s+({_TIME})\s+\(({_TIME})\)\s*$")


def _event_info(lines: "list[str]") -> dict:
    for ln in lines[:4]:
        m = _LAP_HEADER.match(ln.strip())
        if m:
            return {"sex": {"Men": "Boys", "Women": "Girls"}.get(m.group(1), m.group(1)),
                    "event": re.sub(r"\s+", " ", m.group(2))}
    return {}


def parse_lap_section(text: str) -> "tuple[dict, list, list]":
    """Parse the lap-times format. See module docstring."""
    lines = text.splitlines()
    info = _event_info(lines)
    entries, problems = [], []
    pending = None
    for ln in lines:
        em = _LAP_ENTRY.match(ln)
        if em:
            if pending is not None:
                problems.append(f"{pending.name}: entry without split line")
            place, name, age, team, final = em.groups()
            pending = HytekEntry(place=place.lstrip("*"), name=name.strip(),
                                 age=int(age), team=team, seed="", final=final,
                                 tags="")
            continue
        sm = _LAP_SPLITS.match(ln)
        if sm and pending is not None:
            laps = [_seconds(x) for x in sm.groups()]
            cum, run = [], 0.0
            for lap in laps:
                run += lap
                cum.append(_fmt_cum(round(run, 2)))
            if abs(run - _seconds(pending.final)) > 0.011:
                problems.append(
                    f"{pending.name}: laps sum to {run:.2f} != final "
                    f"{pending.final} — transcription or timing error")
            else:
                pending.splits.extend(cum)
                entries.append(pending)
            pending = None
    if pending is not None:
        problems.append(f"{pending.name}: entry without split line")
    if not entries:
        problems.append("no entries parsed")
    return info, entries, problems


def parse_hs_champ_section(text: str) -> "tuple[dict, list, list]":
    """Parse the CIF/NCS championship format. See module docstring."""
    lines = text.splitlines()
    info = _event_info(lines) or {}
    if not info:
        for ln in lines[:4]:
            m = re.match(r"^\s*(Boys|Girls)\s+(\d{2,4}\s+Yard\s+\w+)", ln.strip())
            if m:
                info = {"sex": m.group(1), "event": m.group(2)}
                break
    entries, problems = [], []
    pending = None
    for ln in lines:
        em = _HS_ENTRY.match(ln)
        if em:
            if pending is not None:
                problems.append(f"{pending.name}: entry without split line")
            place, name, grade, school, final, tag = em.groups()
            tags = f"grade {grade}" + (f"; {tag}" if tag else "")
            pending = HytekEntry(place=place.lstrip("*"), name=name.strip(),
                                 age=None, team=school.strip(), seed="",
                                 final=final, tags=tags)
            continue
        sm = _HS_SPLITS.match(ln)
        if sm and pending is not None:
            s50, c100, lap2, c150, lap3, c200, lap4 = sm.groups()
            ok = True
            checks = [(c100, s50, lap2), (c150, c100, lap3), (c200, c150, lap4)]
            for cum, prev, lap in checks:
                if abs(_seconds(cum) - _seconds(prev) - _seconds(lap)) > 0.011:
                    problems.append(
                        f"{pending.name}: {cum} != {prev} + {lap} — "
                        f"internal split inconsistency")
                    ok = False
            if abs(_seconds(c200) - _seconds(pending.final)) > 0.011:
                problems.append(
                    f"{pending.name}: last cumulative {c200} != final "
                    f"{pending.final}")
                ok = False
            if ok:
                pending.splits.extend([s50, c100, c150, c200])
                entries.append(pending)
            pending = None
    if pending is not None:
        problems.append(f"{pending.name}: entry without split line")
    if not entries:
        problems.append("no entries parsed")
    return info, entries, problems
