"""
Tests for the config-driven Hy-Tek ingester (scripts/ingest_hytek.py) on
synthetic fixtures: config validation, checksum refusal, cross-source identity
matching through recorded name variants, and byte-level idempotency — the
property whose absence in the original one-meet script minted duplicate IDs.
"""

import csv
import json
import os

import pytest

from scripts.ingest_hytek import ingest, load_config, name_variants, norm_key

SECTION = """Boys 200 Yard Freestyle
===============================================================================
              1:58.59  SRII
    Name                     Age Team                    Seed     Finals
===============================================================================
  1 Alpha, Test               16 AAAA-PC              1:36.64    1:37.01 SRII
       22.72    47.02  1:11.97  1:37.01
  2 Beta, Case B              15 BBBB-PC                   NT    1:42.63 SRII+
       24.33    50.11  1:16.19  1:42.63
 -- Delta, Scratch            14 AAAA-PC              1:50.11        DFS
"""

@pytest.fixture()
def sandbox(tmp_path, synthetic_raw_csv):
    """A repo-shaped sandbox: source file, empty raw CSV, seeded id map."""
    src = tmp_path / "sources" / "meet.txt"
    src.parent.mkdir()
    src.write_text(SECTION)

    raw = tmp_path / "raw.csv"
    # Column names only, taken from the synthetic fixture rather than the
    # gitignored real raw file, which CI's clean checkout does not have.
    header = open(synthetic_raw_csv).readline().strip().split(",")
    with open(raw, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=header).writeheader()

    idmap = tmp_path / "map.csv"
    with open(idmap, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["swimmer_id", "name", "teams", "meets"])
        w.writeheader()
        # seeded with a SwimCloud-style spelling of the same person the
        # Hy-Tek section lists as "Alpha, Test"
        w.writerow({"swimmer_id": "S001", "name": "Test Alpha",
                    "teams": "AAAA", "meets": "OTHER_MEET"})

    cfg = {
        "meet_id": "TEST_MEET", "meet_name": "Test Meet",
        "meet_date": "2025-01-01", "course": "SCY", "round": "timed_final",
        "source_file": str(src.relative_to(tmp_path)),
        "data_source": "synthetic fixture",
        "expected_event": {"sex": "Boys", "event": "200 Yard Freestyle"},
    }
    return {"repo": str(tmp_path), "raw": str(raw), "map": str(idmap),
            "cfg": cfg}


def run(sb):
    return ingest(sb["cfg"], repo=sb["repo"], raw_csv=sb["raw"],
                  map_csv=sb["map"], verbose=False)


def test_ingest_adds_completed_rows_only(sandbox):
    summary = run(sandbox)
    assert summary["rows"] == 2  # DFS skipped
    rows = list(csv.DictReader(open(sandbox["raw"])))
    assert len(rows) == 2
    assert {r["meet_id"] for r in rows} == {"TEST_MEET"}


def test_identity_matches_across_source_spellings(sandbox):
    summary = run(sandbox)
    assert summary["matches"] == 1 and summary["new_ids"] == 1
    rows = {r["name"]: r for r in csv.DictReader(open(sandbox["map"]))}
    matched = [r for r in rows.values() if r["swimmer_id"] == "S001"]
    assert len(matched) == 1
    assert "hytek: Alpha, Test" in matched[0]["name"]
    assert "TEST_MEET" in matched[0]["meets"] and "OTHER_MEET" in matched[0]["meets"]


def test_reingest_is_byte_identical(sandbox):
    run(sandbox)
    raw1 = open(sandbox["raw"]).read()
    map1 = open(sandbox["map"]).read()
    run(sandbox)
    assert open(sandbox["raw"]).read() == raw1
    assert open(sandbox["map"]).read() == map1


def test_variant_lookup_survives_recorded_hytek_names():
    """The regression the original script had: index EVERY recorded variant."""
    field = "Test Alpha | hytek: Alpha, Test B"
    keys = {norm_key(v) for v in name_variants(field)}
    assert norm_key("Test Alpha") in keys
    assert norm_key("Alpha, Test B") in keys


def test_checksum_mismatch_refuses(sandbox):
    sandbox["cfg"]["source_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="checksum mismatch"):
        run(sandbox)


def test_event_mismatch_refuses(sandbox):
    sandbox["cfg"]["expected_event"] = {"sex": "Girls",
                                        "event": "200 Yard Freestyle"}
    with pytest.raises(SystemExit, match="event mismatch"):
        run(sandbox)


SECTION_B = """Boys 200 Yard Freestyle
===============================================================================
              1:58.59  SRII
    Name                     Age Team                    Seed     Finals
===============================================================================
  1 Alpha, Test               16 AAAA-PC              1:37.01    1:36.20 SRII
       22.50    46.80  1:11.40  1:36.20
  2 Epsilon, New              17 DDDD-PC                   NT    1:44.10
       24.90    51.00  1:17.55  1:44.10
"""


def test_two_meet_merge_keeps_one_identity(sandbox):
    """
    The cross-meet contract: the same swimmer in a second meet keeps the same
    S-number (through the hytek name variant recorded by meet one), new
    swimmers get new IDs, and re-ingesting meet one afterwards disturbs
    nothing about meet two.
    """
    run(sandbox)  # meet 1

    src2 = os.path.join(sandbox["repo"], "sources", "meet2.txt")
    open(src2, "w").write(SECTION_B)
    cfg2 = dict(sandbox["cfg"], meet_id="TEST_MEET_2", meet_name="Test Meet 2",
                meet_date="2025-03-01", source_file="sources/meet2.txt")
    s2 = ingest(cfg2, repo=sandbox["repo"], raw_csv=sandbox["raw"],
                map_csv=sandbox["map"], verbose=False)
    assert s2["matches"] == 1 and s2["new_ids"] == 1  # Alpha matched, Epsilon new

    rows = list(csv.DictReader(open(sandbox["raw"])))
    alpha_ids = {r["swimmer_id"] for r in rows
                 if r["final_time"] in ("1:37.01", "1:36.20")}
    assert alpha_ids == {"S001"}, "same swimmer must keep one ID across meets"
    assert {r["meet_id"] for r in rows} == {"TEST_MEET", "TEST_MEET_2"}

    idmap = {r["swimmer_id"]: r for r in csv.DictReader(open(sandbox["map"]))}
    assert "TEST_MEET" in idmap["S001"]["meets"]
    assert "TEST_MEET_2" in idmap["S001"]["meets"]

    # re-ingesting meet 1 leaves the dataset content-identical (its rows are
    # replaced as a block and re-appended, so ORDER may change but no row may
    # appear, vanish, or drift)
    before = sorted(open(sandbox["raw"]).read().splitlines())
    run(sandbox)
    assert sorted(open(sandbox["raw"]).read().splitlines()) == before
    map_before = sorted(open(sandbox["map"]).read().splitlines())
    run(sandbox)
    assert sorted(open(sandbox["map"]).read().splitlines()) == map_before


def test_config_validation_names_missing_keys(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"meet_id": "X"}))
    with pytest.raises(SystemExit, match="missing required keys"):
        load_config(str(p))
