"""
Parser for Hy-Tek MEET MANAGER results text (the format official meet results
are published in, e.g. on pacswim.org).

An event section looks like:

    Boys 200 Yard Freestyle
    ===============================================================
                  1:58.59  SRII
                  2:08.39  SOPN
        Name                     Age Team              Seed     Finals
    ===============================================================
      1 Wu, Songrui               16 PLS-PC          1:36.64    1:37.01 SRII
           22.72    47.02  1:11.97  1:37.01
      2 Dangol, Aasish            16 AAA-PC          1:42.77    1:42.63 SRII
           24.33    50.11  1:16.19  1:42.63
     -- Ly, Nathan A              14 PLS-PC          1:50.11        DFS

Each entry is a result line (place or --, "Last, First", age, team, seed,
final, optional standard tags) followed, for completed swims, by a line of
CUMULATIVE splits at 50/100/150/200. DFS/DQ/NS entries have no splits and are
reported but not converted into races.

This is deliberately a parser for the one section shape this project ingests
(4x50 individual events). It refuses, loudly, anything it does not recognize,
because silently mis-parsed race data is worse than no data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Leading indent up to 8 spaces and a single-space name-age gap both occur in
# print-to-PDF renderings of the same official files (long names squeeze the
# column); names never contain digits, so the non-greedy name safely stops at
# the age either way.
RESULT_LINE = re.compile(
    r"^\s{0,8}(?P<place>\d{1,3}|--)\s+"
    r"(?P<name>[A-Za-z' .,()-]+?)\s+"
    r"(?P<age>\d{1,2})\s+"
    r"(?P<team>[A-Z0-9-]+)\s+"
    r"(?:(?P<seed>(?:\d{1,2}:)?\d{2}\.\d{2}|NT)\s+)?"  # seed column is optional
    r"(?P<final>(?:\d{1,2}:)?\d{2}\.\d{2}|DFS|DQ|NS|SCR)"
    r"(?P<tags>[A-Za-z+ ]*?)(?:\s+(?P<points>\d{1,3}(?:\.\d+)?))?\s*$"
)

_T = r"(?:\d{1,2}:)?\d{2}\.\d{2}"
#: A split line is 1-4 cumulative times, each optionally followed by the lap
#: time in parentheses (Hy-Tek prints "47.74 (24.61)"); nothing else.
_SPLIT_LINE_SHAPE = re.compile(rf"^\s+(?:{_T}(?:\s*\({_T}\))?\s*)+$")
_SPLIT_TOKEN = re.compile(rf"({_T})(?:\s*\(({_T})\))?")


def _seconds(t: str) -> float:
    if ":" in t:
        m, s = t.split(":")
        return 60 * int(m) + float(s)
    return float(t)


def parse_split_line(ln: str):
    """(cumulatives, laps) for a split line, or None if the line is not one."""
    if not _SPLIT_LINE_SHAPE.match(ln):
        return None
    toks = _SPLIT_TOKEN.findall(ln.strip())
    return [c for c, _ in toks], [lap for _, lap in toks]

EVENT_HEADER = re.compile(r"^(?P<sex>Boys|Girls|Men|Women|Mixed)\s+(?P<event>.+)$")


@dataclass
class HytekEntry:
    place: str
    name: str
    age: int
    team: str
    seed: str
    final: str
    tags: str
    splits: "list[str]" = field(default_factory=list)

    @property
    def completed(self) -> bool:
        return self.final not in ("DFS", "DQ", "NS", "SCR")


def parse_section(text: str, require_splits: bool = True,
                  missing_splits: str = "refuse") -> "tuple[dict, list[HytekEntry], list[str]]":
    """
    Parse one event section.

    Returns (event_info, entries, problems). Every line that looks like a
    result but does not parse cleanly lands in `problems` rather than being
    guessed at.

    `require_splits=False` accepts sections whose official file prints no
    split lines at all (some meets publish final times only); such entries
    keep empty splits and feed PB history rather than shape analysis. An
    entry with a PARTIAL split set is a problem in either mode, and when any
    entry in the section has splits, all completed entries must — unless
    `missing_splits="blank"`, which handles the real-world case of an
    official file where a few entries have no or broken split lines (timing
    gaps): those entries keep their final time with splits cleared and a
    tag noting it, while every other entry is still held to the full check.
    """
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    event_info: dict = {}
    entries: "list[HytekEntry]" = []
    problems: "list[str]" = []

    current: HytekEntry | None = None
    for ln in lines:
        if not ln.strip() or set(ln.strip()) == {"="}:
            continue
        m = EVENT_HEADER.match(ln.strip())
        if m and not event_info:
            event_info = {"sex": m.group("sex"), "event": m.group("event").strip()}
            continue

        m = RESULT_LINE.match(ln)
        if m:
            current = HytekEntry(
                place=m.group("place"),
                name=m.group("name").strip(),
                age=int(m.group("age")),
                team=m.group("team"),
                seed=m.group("seed") or "",
                final=m.group("final"),
                tags=m.group("tags").strip(),
            )
            entries.append(current)
            continue

        parsed = parse_split_line(ln)
        if parsed is not None and current is not None:
            cums, laps = parsed
            current.splits = cums
            # printed lap times are redundant with the cumulatives; any
            # disagreement is a real inconsistency in the source, surfaced
            for i in range(1, len(cums)):
                if laps[i] and abs(_seconds(cums[i]) - _seconds(cums[i - 1])
                                   - _seconds(laps[i])) > 0.011:
                    problems.append(
                        f"{current.name}: {cums[i]} - {cums[i-1]} != printed "
                        f"lap {laps[i]}")
            continue

        # A line that resembles a result but failed to parse must be surfaced.
        if re.match(r"^\s{0,8}(\d{1,3}|--)\s+\S", ln):
            problems.append(ln)

    # structural validation
    any_splits = any(e.splits for e in entries)
    for e in entries:
        if e.completed:
            if len(e.splits) != 4 and missing_splits == "blank":
                note = ("no split line published" if not e.splits
                        else f"partial splits ({len(e.splits)}) dropped")
                e.splits = []
                e.tags = (e.tags + "; " + note).strip("; ")
                continue
            if len(e.splits) != 4 and (require_splits or any_splits
                                       or len(e.splits) != 0):
                problems.append(f"{e.name}: {len(e.splits)} splits, expected 4")
            elif e.splits and e.splits[-1] != e.final:
                problems.append(
                    f"{e.name}: last cumulative split {e.splits[-1]} != final {e.final}")
        elif e.splits:
            problems.append(f"{e.name}: non-completed swim carries splits")

    return event_info, entries, problems


def entries_to_raw_rows(entries, *, meet_id: str, meet_name: str,
                        meet_date: str, course: str, round_: str,
                        data_source: str, sid_of, extra_note: str = "",
                        meet_level: str = "invitational"):
    """
    Convert parsed entries into the project's raw-CSV row dicts.

    `sid_of` maps a swimmer's real name to an anonymous ID and is supplied by
    the caller so that one identity map spans every source. Non-completed
    entries (DFS/DQ/NS) are skipped; the caller reports how many.
    """
    rows = []
    for e in entries:
        if not e.completed:
            continue
        note_bits = [f"place {e.place}", f"hytek tags {e.tags or 'none'}",
                     "seed from official results"]
        if extra_note:
            note_bits.append(extra_note)
        rows.append({
            "swimmer_id": sid_of(e.name, e.age, meet_date),
            "meet_id": meet_id,
            "meet_name": meet_name,
            "meet_date": meet_date,
            # None = the source publishes no age (e.g. high school results
            # list grades); the blank fails the pipeline's age gate, which is
            # the intended conservative default.
            "age": "" if e.age is None else str(e.age),
            "sex_category": "M",
            "event": "200 FR",
            "course": course,
            "round": round_,
            "seed_time": "" if e.seed == "NT" else e.seed,
            "pre_race_pb": "",
            "final_time": e.final,
            "split_50": e.splits[0] if e.splits else "",
            "split_100": e.splits[1] if e.splits else "",
            "split_150": e.splits[2] if e.splits else "",
            "split_200": e.splits[3] if e.splits else "",
            "data_source": data_source,
            "split_15m": "", "reaction_time": "",
            "meet_level": meet_level,
            "team": e.team,
            "notes": "; ".join(note_bits),
        })
    return rows
