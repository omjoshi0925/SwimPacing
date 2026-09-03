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

## pilot-v0.2  (2026-09-03)  — FROZEN; the registered analysis runs on this version

| | |
|---|---|
| Raw rows | 1382 (16 meet_ids, 841 anonymous identities) |
| Usable races | **345** (male 15-18, SCY, complete monotonic splits, 11 meets) |
| Unique swimmers among usable | 248; 60 swimmers with >1 usable race (157 races) |
| Age provenance among usable | 291 published, 54 club-linked (validation_plan amendment 2026-09-02); 0 link conflicts |
| Usable races with a pre-race PB | 110 (71 swimmers) — the H1 analysis set; PBs are derived in-file from earlier rows of the same identity (no PB is imported) |
| Rounds among usable | 268 timed finals, 57 prelims, 20 finals |
| Meet levels among usable | 282 invitational, 54 championship (high school NCS/CIF), 9 intrasquad |
| Split coverage (raw) | 832/1382 rows; the 550 split-less rows are SwimCloud final-time pages (449), BAC 2021 (66), Palooza 2025 (21, splits withheld, see exclusions), and timing gaps in official files (14) |
| 15 m start times | none published in any source |
| Frozen files | `data/raw/200_free_scy_raw.csv` sha256 `00f67f24c9f446ff256b40281b569a739618b1cdf707f1482d81952fad7e21c3`; `data/processed/200_free_scy_processed.csv` sha256 `c2a1929a3ea5f5308e833696775e7c53b03b597fffbdd0374cc1c6b85f433d6b` |

### Usable races by meet and provenance tier

Tier 1 = checksum-verified retrieval of the official results section
(browser extraction with recomputed length/hash checks, sha256 in the
integrity table below). Tier 2 = verified transcription: official file
identified, a third-party extraction admitted after independent
spot-verification against the official file (data_dictionary.md, provenance
tiers).

| meet_id | date | level | tier | usable | swimmers | age source | with PB |
|---|---|---|---|---|---|---|---|
| 2025_ORINDA_SC_SENIOR_OPEN | 2025-01-25 | invitational | 1 | 80 | 80 | published | 6 |
| 2025_ALTO_ROCK_THE_BLOCKS | 2025-03-29 | invitational | 2 | 14 | 8 | published | 0 |
| 2025_ORINDA_SC_SENIOR_OPEN_OCT | 2025-10-18 | invitational | 1 | 130 | 130 | published | 48 |
| 2025_BAC_SPOOKY_FALL | 2025-10-25 | invitational | 1 | 34 | 34 | published | 4 |
| 2025_ALTO_FALL_FROLIC | 2025-11-15 | invitational | 1 | 8 | 8 | published | 1 |
| 2025_ALTO_CANDY_CANE | 2025-12-19 | invitational | 1 | 16 | 16 | published | 4 |
| 2026_PASA_SUMMER_PALOOZA | 2026-07-26 | intrasquad | 1 | 9 | 6 | published | 9 |
| 2024_NCS_CHAMPIONSHIPS | 2024-05-03 | championship | 2 | 10 | 7 | club-linked | 0 |
| 2024_CIF_STATE_CHAMPIONSHIPS | 2024-05-09 | championship | 2 | 2 | 2 | club-linked | 1 |
| 2025_NCS_CHAMPIONSHIPS | 2025-05-09 | championship | 2 | 23 | 15 | club-linked | 18 |
| 2026_NCS_CHAMPIONSHIPS | 2026-05-07 | championship | 1 | 19 | 19 | club-linked | 19 |

Raw-only meets (final times, PB history and identity linkage only; no
usable races): 2021_BAC_SPOOKY_FALL (66, official file publishes no splits),
2025_PASA_SUMMER_PALOOZA (21, see exclusions), 2026_PC_CAL_INVITATIONAL
(121), 2026_PC_SC_SENIOR_OPEN (162), 2026_PC_TERA_FAR_WESTERN (166)
(SwimCloud pages, final times only).

### Exclusions and withheld sources (decided before the freeze)

- **ALTO Valentine Invitational 2026** (workbook meet): the workbook's rows
  were contradicted by the official results file on independent check, so
  the meet was NOT ingested. It can be admitted later from the official PDF.
- **PASA Summer Palooza 2025** (workbook meet): laps 3 and 4 appear
  transposed in the extraction, so only final times were ingested
  (`splits: blank`); the 21 rows feed PB history only.
- **TCA and TERA meets in the workbook**: official files not yet obtained;
  not ingested. Upgrade path: attach the official PDFs, verify, add a config.
- **Age-inconsistent same-name match**: one workbook entry (age 15,
  unattached) shared a normalized name with an existing identity whose
  published ages elsewhere make that impossible; the age-aware matcher split
  it into its own identity (map note "distinct person from S###"). This
  removed one spurious pre-race PB relative to the pre-fix state.
- Pre-registered exclusions (validation_plan §10) applied in
  `src/preprocessing.py`; counts are in `results/validation/report_v0_2.md`.

