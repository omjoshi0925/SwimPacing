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

## Expansion toward pilot-v0.2 (IN PROGRESS, not frozen)

Status 2026-09-02, after ingesting the 2026 PASA Summer Palooza (16 rows,
prelims + A-final, ages published) and the 2026 NCS Championships Boys 200
Free prelims (41 rows, grades published, ages blank):

| | |
|---|---|
| Raw rows | 638 |
| Usable races | 100 (80 Orinda + 9 Palooza + 11 NCS via the club-linked age amendment of 2026-09-02) |
| Age provenance among usable | 89 published, 11 club-linked ([lo, hi] fully inside 15-18; 2 linkable NCS rows excluded, ages 19/14 possible; 0 link conflicts) |
| Swimmers with >1 usable race | 12 |
| Usable races with a pre-race PB | 15 (H1 minimally covered for the first time) |

`results/validation/pilot_report.md` remains the frozen **pilot-v0.1**
analysis (80 races); the processed CSV now reflects the expansion in
progress. The registered fits and held-out comparison wait for the v0.2
freeze (~250 usable races).

## Source integrity (public record of private sources)

The verbatim sources live in `data/private/` and are never published; their sha256 digests are public, so anyone re-retrieving the official page can verify the dataset was built from the genuine file.

| meet_id | source file | sha256 | rows | ingested |
|---|---|---|---|---|
| 2026_PASA_SUMMER_PALOOZA | palooza_2026-07-26_boys200free_prelims.txt | `e1bd7d29f25ef905288a2dbd87f1314285c0bb578ded82579fd0eb9fc549ca7b` | 10 | 2026-09-02 |
| 2026_PASA_SUMMER_PALOOZA | palooza_2026-07-26_boys200free_afinal.txt | `c9d6efc99d2548903684435c878299d7548093add59eaa14a3cbfeb126eee3c5` | 6 | 2026-09-02 |
| 2026_NCS_CHAMPIONSHIPS | ncs_2026-05-07_boys200free_prelims.txt | `46f3e376765d18331c1e0c0376c6d41e932f66e73f4dcf822f62fb70ba40ab25` | 41 | 2026-09-02 |
| 2025_ORINDA_SC_SENIOR_OPEN | orinda_2025-01-25_boys_200_free.txt | `f1dd9fd3532349e78814c13547be354799067f0e1138df90a69d8e113b61b7c1` | 132 | 2026-09-02 |
| 2021_BAC_SPOOKY_FALL | bac_2021-10-23_boys1314_200free.txt | `461b282708ee41e55fb69b46a68657a2d0751dcc0de328948542038ff7086a4b` | 24 | 2026-09-02 |
| 2021_BAC_SPOOKY_FALL | bac_2021-10-23_boys15over_200free.txt | `ce06079b869adf640a3e8027b7345ebedbfd4075d3b7b66a0042d3ae51ef04a2` | 42 | 2026-09-02 |
