#!/usr/bin/env python3
"""
Config-driven ingester for official Hy-Tek meet results (Task: dataset
expansion). One meet = one JSON config in `configs/meets/`; the code is the
same for every meet, so adding a meet is data, not programming.

    python -m scripts.ingest_hytek configs/meets/2025_orinda_sc_senior_open.json
    python -m scripts.ingest_hytek --record data/private/sources/foo.txt

Design rules, inherited from the first (Orinda) ingest:
- Sources are verbatim saved sections of OFFICIAL results pages, stored under
  `data/private/sources/` (gitignored — they contain minors' names). The
  config records the source's sha256; ingest refuses on mismatch, so a source
  file cannot drift silently after its checksum is recorded.
- Anonymization reuses one private map (`data/private/swimmer_id_map.csv`) so
  a swimmer keeps one S-number across meets and sources. Hy-Tek names
  ("Last, First M") match SwimCloud names ("First Last") on normalized
  (first, last) tokens, middle initials dropped; every match basis is
  recorded in the map.
- Re-running an ingest is idempotent: rows for the config's meet_id are
  replaced, never duplicated.
- Malformed sections refuse loudly (parse problems abort the ingest).
"""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from src.hytek_parser import parse_section, entries_to_raw_rows  # noqa: E402
from src.results_parsers import (parse_hs_champ_section,  # noqa: E402
                                 parse_lap_section)

#: Section formats the ingester can read. "hytek" is the classic results
#: section; the others are documented in src/results_parsers.py.
PARSERS = {
    "hytek": parse_section,
    "lap_times": parse_lap_section,
    "hs_championship": parse_hs_champ_section,
}

REQUIRED_KEYS = ["meet_id", "meet_name", "meet_date", "course", "data_source"]
SECTION_KEYS = ["source_file", "round", "expected_event"]


def config_sections(cfg: dict) -> "list[dict]":
    """
    A meet is one or more sections (e.g. prelims and finals as separate
    source files). Multi-section configs carry a "sections" list; classic
    single-section configs keep their top-level keys. Each section:
    source_file, round, expected_event, optional format (default "hytek")
    and optional source_sha256.
    """
    if "sections" in cfg:
        secs = cfg["sections"]
    else:
        secs = [{k: cfg.get(k) for k in
                 ("source_file", "round", "expected_event", "source_sha256")}
                | {"format": cfg.get("format", "hytek")}]
    out = []
    for s in secs:
        missing = [k for k in SECTION_KEYS if not s.get(k)]
        if missing:
            raise SystemExit(f"section missing required keys: {missing}")
        fmt = s.get("format", "hytek")
        if fmt not in PARSERS:
            raise SystemExit(f"unknown section format {fmt!r}; "
                             f"known: {sorted(PARSERS)}")
        out.append(dict(s, format=fmt))
    return out


def norm_key(name: str) -> "tuple[str, str]":
    """('first','last') from either 'Last, First M' or 'First Last'."""
    name = re.sub(r"\s+", " ", name.strip())
    if "," in name:
        last, first = [p.strip() for p in name.split(",", 1)]
        first = first.split()[0] if first.split() else first
        return first.lower(), last.lower()
    parts = name.split()
    return parts[0].lower(), " ".join(parts[1:]).lower()


def name_variants(field: str) -> "list[str]":
    """
    All recorded spellings in a map row's name field. The field accumulates
    variants as sources are merged ("First Last | hytek: Last, First M"), and
    the identity lookup must index EVERY variant: the original Orinda script
    keyed only the raw field, so a swimmer recorded with a hytek variant could
    never be matched again — re-ingesting or ingesting a second meet would
    mint duplicate IDs. Found by the byte-identity re-ingest check.
    """
    parts = [p.strip() for p in field.split("|")]
    return [re.sub(r"^hytek:\s*", "", p) for p in parts if p]


def _date(s: str) -> date:
    return date.fromisoformat(str(s)[:10])


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config(path: str) -> dict:
    with open(path) as f:
        cfg = json.load(f)
    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        raise SystemExit(f"config {path} missing required keys: {missing}")
    return cfg


