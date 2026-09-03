#!/usr/bin/env python3
"""
Ingest meets from a verified extraction spreadsheet (Tier 2 "verified
transcription" path; data/data_dictionary.md, provenance tiers).

The spreadsheet is a third-party extraction of official results files, one
row per completed swim, with cumulative splits. It is admitted MEET BY MEET,
each meet named in a config with its own verification status, because
extraction quality is a per-file property: on this project's first such
workbook the extraction matched verbatim official HTML sections 100% on 356
rows across four meets, matched every independently confirmed PDF entry, and
yet one meet's rows were contradicted by its official file. Meets are
therefore admitted only with a stated basis, and everything else is refused.

    python -m scripts.ingest_spreadsheet configs/meets/spreadsheet_2026-09-02.json

Per-meet config keys: sheet_meet (the workbook's Meet label), meet_id,
meet_name, meet_date, course, meet_level, data_source, verification
(free text, required), splits ("use" | "blank"), notes.
"""

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import pandas as pd  # noqa: E402

from scripts.ingest_hytek import (merge_parsed_sections,  # noqa: E402
                                  record_integrity, sha256_of)
from src.hytek_parser import HytekEntry  # noqa: E402

ROUND = {"Timed final": "timed_final", "Preliminary": "prelim", "Final": "final"}


def _fmt(t) -> str:
    """Normalize a workbook time cell to Hy-Tek text (24.3 -> '24.30')."""
    if t is None or (isinstance(t, float) and math.isnan(t)):
        return ""
    s = str(t).strip()
    if ":" in s:
        m, sec = s.split(":")
        return f"{int(m)}:{float(sec):05.2f}"
    return f"{float(s):.2f}"


def entries_for_meet(df: pd.DataFrame, splits_policy: str):
    """Workbook rows for one meet -> {round: [HytekEntry]}."""
    by_round: dict = {}
    for _, r in df.iterrows():
        complete = (r["Split Status"] == "Complete 50-yard splits"
                    and splits_policy == "use")
        splits = ([_fmt(r["50 Cum"]), _fmt(r["100 Cum"]), _fmt(r["150 Cum"]),
                   _fmt(r["200 Cum"])] if complete else [])
        age = None if pd.isna(r["Age"]) else int(r["Age"])
        tags = []
        if isinstance(r.get("Class"), str) and r["Class"]:
            tags.append(f"grade {r['Class']}")
        if not complete:
            tags.append("splits withheld at ingest" if splits_policy == "blank"
                        else f"workbook split status: {r['Split Status']}")
        e = HytekEntry(place=str(r["Place"]), name=str(r["Swimmer"]).strip(),
                       age=age, team=str(r["Team"]), seed="",
                       final=_fmt(r["Final Time"]), tags="; ".join(tags),
                       splits=splits)
        by_round.setdefault(ROUND.get(str(r["Round"]), "timed_final"), []).append(e)
    return by_round


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config")
    args = ap.parse_args()
    cfg = json.load(open(args.config))
    wb = os.path.join(REPO, cfg["workbook"])
    digest = sha256_of(wb)
    if cfg.get("workbook_sha256") and cfg["workbook_sha256"] != digest:
        raise SystemExit("workbook checksum mismatch; re-verify before ingesting")
    xl = pd.read_excel(wb, sheet_name=cfg.get("sheet", "Men 200 Free"))

    raw_csv = os.path.join(REPO, "data", "raw", "200_free_scy_raw.csv")
    map_csv = os.path.join(REPO, "data", "private", "swimmer_id_map.csv")
    for m in cfg["meets"]:
        if not m.get("verification"):
            raise SystemExit(f"{m['meet_id']}: no verification basis stated; refusing")
        sub = xl[xl["Meet"] == m["sheet_meet"]]
        if sub.empty:
            raise SystemExit(f"{m['meet_id']}: no workbook rows for {m['sheet_meet']!r}")
        by_round = entries_for_meet(sub, m.get("splits", "use"))
        meet_cfg = {k: m[k] for k in ("meet_id", "meet_name", "meet_date",
                                      "course", "data_source")}
        meet_cfg["meet_level"] = m.get("meet_level", "invitational")
        meet_cfg["notes"] = m.get("notes", "")
        parsed = [({"round": rnd}, ents) for rnd, ents in by_round.items()]
        files = [{"file": os.path.basename(cfg["workbook"]) + f" [{m['sheet_meet']}]",
                  "sha256": digest, "rows": int(len(sub))}]
        print(f"== {m['meet_id']}: {len(sub)} workbook rows, rounds "
              f"{ {k: len(v) for k, v in by_round.items()} }, splits={m.get('splits', 'use')}")
        summary = merge_parsed_sections(meet_cfg, parsed, files, raw_csv=raw_csv,
                                        map_csv=map_csv, verbose=True)
        record_integrity(meet_cfg, summary, repo=REPO)


if __name__ == "__main__":
    main()
