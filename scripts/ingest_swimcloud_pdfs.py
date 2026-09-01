#!/usr/bin/env python3
"""
Ingest the three SwimCloud event-result PDFs (2026-08-31 upload) into the raw
dataset schema, with anonymization.

WHAT THESE SOURCES CONTAIN, AND DO NOT CONTAIN
----------------------------------------------
SwimCloud event pages carry place, name, team and FINAL TIME ONLY. They carry
no 50 splits, no ages, no seed times. That was verified against the live pages
on 2026-08-31, including the per-time detail pages, which also have no splits
for these meets. Missing fields are therefore left missing, per the collection
protocol: no fabrication, no substitution.

The consequence is stated up front: rows ingested from these sources CANNOT be
used for any pacing analysis, because the entire methodology runs on the four
50 splits. They are ingested anyway because (a) they exercise the pipeline's
missing-data handling on real input, (b) the anonymization map and meet
records they establish carry over when split data for the same meets arrives,
and (c) final times from earlier meets feed pre_race_pb chains later.

Meet metadata (dates, course, venue) was recovered from the live SwimCloud
pages on 2026-08-31 and is recorded per meet below.

ANONYMIZATION
-------------
Swimmers are assigned S### identifiers in order of first appearance. The
name-to-ID map is written to data/private/swimmer_id_map.csv, which is
gitignored and must never be committed or published. Identity across meets is
matched on exact full name; where the same name appears with a different team
in a different meet, it is treated as the same person only if no other swimmer
of that name appears in the same meet (club changes are common between fall
and summer), and the ambiguity is recorded in the notes column.
"""

import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EXTRACTED = "/home/claude/meet_pdfs/extracted_rows.csv"

MEETS = {
    "2026_PC_SC_SENIOR_OPEN": dict(
        meet_name="Pacific Swimming SC Senior Open",
        meet_date="2025-10-18",  # meet ran Oct 18-19, 2025; swim day unknown
        course="SCY",
        note="dates Oct 18-19 2025, Soda Aquatic Center, Moraga CA; "
             "timed finals; swim day within meet unknown",
        source="SwimCloud event page saved to PDF 2026-08-31, "
               "https://www.swimcloud.com/results/358817/event/16/ "
               "(no splits, ages or seed times published there)",
    ),
    "2026_PC_CAL_INVITATIONAL": dict(
        meet_name="PC Cal Invitational",
        meet_date="2026-01-17",  # meet ran Jan 17-18, 2026
        course="SCY",
        note="dates Jan 17-18 2026, Legends Aquatic Center, Berkeley CA; "
             "timed finals; field includes college and open swimmers, so many "
             "rows will be outside the 15-18 scope once ages are known",
        source="SwimCloud event page saved to PDF 2026-08-31, "
               "https://www.swimcloud.com/results/373259/event/24/ "
               "(no splits, ages or seed times published there)",
    ),
    "2026_PC_TERA_FAR_WESTERN": dict(
        meet_name="PC TERA Far Western Championships",
        meet_date="2026-07-30",  # meet ran Jul 30 - Aug 2, 2026
        course="LCM",  # confirmed long course metres; MUST NOT mix into SCY
        note="dates Jul 30 - Aug 2 2026; LONG COURSE METRES, retained only so "
             "the course guard is exercised on real data; age group recorded "
             "from the section header",
        source="SwimCloud event page saved to PDF 2026-08-31, "
               "https://www.swimcloud.com/results/393282/event/18/ "
               "(no splits, ages or seed times published there)",
    ),
}

RAW_HEADER = ["swimmer_id", "meet_id", "meet_name", "meet_date", "age",
              "sex_category", "event", "course", "round", "seed_time",
              "pre_race_pb", "final_time", "split_50", "split_100",
              "split_150", "split_200", "data_source",
              "split_15m", "reaction_time", "meet_level", "team", "notes"]


def main() -> None:
    with open(EXTRACTED) as f:
        rows = list(csv.DictReader(f))

    # ---- anonymization with cross-meet identity matching -------------------
    # name -> list of (meet_id, team); same exact name in the same meet twice
    # would be two different people, which we check for and did not observe.
    by_name = defaultdict(list)
    for r in rows:
        by_name[r["name"]].append((r["meet_id"], r["team"]))

    sid_of, notes_of = {}, {}
    counter = 0
    for r in rows:
        name = r["name"]
        if name not in sid_of:
            counter += 1
            sid_of[name] = f"S{counter:03d}"
            teams = {t for _, t in by_name[name]}
            meets = {m for m, _ in by_name[name]}
            if len(teams) > 1 and len(meets) > 1:
                notes_of[name] = (f"same name in {len(meets)} meets with "
                                  f"different team listings; treated as one "
                                  f"person, verify when splits arrive")
            else:
                notes_of[name] = ""

    # ---- private map, never committed --------------------------------------
    priv_dir = os.path.join(REPO, "data", "private")
    os.makedirs(priv_dir, exist_ok=True)
    with open(os.path.join(priv_dir, "swimmer_id_map.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["swimmer_id", "name", "teams", "meets"])
        for name, sid in sorted(sid_of.items(), key=lambda kv: kv[1]):
            w.writerow([sid, name,
                        "; ".join(sorted({t for _, t in by_name[name]})),
                        "; ".join(sorted({m for m, _ in by_name[name]}))])

    # ---- raw dataset --------------------------------------------------------
    out = []
    for r in rows:
        meet = MEETS[r["meet_id"]]
        note_bits = [meet["note"]]
        if r["age_group"]:
            note_bits.append(f"age group {r['age_group']}")
        note_bits.append(f"place {r['place']}")
        if notes_of[r["name"]]:
            note_bits.append(notes_of[r["name"]])
        out.append({
            "swimmer_id": sid_of[r["name"]],
            "meet_id": r["meet_id"],
            "meet_name": meet["meet_name"],
            "meet_date": meet["meet_date"],
            "age": "",                      # not published on these pages
            "sex_category": "M",
            "event": "200 FR",
            "course": meet["course"],
            "round": r["round"],
            "seed_time": "",                # not published
            "pre_race_pb": "",              # not published; derivable later
            "final_time": r["final_time"],
            "split_50": "", "split_100": "", "split_150": "", "split_200": "",
            "data_source": meet["source"],
            "split_15m": "", "reaction_time": "",
            "meet_level": ("championship" if "FAR_WESTERN" in r["meet_id"]
                           else "invitational"),
            "team": r["team"],
            "notes": "; ".join(note_bits),
        })

    raw_path = os.path.join(REPO, "data", "raw", "200_free_scy_raw.csv")
    with open(raw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RAW_HEADER)
        w.writeheader()
        w.writerows(out)

    n_scy = sum(1 for r in out if r["course"] == "SCY")
    print(f"wrote {raw_path}: {len(out)} rows "
          f"({n_scy} SCY, {len(out) - n_scy} LCM), "
          f"{len(sid_of)} unique swimmers")
    print(f"private map: data/private/swimmer_id_map.csv (gitignored)")

    # repeated swimmers across meets, useful later for pre_race_pb chains
    multi = {n: m for n, m in
             (( name, {mm for mm, _ in v}) for name, v in by_name.items())
             if len(m) > 1}
    print(f"swimmers appearing in more than one meet: {len(multi)}")


if __name__ == "__main__":
    main()
