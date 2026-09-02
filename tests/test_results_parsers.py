"""
Tests for the additional results-format parsers (src/results_parsers.py):
happy paths on synthetic fixtures, and — the important part — refusal on
arithmetic inconsistencies, because these formats' redundancy is the built-in
transcription check the ingest protocol relies on.
"""

from src.results_parsers import parse_hs_champ_section, parse_lap_section

LAP = """#7 Boys 13&O 200 Yard Free
Round: Preliminaries
  1 Alpha, Test              16  AAAA-PC  1:40.00
       24.00   25.00   25.50   25.50
  2 Beta, Case               15  BBBB-PC  1:44.10
       24.90   26.00   26.60   26.60
"""

HS = """Boys 200 Yard Freestyle
Round: Preliminaries
  1 Test Alpha           JR  Some School  1:40.00  CIFA
       24.00   49.00 (25.00)   1:14.50 (25.50)   1:40.00 (25.50)
 *2 Case Beta            --  Other School  1:44.10
       24.90   50.90 (26.00)   1:17.50 (26.60)   1:44.10 (26.60)
"""


def test_lap_format_parses_and_converts_to_cumulative():
    info, entries, problems = parse_lap_section(LAP)
    assert info == {"sex": "Boys", "event": "200 Yard Free"}
    assert problems == []
    assert len(entries) == 2
    e = entries[0]
    assert (e.name, e.age, e.team, e.final) == ("Alpha, Test", 16, "AAAA-PC",
                                                "1:40.00")
    assert e.splits == ["24.00", "49.00", "1:14.50", "1:40.00"]


def test_lap_format_refuses_when_laps_do_not_sum_to_final():
    broken = LAP.replace("25.50   25.50", "25.50   26.50", 1)
    _, entries, problems = parse_lap_section(broken)
    assert any("!= final" in p for p in problems)
    assert len(entries) == 1  # the intact entry still parses


def test_hs_format_parses_grades_ties_and_blank_grades():
    info, entries, problems = parse_hs_champ_section(HS)
    assert info == {"sex": "Boys", "event": "200 Yard Freestyle"}
    assert problems == []
    a, b = entries
    assert a.age is None and "grade JR" in a.tags and "CIFA" in a.tags
    assert a.splits == ["24.00", "49.00", "1:14.50", "1:40.00"]
    assert b.place == "2" and "grade --" in b.tags  # tie asterisk stripped
    assert b.team == "Other School"


def test_hs_format_refuses_internal_inconsistency():
    broken = HS.replace("1:14.50 (25.50)", "1:14.50 (25.90)", 1)
    _, entries, problems = parse_hs_champ_section(broken)
    assert any("inconsistency" in p for p in problems)
    assert len(entries) == 1


def test_hs_format_refuses_when_last_cumulative_misses_final():
    broken = HS.replace("1:40.00 (25.50)", "1:40.10 (25.60)", 1)
    _, entries, problems = parse_hs_champ_section(broken)
    assert any("!= final" in p for p in problems)


def test_entry_without_split_line_is_a_problem():
    truncated = "\n".join(LAP.splitlines()[:3]) + "\n"
    _, entries, problems = parse_lap_section(truncated)
    assert entries == []
    assert any("without split line" in p for p in problems)