### Changes from pilot-v0.1

Eleven additional meets; the club-linked age rule; the start-transform sign
correction (validation_plan §7 amendment (a)); age-aware identity matching.
pilot-v0.1's `results/validation/pilot_report.md` is preserved unchanged and
its calibration anchors remain pinned in `tests/test_calibration.py`.

## Source integrity (public record of private sources)

The verbatim sources live in `data/private/` and are never published; their sha256 digests are public, so anyone re-retrieving the official page can verify the dataset was built from the genuine file.

| meet_id | source file | sha256 | rows | ingested |
|---|---|---|---|---|
| 2025_ORINDA_SC_SENIOR_OPEN | orinda_2025-01-25_boys_200_free.txt | `f1dd9fd3532349e78814c13547be354799067f0e1138df90a69d8e113b61b7c1` | 132 | 2026-09-02 |
| 2026_PASA_SUMMER_PALOOZA | palooza_2026-07-26_boys200free_prelims.txt | `e1bd7d29f25ef905288a2dbd87f1314285c0bb578ded82579fd0eb9fc549ca7b` | 10 | 2026-09-03 |
| 2026_PASA_SUMMER_PALOOZA | palooza_2026-07-26_boys200free_afinal.txt | `c9d6efc99d2548903684435c878299d7548093add59eaa14a3cbfeb126eee3c5` | 6 | 2026-09-03 |
| 2026_NCS_CHAMPIONSHIPS | ncs_2026-05-07_boys200free_prelims.txt | `46f3e376765d18331c1e0c0376c6d41e932f66e73f4dcf822f62fb70ba40ab25` | 41 | 2026-09-03 |
| 2021_BAC_SPOOKY_FALL | bac_2021-10-23_boys1314_200free.txt | `461b282708ee41e55fb69b46a68657a2d0751dcc0de328948542038ff7086a4b` | 24 | 2026-09-03 |
| 2021_BAC_SPOOKY_FALL | bac_2021-10-23_boys15over_200free.txt | `ce06079b869adf640a3e8027b7345ebedbfd4075d3b7b66a0042d3ae51ef04a2` | 42 | 2026-09-03 |
| 2025_ORINDA_SC_SENIOR_OPEN_OCT | orinda_2025-10-18_men_200_free.txt | `f3a09ee6231f80b259e0c0617673f4280751f0894d9bc1f93bad008e5b766a62` | 163 | 2026-09-03 |
| 2025_BAC_SPOOKY_FALL | bac_2025-10-25_boys11over_200free.txt | `b757e70fa1000d1f8aae7ba4dfcc009f0e18bba1da1b1be8d39cf35601ea0925` | 103 | 2026-09-03 |
| 2025_ALTO_FALL_FROLIC | alto_2025-11-15_boys11over_200free_a.txt | `5a29f8c0f0edd9b2391c429b2bee0c4673e201d1ddfb64c0d0995b9f3fce46a5` | 42 | 2026-09-03 |
| 2025_ALTO_FALL_FROLIC | alto_2025-11-15_boys11over_200free_b.txt | `976703beaf5c9d616386261184445098a067f43136b053ddba2f52eaf248bc2e` | 8 | 2026-09-03 |
| 2025_ALTO_CANDY_CANE | alto_2025-12-19_boys11over_200free.txt | `aaa461d7f4bf262eced3303d1abb2bf029eb09598f664fc9cfca6004ccd46f7c` | 40 | 2026-09-03 |
| 2025_NCS_CHAMPIONSHIPS | mens_200_free_scy_meets_2026-09-02.xlsx [NCS Championships 2025] | `079024f19964c615ca7dc0e87ac6f7dfccafd059d715d39d6e9ddcde9fae88e6` | 55 | 2026-09-03 |
| 2024_NCS_CHAMPIONSHIPS | mens_200_free_scy_meets_2026-09-02.xlsx [NCS Championships 2024] | `079024f19964c615ca7dc0e87ac6f7dfccafd059d715d39d6e9ddcde9fae88e6` | 56 | 2026-09-03 |
| 2024_CIF_STATE_CHAMPIONSHIPS | mens_200_free_scy_meets_2026-09-02.xlsx [CIF State Championships] | `079024f19964c615ca7dc0e87ac6f7dfccafd059d715d39d6e9ddcde9fae88e6` | 58 | 2026-09-03 |
| 2025_ALTO_ROCK_THE_BLOCKS | mens_200_free_scy_meets_2026-09-02.xlsx [ALTO Rock the Blocks Invitational] | `079024f19964c615ca7dc0e87ac6f7dfccafd059d715d39d6e9ddcde9fae88e6` | 132 | 2026-09-03 |
| 2025_PASA_SUMMER_PALOOZA | mens_200_free_scy_meets_2026-09-02.xlsx [PASA Summer Palooza Championships] | `079024f19964c615ca7dc0e87ac6f7dfccafd059d715d39d6e9ddcde9fae88e6` | 21 | 2026-09-03 |
