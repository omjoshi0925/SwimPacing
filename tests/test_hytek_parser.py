"""
Tests for the Hy-Tek results parser against a SYNTHETIC section written in the
exact format of the official files. Synthetic because the real retrieved
section lives in data/private/ (it contains names) and tests must not depend on
gitignored files.
"""

import pytest

from src.hytek_parser import parse_section, entries_to_raw_rows

SYNTHETIC = """Boys 200 Yard Freestyle
===============================================================================
              1:58.59  SRII
    Name                     Age Team                    Seed     Finals
===============================================================================
  1 Alpha, Test               16 AAAA-PC              1:36.64    1:37.01 SRII
       22.72    47.02  1:11.97  1:37.01
  2 Beta, Case B              15 BBBB-PC                   NT    1:42.63 SRII+
       24.33    50.11  1:16.19  1:42.63
  2 Gamma, Tie                17 CCCC-PC              1:45.00    1:42.63
       24.50    50.40  1:16.90  1:42.63
 -- Delta, Scratch            14 AAAA-PC              1:50.11        DFS
"""


def test_parses_the_synthetic_section():
    info, entries, problems = parse_section(SYNTHETIC)
    assert info == {"sex": "Boys", "event": "200 Yard Freestyle"}
    assert problems == []
    assert len(entries) == 4
    assert [e.completed for e in entries] == [True, True, True, False]


def test_fields_land_in_the_right_columns():
    _, entries, _ = parse_section(SYNTHETIC)
    e = entries[0]
    assert (e.name, e.age, e.team) == ("Alpha, Test", 16, "AAAA-PC")
    assert (e.seed, e.final) == ("1:36.64", "1:37.01")
    assert e.splits == ["22.72", "47.02", "1:11.97", "1:37.01"]


def test_nt_seed_and_tie_places_are_handled():
    _, entries, _ = parse_section(SYNTHETIC)
    assert entries[1].seed == "NT"
    assert entries[1].place == entries[2].place == "2"


def test_last_split_must_equal_final_or_it_is_a_problem():
    broken = SYNTHETIC.replace("  1:11.97  1:37.01\n", "  1:11.97  1:37.99\n", 1)
    _, _, problems = parse_section(broken)
    assert any("!= final" in p for p in problems)


def test_completed_entry_with_missing_splits_is_a_problem():
    broken = SYNTHETIC.replace("       24.50    50.40  1:16.90  1:42.63\n", "")
    _, _, problems = parse_section(broken)
    assert any("expected 4" in p for p in problems)


SPLITLESS = """Boys 15 & Over 200 Yard Freestyle
===============================================================================
    Name                     Age Team                    Seed     Finals
===============================================================================
    1 Balva, Arthur A           16 PASA-PC              1:46.59    1:42.37
     3 Tsang, Jonathan C                              16 PASA-PC                                1:48.20            1:47.13
   10 Conover-Hustis, Austin J 13 PASA-PC               2:04.02    2:11.05
"""


def test_splitless_sections_parse_under_require_splits_false():
    """
    Some official files publish final times only, and print-to-PDF renderings
    vary indent and squeeze the name-age gap to one space. All three entry
    layouts above occur verbatim in the BAC 2021 official file.
    """
    info, entries, problems = parse_section(SPLITLESS, require_splits=False)
    assert info == {"sex": "Boys", "event": "15 & Over 200 Yard Freestyle"}
    assert problems == []
    assert [e.name for e in entries] == ["Balva, Arthur A", "Tsang, Jonathan C",
                                         "Conover-Hustis, Austin J"]
    assert all(e.splits == [] for e in entries)


def test_splitless_sections_still_refuse_by_default():
    _, _, problems = parse_section(SPLITLESS)
    assert len(problems) == 3 and all("expected 4" in p for p in problems)


def test_partial_splits_are_a_problem_even_when_not_required():
    partial = SPLITLESS.replace(
        "    1 Balva, Arthur A           16 PASA-PC              1:46.59    1:42.37\n",
        "    1 Balva, Arthur A           16 PASA-PC              1:46.59    1:42.37\n"
        "       24.00    50.00\n")
    _, _, problems = parse_section(partial, require_splits=False)
    assert any("expected 4" in p for p in problems)


def test_rows_carry_schema_fields_and_skip_dfs():
    _, entries, _ = parse_section(SYNTHETIC)
    rows = entries_to_raw_rows(
        entries, meet_id="TEST", meet_name="Synthetic Meet",
        meet_date="2025-01-25", course="SCY", round_="timed_final",
        data_source="synthetic test fixture", sid_of=lambda n: "S999")
    assert len(rows) == 3  # DFS skipped
    r = rows[0]
    assert r["split_200"] == r["final_time"] == "1:37.01"
    assert r["age"] == "16" and r["course"] == "SCY"
    assert r["seed_time"] == "1:36.64"
    assert rows[1]["seed_time"] == ""  # NT -> missing, not fabricated