def ingest(cfg: dict, repo: str = REPO, raw_csv: str | None = None,
           map_csv: str | None = None, verbose: bool = True) -> dict:
    """
    Run one meet's ingest. Paths are repo-relative in the config; `raw_csv` /
    `map_csv` overrides exist so tests can run against fixtures.
    Returns a summary dict (rows added, matches, new ids, source sha256).
    """
    raw_csv = raw_csv or os.path.join(repo, "data", "raw", "200_free_scy_raw.csv")
    map_csv = map_csv or os.path.join(repo, "data", "private", "swimmer_id_map.csv")

    parsed_sections, files = [], []
    for sec in config_sections(cfg):
        src_path = os.path.join(repo, sec["source_file"])
        digest = sha256_of(src_path)
        if sec.get("source_sha256") and sec["source_sha256"] != digest:
            raise SystemExit(
                f"source checksum mismatch for {cfg['meet_id']} "
                f"({sec['source_file']}): config says "
                f"{sec['source_sha256'][:12]}…, file is {digest[:12]}…. The "
                "saved source changed since its checksum was recorded; "
                "re-verify against the official page before ingesting.")

        text = open(src_path).read()
        if sec["format"] == "hytek":
            info, entries, problems = parse_section(
                text, require_splits=sec.get("require_splits", True),
                missing_splits=sec.get("missing_splits", "refuse"))
        else:
            info, entries, problems = PARSERS[sec["format"]](text)
        if info != sec["expected_event"]:
            raise SystemExit(f"event mismatch in {sec['source_file']}: parsed "
                             f"{info}, config expects {sec['expected_event']}")
        if problems:
            for p in problems:
                print("  PARSE PROBLEM:", p)
            raise SystemExit(f"{len(problems)} parse problems in "
                             f"{sec['source_file']}, refusing to ingest")

        completed = [e for e in entries if e.completed]
        skipped = [e for e in entries if not e.completed]
        if verbose:
            print(f"{os.path.basename(sec['source_file'])} "
                  f"[{sec['format']}, {sec['round']}]: {len(entries)} entries, "
                  f"{len(completed)} completed, {len(skipped)} skipped "
                  f"({', '.join(e.final for e in skipped) or '-'})")
        parsed_sections.append((sec, completed))
        files.append({"file": os.path.basename(sec["source_file"]),
                      "sha256": digest, "rows": len(completed)})

    return merge_parsed_sections(cfg, parsed_sections, files, raw_csv=raw_csv,
                                 map_csv=map_csv, verbose=verbose)


