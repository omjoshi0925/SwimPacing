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
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from src.hytek_parser import parse_section, entries_to_raw_rows  # noqa: E402

REQUIRED_KEYS = ["meet_id", "meet_name", "meet_date", "course", "round",
                 "source_file", "data_source", "expected_event"]


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
    src_path = os.path.join(repo, cfg["source_file"])

    digest = sha256_of(src_path)
    if cfg.get("source_sha256") and cfg["source_sha256"] != digest:
        raise SystemExit(
            f"source checksum mismatch for {cfg['meet_id']}: config says "
            f"{cfg['source_sha256'][:12]}…, file is {digest[:12]}…. The saved "
            "source changed since its checksum was recorded; re-verify against "
            "the official page before ingesting.")

    section = open(src_path).read()
    info, entries, problems = parse_section(section)
    if info != cfg["expected_event"]:
        raise SystemExit(f"event mismatch: parsed {info}, "
                         f"config expects {cfg['expected_event']}")
    if problems:
        for p in problems:
            print("  PARSE PROBLEM:", p)
        raise SystemExit(f"{len(problems)} parse problems, refusing to ingest")

    completed = [e for e in entries if e.completed]
    skipped = [e for e in entries if not e.completed]
    if verbose:
        print(f"parsed {len(entries)} entries: {len(completed)} completed, "
              f"{len(skipped)} skipped "
              f"({', '.join(e.final for e in skipped) or '-'})")

    with open(map_csv) as f:
        existing = list(csv.DictReader(f))
    by_key: dict = {}
    for r in existing:
        for v in name_variants(r["name"]):
            # first writer wins; two different swimmers sharing a normalized
            # (first, last) is the known limitation of name-based matching and
            # is documented in data/data_dictionary.md
            by_key.setdefault(norm_key(v), r)
    next_n = 1 + max((int(r["swimmer_id"][1:]) for r in existing), default=0)
    matches, created = [], []

    def sid_of(hytek_name: str) -> str:
        nonlocal next_n
        key = norm_key(hytek_name)
        if key in by_key:
            row = by_key[key]
            if hytek_name not in row["name"]:
                row["name"] = f"{row['name']} | hytek: {hytek_name}"
            matches.append((hytek_name, row["swimmer_id"]))
            return row["swimmer_id"]
        sid = f"S{next_n:03d}"
        next_n += 1
        row = {"swimmer_id": sid, "name": f"hytek: {hytek_name}",
               "teams": "", "meets": ""}
        existing.append(row)
        by_key[key] = row
        created.append((hytek_name, sid))
        return sid

    rows = entries_to_raw_rows(
        completed, meet_id=cfg["meet_id"], meet_name=cfg["meet_name"],
        meet_date=cfg["meet_date"], course=cfg["course"],
        round_=cfg["round"], data_source=cfg["data_source"], sid_of=sid_of,
        extra_note=cfg.get("notes", ""),
    )

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
              f"{len(created)} new IDs (total {len(existing)})")

    return {"meet_id": cfg["meet_id"], "rows": len(rows),
            "raw_total": len(merged), "matches": len(matches),
            "new_ids": len(created), "source_sha256": digest}


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
    ingest(load_config(args.config))


if __name__ == "__main__":
    main()
