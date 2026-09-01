#!/usr/bin/env python3
"""
Ingest the Boys 200 Yard Freestyle section of the Orinda Aquatics SCY Senior
Open (Jan 25-26, 2025) official Hy-Tek results into the raw dataset, merging
with the rows already ingested from the SwimCloud PDFs and REUSING the same
anonymization map so one swimmer keeps one ID across sources.

Source: official meet results hosted by Pacific Swimming,
https://www.pacswim.org/userfiles/meets/documents/2616/
2025-01-25-orinda-sc-senior-open-meet---results.htm
Sanction #25-010. Retrieved 2026-08-31 through the user's browser; the saved
section was verified byte-identical to the live page by dual checksum.

Identity matching across sources: Hy-Tek lists names as "Last, First M";
SwimCloud as "First Last". A Hy-Tek entry is matched to an existing SwimCloud
identity when normalized (first, last) tokens agree exactly (middle initials
dropped). Every such match is recorded in the private map with its basis.
Unmatched names get new IDs.
"""

import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from src.hytek_parser import parse_section, entries_to_raw_rows  # noqa: E402

SOURCE_TXT = os.path.join(REPO, "data", "private", "sources",
                          "orinda_2025-01-25_boys_200_free.txt")
RAW_CSV = os.path.join(REPO, "data", "raw", "200_free_scy_raw.csv")
MAP_CSV = os.path.join(REPO, "data", "private", "swimmer_id_map.csv")

MEET_ID = "2025_ORINDA_SC_SENIOR_OPEN"
DATA_SOURCE = ("Official Hy-Tek results, Orinda Aquatics SCY Senior Open Meet "
               "1/25-26/2025, Sanction #25-010, Boys 200 Yard Freestyle, "
               "https://www.pacswim.org/userfiles/meets/documents/2616/"
               "2025-01-25-orinda-sc-senior-open-meet---results.htm "
               "(retrieved 2026-08-31, checksum-verified)")


def norm_key(name: str) -> "tuple[str, str]":
    """('first','last') from either 'Last, First M' or 'First Last'."""
    name = re.sub(r"\s+", " ", name.strip())
    if "," in name:
        last, first = [p.strip() for p in name.split(",", 1)]
        first = first.split()[0] if first.split() else first
        # multi-word last names keep all their words
        return first.lower(), last.lower()
    parts = name.split()
    return parts[0].lower(), " ".join(parts[1:]).lower()


def main() -> None:
    section = open(SOURCE_TXT).read()
    info, entries, problems = parse_section(section)
    assert info == {"sex": "Boys", "event": "200 Yard Freestyle"}, info
    if problems:
        print("PARSE PROBLEMS, refusing to ingest:")
        for p in problems:
            print("  ", p)
        sys.exit(1)

    completed = [e for e in entries if e.completed]
    skipped = [e for e in entries if not e.completed]
    print(f"parsed {len(entries)} entries: {len(completed)} completed, "
          f"{len(skipped)} skipped ({', '.join(e.final for e in skipped) or '-'})")

    # ---- load the existing map and extend it -------------------------------
    with open(MAP_CSV) as f:
        existing = list(csv.DictReader(f))
    by_key = {norm_key(r["name"]): r for r in existing}
    next_n = 1 + max(int(r["swimmer_id"][1:]) for r in existing)

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
        completed, meet_id=MEET_ID,
        meet_name="Orinda Aquatics SCY Senior Open Meet",
        meet_date="2025-01-25",  # meet ran Jan 25-26; event day not stated
        course="SCY", round_="timed_final",
        data_source=DATA_SOURCE, sid_of=sid_of,
        extra_note="meet ran 2025-01-25 to 2025-01-26, event day not stated; "
                   "senior open field includes ages outside 15-18 by design",
    )

    # note which meet each mapped swimmer now spans
    for r in existing:
        meets = set(filter(None, (r.get("meets") or "").split("; ")))
        if any(sid == r["swimmer_id"] for _, sid in matches + created):
            meets.add(MEET_ID)
        r["meets"] = "; ".join(sorted(meets))

    # ---- merge into the raw CSV (idempotent) -------------------------------
    with open(RAW_CSV) as f:
        rdr = csv.DictReader(f)
        header = rdr.fieldnames
        old = [r for r in rdr if r["meet_id"] != MEET_ID]

    merged = old + rows
    with open(RAW_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(merged)

    with open(MAP_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["swimmer_id", "name", "teams", "meets"])
        w.writeheader()
        w.writerows(existing)

    print(f"raw file now {len(merged)} rows "
          f"({len(old)} prior + {len(rows)} from this meet)")
    print(f"identity map: {len(matches)} cross-source matches, "
          f"{len(created)} new IDs (total {len(existing)})")
    print("cross-source matches:",
          ", ".join(f"{n}->{s}" for n, s in matches[:12]),
          "..." if len(matches) > 12 else "")
    in_scope = sum(1 for r in rows if 15 <= int(r["age"]) <= 18)
    print(f"ages in this meet: {min(int(r['age']) for r in rows)}-"
          f"{max(int(r['age']) for r in rows)}; 15-18 in scope: {in_scope}")


if __name__ == "__main__":
    main()
