# Dataset versions

## pilot-v0.1  (2026-08-31)

| | |
|---|---|
| Raw rows | 581 |
| Usable races | 80 |
| Unique swimmers (raw / usable) | 453 / 80 |
| Meets | 4 sources: Orinda SC Senior Open Jan 2025 (official Hy-Tek, WITH splits); Pacific Swimming SC Senior Open Oct 2025, PC Cal Invitational Jan 2026, PC TERA Far Western Jul-Aug 2026 (SwimCloud pages, final times only) |
| Usable population | male 15-18, SCY, timed finals, one meet |
| Split coverage | 132/581 rows (22.7%), all from the official Hy-Tek source |
| Age coverage | 132/581 rows (SwimCloud publishes no ages) |
| pre_race_pb coverage | 94/581 rows, all derived in-file from cross-meet identity matches; 0/80 usable rows (the split-bearing meet is the earliest in the file, so H1 is untestable on this version) |
| 15 m start times | none published in any source |
| Known biases | single region (Pacific Swimming); senior-open field filtered to 15-18 selects committed club swimmers; the split-bearing meet is one weekend in one pool |
| Frozen | data/raw/200_free_scy_raw.csv at this date; subsequent changes require a new version entry here |

Exclusion counts and reasons: see `results/validation/pilot_report.md`.
Verbatim sources with names: `data/private/` (gitignored, never published).
Anonymization: S### identifiers, cross-source identity matched on normalized
name; map in `data/private/swimmer_id_map.csv`.

Planned pilot-v0.2: 200-300 races across several meets via `src/hytek_parser.py`
on official pacswim.org results, prioritizing repeated swimmers so pre-race PBs
and the mixed-effects structure become available.