def merge_parsed_sections(cfg: dict, parsed_sections, files, *, raw_csv: str,
                          map_csv: str, verbose: bool = True) -> dict:
    """
    Shared merge step for every ingest path (Hy-Tek sections, transcriptions,
    verified spreadsheet extracts): anonymize through the ONE private identity
    map, replace this meet_id's rows in the raw CSV, update the map's meet
    membership. `parsed_sections` is a list of (section_dict, completed_entries);
    `files` a list of {file, sha256, rows} for the integrity record.
    """
    with open(map_csv) as f:
        existing = list(csv.DictReader(f))
    # every recorded spelling indexes its row; a key may hold SEVERAL rows
    # once two different people share a normalized name (see sid_of)
    by_key: dict = {}
    for r in existing:
        for v in name_variants(r["name"]):
            by_key.setdefault(norm_key(v), [])
            if r not in by_key[norm_key(v)]:
                by_key[norm_key(v)].append(r)
    next_n = 1 + max((int(r["swimmer_id"][1:]) for r in existing), default=0)
    matches, created, split_off = [], [], []

    # ages already on file per identity, for age-aware matching (this meet's
    # own prior rows are excluded so a re-ingest reproduces a first ingest)
    known: dict = {}
    with open(raw_csv) as f:
        for r in csv.DictReader(f):
            if r.get("age") and r["meet_id"] != cfg["meet_id"]:
                known.setdefault(r["swimmer_id"], []).append(
                    (int(float(r["age"])), r["meet_date"]))

    def _consistent(sid: str, age, meet_date) -> bool:
        """Could a person aged `age` on `meet_date` be identity `sid`?"""
        if age is None or not meet_date:
            return True
        d = _date(meet_date)
        for a0, d0 in known.get(sid, []):
            delta = (d - _date(d0)).days / 365.25
            if not (a0 + math.floor(delta) <= age <= a0 + math.ceil(delta)):
                return False
        return True

    def sid_of(hytek_name: str, age=None, meet_date=None) -> str:
        """
        Anonymous ID for a name. Name match alone is not enough: when the
        entry's published age is impossible for the matched identity (two
        different people sharing a name, which happened on the first
        multi-meet expansion), the entry gets its OWN identity and the split
        is recorded in the map. Age-blank entries match by name only, the
        documented limitation.
        """
        nonlocal next_n
        key = norm_key(hytek_name)
        cands = by_key.get(key, [])
        for row in cands:
            if _consistent(row["swimmer_id"], age, meet_date):
                if hytek_name not in row["name"]:
                    row["name"] = f"{row['name']} | hytek: {hytek_name}"
                matches.append((hytek_name, row["swimmer_id"]))
                if age is not None and meet_date:
                    known.setdefault(row["swimmer_id"], []).append((age, meet_date))
                return row["swimmer_id"]
        sid = f"S{next_n:03d}"
        next_n += 1
        row = {"swimmer_id": sid, "name": f"hytek: {hytek_name}",
               "teams": "", "meets": ""}
        if cands:
            row["teams"] = (f"distinct person from {cands[0]['swimmer_id']}: "
                            f"same name, age-inconsistent")
            split_off.append((hytek_name, sid, cands[0]["swimmer_id"]))
        existing.append(row)
        by_key.setdefault(key, []).append(row)
        if age is not None and meet_date:
            known[sid] = [(age, meet_date)]
        created.append((hytek_name, sid))
        return sid

    rows = []
    for sec, completed in parsed_sections:
        rows.extend(entries_to_raw_rows(
            completed, meet_id=cfg["meet_id"], meet_name=cfg["meet_name"],
            meet_date=cfg["meet_date"], course=cfg["course"],
            round_=sec["round"], data_source=cfg["data_source"],
            sid_of=sid_of, extra_note=cfg.get("notes", ""),
            meet_level=cfg.get("meet_level", "invitational"),
        ))

    for r in existing:
        meets = set(filter(None, (r.get("meets") or "").split("; ")))
        if any(sid == r["swimmer_id"] for _, sid in matches + created):
            meets.add(cfg["meet_id"])
        r["meets"] = "; ".join(sorted(meets))

    with open(raw_csv) as f:
        rdr = csv.DictReader(f)
        header = rdr.fieldnames
        old = [r for r in rdr if r["meet_id"] != cfg["meet_id"]]

    merged = old + rows
    with open(raw_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(merged)

    with open(map_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["swimmer_id", "name", "teams", "meets"])
        w.writeheader()
        w.writerows(existing)

    if verbose:
        print(f"raw file now {len(merged)} rows "
              f"({len(old)} prior + {len(rows)} from this meet)")
        print(f"identity map: {len(matches)} cross-source matches, "
              f"{len(created)} new IDs (total {len(existing)})"
              + (f"; {len(split_off)} same-name identities split off on age"
                 if split_off else ""))

    return {"meet_id": cfg["meet_id"], "rows": len(rows),
            "raw_total": len(merged), "matches": len(matches),
            "new_ids": len(created), "files": files}


INTEGRITY_HEADER = (
    "## Source integrity (public record of private sources)\n\n"
    "The verbatim sources live in `data/private/` and are never published; "
    "their sha256 digests are public, so anyone re-retrieving the official "
    "page can verify the dataset was built from the genuine file.\n\n"
    "| meet_id | source file | sha256 | rows | ingested |\n"
    "|---|---|---|---|---|\n")


def record_integrity(cfg: dict, summary: dict, repo: str = REPO,
                     versions_md: str | None = None) -> None:
    """
    Publish the source's sha256 in data/DATASET_VERSIONS.md: provenance is
    verifiable without exposing a file full of minors' names. Idempotent by
    meet_id (a re-ingest updates its row in place).
    """
    from datetime import date

    path = versions_md or os.path.join(repo, "data", "DATASET_VERSIONS.md")
    text = open(path).read()
    new_rows = [(f"| {cfg['meet_id']} | {f['file']} | `{f['sha256']}` | "
                 f"{f['rows']} | {date.today().isoformat()} |\n")
                for f in summary["files"]]
    if INTEGRITY_HEADER not in text:
        text = text.rstrip() + "\n\n" + INTEGRITY_HEADER + "".join(new_rows)
    else:
        head, _, tail = text.partition(INTEGRITY_HEADER)
        lines = [ln for ln in tail.splitlines(keepends=True)
                 if ln.startswith("|")]
        rest = "".join(ln for ln in tail.splitlines(keepends=True)
                       if not ln.startswith("|"))
        lines = [ln for ln in lines
                 if not ln.startswith(f"| {cfg['meet_id']} ")] + new_rows
        text = head + INTEGRITY_HEADER + "".join(lines) + rest
    with open(path, "w") as f:
        f.write(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config", nargs="?", help="meet config JSON")
    ap.add_argument("--record", metavar="SOURCE",
                    help="print the sha256 of a source file (for a new config)")
    args = ap.parse_args()
    if args.record:
        print(sha256_of(args.record))
        return
    if not args.config:
        ap.error("give a meet config, or --record SOURCE")
    cfg = load_config(args.config)
    summary = ingest(cfg)
    record_integrity(cfg, summary)
    print("integrity row recorded in data/DATASET_VERSIONS.md")


if __name__ == "__main__":
    main()
