# Atomic commit roadmap

Plan for every remaining legitimate atomic commit in this project, in dependency
order. Written 2026-09-01 against the base state below. Each row is one commit:
one logical change, independently understandable, leaving the tree buildable.

**Base state (certified).** The "Pilot empirical validation" commit: 88 tracked
files, full test suite green (108 passed, 123 s). Everything below builds on
that tree, each change on the previous one, never re-branched from base.

## Delivery protocol

Each change arrives as `Change_NNN.zip` containing only added/modified files at
repo-root-relative paths, plus one paste block that overlays it onto
`~/Documents/GitHub/SwimPacing` and removes any deleted files, plus the change
report (files touched, what changed, why it is one commit, build/test status)
and the exact commit message. One change at a time; the next starts only after
the commit is confirmed. `data/private/` (real names, verbatim source text)
never appears in any deliverable.

**Build/test definition for this project.** "Builds" means the full pytest
suite passes and every script a change touches runs cleanly. Changes that alter
results or figures include the regenerated outputs in the same commit, since a
result and the code that made it belong together.

## Ground rules

1. No manufactured commits: no whitespace churn, no rename-and-rename-back, no
   splitting a single logical change across commits just to inflate the count.
   Where execution shows a planned row is too thin to stand alone, it merges
   into its neighbor and the roadmap is annotated, not padded.
2. Every commit leaves a valid checkpoint: suite green, scripts runnable, docs
   consistent with code.
3. Numbering below is the planning sequence. Bands may interleave where the
   dependency column allows; numbers then shift but titles stay stable.
4. Gates: **[DATA]** needs new source material (official results pulled in a
   session with browser access, or files provided); **[ORDER]** is locked by the
   pre-registered validation plan and cannot be moved earlier.

## Integrity constraints the ordering enforces

- The held-out test set (25% of swimmers, seed 20260829) stays untouched until
  the registered evaluation in band G. Nothing in bands A-F reads it.
- Fits on pilot-v0.1 (band D) are **exploratory**, labeled as such everywhere;
  the registered fits happen once on the expanded frozen dataset (band G).
- Fitted parameters are estimates, never described as measured physiology.
- Poor models stay in every comparison table. Null results get reported.

## Band summary

| Band | Theme | Commits | Gate |
|---|---|---|---|
| A | Infrastructure and CI | 001-008 | none |
| B | Start term as a model parameter | 009-016 | none |
| C | Calibration machinery (synthetic-verified) | 017-028 | none |
| D | Exploratory pilot fits | 029-034 | none |
| E | Multi-meet ingest tooling | 035-040 | none |
| F | Dataset expansion to 200-300 races | 041-058 | [DATA] |
| G | Registered fits, held-out comparison, stats | 059-072 | [ORDER] after F |
| H | Literature completion | 073-082 | none |
| I | Paper | 083-098 | empirical sections after G |
| J | Code quality and documentation | 099-106 | as discovered |

---

## Band A — Infrastructure and CI (001-008)

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 001 | docs | add atomic commit roadmap | `ATOMIC_COMMIT_ROADMAP.md` | record the plan this history follows | none |
| 002 | test | add quick/slow pytest markers | `pytest.ini`, `tests/test_model.py`, `tests/test_pipeline.py` | tag the minute-scale ODE tests so a fast subset exists for CI and local iteration | none |
| 003 | build(ci) | add GitHub Actions workflow running the quick suite on push | `.github/workflows/tests.yml` | every future commit gets verified buildable automatically, which is what makes 100+ small commits safe | 002 |
| 004 | build | pin exact dependency versions | `requirements.txt` | reproducibility of every number in the repo across machines | none |
| 005 | docs | add CI badge and correct quickstart runtimes | `README.md` | surface build status; README now states the measured 123 s suite time | 003 |
| 006 | docs | add CITATION.cff | `CITATION.cff` | makes the repo citable, consistent with the paper goal | none |
| 007 | chore | add .gitattributes | `.gitattributes` | LF normalization and CSV-as-data hints, prevents cross-platform diff noise in race data | none |
| 008 | docs | add developer workflow doc | `DEV_WORKFLOW.md` | one place recording how to verify a checkpoint (test tiers, script order, what regenerates what) | 002 |


**Executed in full, one commit per row (annotation 2026-09-04, from git log).**
001 `58c47dd`, 002 `796a8df`, 003 `c563278`, 004 `ab68d61`, 005 `00f705b`,
006 `d6b5df5`, 007 `ab7eb9e`, 008 `3f9d572`.

## Band B — Start term as a first-class model parameter (009-016)

This band promotes the start credit from a constant buried in analysis code to
a model parameter with provenance, without yet fitting it.

**Re-scoped during execution (2026-09-01).** The 009-010 audit found a sign
error: the pipeline subtracted the start credit from observed lap 1 (the
model-side transform applied to the data), double-counting it. Rows 011-016
became the fix arc: 011 pipeline sign fix + regenerated dataset, 012 corrected
observed strategy shapes + downstream theoretical outputs, 013 corrected
empirical analysis + regenerated pilot report and figures, 014 RESULTS/README
amendments, 015 validation-plan amendment + registered band extension to
3.4 s, 016 parameter/model docs. The originally planned rows 011-016
(invariant tests, observed-space helper adoption, prediction pins) fold into
band C where the calibration loss makes them load-bearing.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 009 | feat(model) | add start_credit to course parameters | `src/parameters.py` | one source of truth for S with Category B provenance (literature band 1.2-2.8 s, working 1.80) | none |
| 010 | refactor(model) | route all start handling through one helper | `src/model.py`, `scripts/empirical_analysis.py` | removes the duplicated START_OFFSET_S constant; apply_start_offset becomes the only path | 009 |
| 011 | test(model) | pin start-term invariants | `tests/test_model.py` | race time invariant, P1 shifted by exactly S/T, corrected metrics consistent; guards the refactor | 010 |
| 012 | docs | parameters.md entry for start_credit | `docs/parameters.md` | provenance table row + change log for a load-bearing number | 009 |
| 013 | feat(model) | observed-space prediction helper | `src/model.py` | single function mapping a model's raced shape into observed-split space (adds S to lap 1) for pipeline and figures alike | 010 |
| 014 | refactor(pipeline) | use the helper in model_predictions | `src/preprocessing.py` | deduplicates the mapping so figures and per-race deviations can never drift apart | 013 |
| 015 | test(pipeline) | pin observed-space shapes for M0-M4 | `tests/test_pipeline.py` | freezes the comparison surface at S = 1.80 to six decimals | 013 |
| 016 | docs | document raced vs observed shape spaces | `docs/model_definitions.md`, `docs/RESULTS.md` | both prediction tables published in both spaces, with the distinction stated once, clearly | 013 |
## Band C — Calibration machinery, synthetic-verified (017-028)

Task 14's tooling, built and tested entirely on synthetic data so that when the
real fits run they are one audited command. No real race is fitted in this band.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 017 | feat(calibration) | new module with the registered loss | `src/calibration.py` | RMSE of split proportions (the pre-registered primary metric) as importable code | none |
| 018 | test(calibration) | loss reproduces the pilot report table | `tests/test_calibration.py` | ties the new code to already-published numbers before anything is fitted | 017 |
| 019 | feat(calibration) | bounded 1-D fitter for beta_x | `src/calibration.py` | M3's parameter, closed-form inner solve, cheap and exact | 017 |
| 020 | test(calibration) | synthetic recovery of beta_x | `tests/test_calibration.py` | generate splits from a known beta_x, refit, recover within tolerance | 019 |
| 021 | feat(calibration) | fitter for gamma with restart ladder | `src/calibration.py` | M4's parameter, ODE inner solve, the n_starts 2-then-5 ladder from the recalibration work | 017 |
| 022 | test(calibration) | synthetic recovery of gamma | `tests/test_calibration.py` | same recovery check for the expensive model | 021 |
| 023 | feat(calibration) | fitter for beta_E | `src/calibration.py` | M2 stays in the contest even though the pilot sign-contradicts it; hiding poor models is forbidden | 017 |
| 024 | test(calibration) | synthetic recovery of beta_E | `tests/test_calibration.py` | recovery check | 023 |
| 025 | feat(calibration) | fit-report writer | `src/calibration.py` | every fit run writes params, train RMSE, n, seed, dataset version: an audit trail | 019,021,023 |
| 026 | feat(calibration) | fitting CLI with train-only guard | `scripts/fit_models.py` | the only sanctioned entry point; loads the swimmer-grouped split at seed 20260829 and refuses test rows structurally | 025 |
| 027 | test(calibration) | leakage guard test | `tests/test_calibration.py` | feeding a test-set row raises; the pre-registration rule enforced in code, not etiquette | 026 |
| 028 | docs | calibration protocol doc | `docs/calibration.md` | what is fitted (beta_E, beta_x, gamma), what stays frozen (E0, R, phi trade off in one equation), exploratory vs registered runs | 026 |


**Executed in full, one commit per row (annotation 2026-09-04, from git log).**
017 `97ee39f`, 018 `5acbe6d`, 019 `32b0499`, 020 `5220fb5`, 021 `9f16676`,
022 `af98dbb`, 023 `23e9b1f`, 024 `8b16fb0`, 025 `d1bf729`, 026 `2c91f71`,
027 `4d4e461`, 028 `549dae6`.

## Band D — Exploratory fits on pilot training rows (029-034)

Labeled exploratory everywhere: pilot-v0.1 is one meet, and the registered
comparison is defined on the expanded dataset. These fits inform priors and
surface the start-credit confound early. Test rows untouched.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 029 | results | exploratory fit run on pilot train rows | `results/validation/fits_train_pilot.csv` | first fitted beta_x, gamma, beta_E values with audit metadata | 026 |
| 030 | feat(viz) | figure emp05, observed vs fitted shapes | `scripts/empirical_analysis.py`, `figures/empirical/emp05*` | the fitted-model picture next to the fixed-parameter one | 029 |
| 031 | docs | exploratory-fit section in the pilot report | `results/validation/pilot_report.md` | values plus the confound check: how fitted beta_x moves across the 1.2-2.8 s start band | 029 |
| 032 | test | fit determinism pin | `tests/test_calibration.py` | same seed, same data, same fitted values; prevents silent drift | 029 |
| 033 | docs | status update in README and RESULTS | `README.md`, `docs/RESULTS.md` | user-facing state of the project advances with the work | 031 |
| 034 | docs | validation plan log entry for the exploratory run | `docs/validation_plan.md` | pre-registration hygiene: declared as exploratory, not the registered analysis | 029 |


**Executed in full, one commit per row (annotation 2026-09-04, from git log).**
029 `2647efd`, 030 `1b8fe76`, 031 `5eb1a0a`, 032 `c9c75ab`, 033 `a4cfb14`,
034 `8878760`.

## Band E — Multi-meet ingest tooling (035-040)

The Orinda ingester generalized so each future meet is configuration, not code.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 035 | refactor(ingest) | generalize the Hy-Tek ingester to per-meet configs | `scripts/ingest_hytek.py` (new), `scripts/ingest_hytek_orinda.py` (becomes a config) | scales ingestion to N meets with cross-meet swimmer identity intact | none |
| 036 | test(ingest) | config parsing and idempotent re-ingest | `tests/test_ingest.py` | re-running an ingest cannot duplicate rows; fixture-based | 035 |
| 037 | feat(ingest) | public integrity record per source | `scripts/ingest_hytek.py`, `data/DATASET_VERSIONS.md` | checksums of private source text published without the text, so provenance is verifiable while names stay private | 035 |
| 038 | docs(data) | multi-meet collection protocol | `data/data_dictionary.md` | the browser-extraction and verification workflow written down as a procedure | 035 |
| 039 | feat(ingest) | meet config template | `configs/meets/TEMPLATE.yml` | reproducible per-meet setup: meet_id, date, course, source path, checksums | 035 |
| 040 | test(ingest) | two-meet merge fixture test | `tests/test_ingest.py` | proves cross-meet identity matching and PB derivation across meets on synthetic data | 036 |


**Executed in full (annotation 2026-09-04, from git log).** 035 `04b0781`
(and `ingest_hytek_orinda.py` was retired as planned; Orinda is now two
configs), 036 `2a662cc`, 037 `8958ce4`, 038 `db3fe2e`, 040 `93a508a`.

**Row 039 landed in a different shape.** `c7d2d98` delivered
`configs/meets/TEMPLATE.json`, not the planned `TEMPLATE.yml` — the per-meet
config system is JSON throughout (`load_config` in `scripts/ingest_hytek.py`,
ten configs in `configs/meets/`). Same purpose, different format; the planned
row text above is left as written.

## Band F — Dataset expansion to 200-300 races (041-058) [DATA]

Each meet lands as two commits: the raw ingest, then the processed refresh with
quality-flag counts. Planned nominally for six meets; the band grows or shrinks
with what the official sources actually yield. Prioritizes meets with swimmers
already in the dataset, so pre-race PBs and repeated-swimmer structure appear.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 041 | data | ingest meet 2 raw rows | `data/raw/`, `configs/meets/` | new races enter under the same verification protocol as Orinda | 035, [DATA] |
| 042 | data | refresh processed dataset after meet 2 | `data/processed/`, `results/validation/` | flags, metrics, updated counts in one auditable step | 041 |
| 043-054 | data | meets 3 through 8, same two-commit pattern | as above | each meet independently reviewable | pairwise |
| 055 | data | freeze pilot-v0.2 | `data/DATASET_VERSIONS.md` | the registered analysis dataset, frozen before any fit touches it | 041-054 |
| 056 | docs(data) | dataset summary statistics | `data/DATASET_VERSIONS.md`, `results/validation/` | races, swimmers, repeats, PB availability, flag rates for the paper's data section | 055 |
| 057 | feat(pipeline) | PB-availability report | `src/preprocessing.py` or `scripts/` | counts of races with usable pre-race PBs, which decides whether H1 is testable | 055 |
| 058 | docs | validation plan annotation: dataset frozen | `docs/validation_plan.md` | records the freeze date and version the registered run will cite | 055 |

**Rows 041-054 landed in a different shape (annotation 2026-09-04).** Planned
as two commits per meet across ~6 meets; executed as TWO commits covering
fifteen meets: `af07cd9` (two meets via new parsers and the club-linked age
rule) and `bccb4db` (splitless-source support, BAC 2021 PB-history rows, the
collection manifest). pilot-v0.2 counts 16 meet_ids, 11 with usable races,
and three workbook meets excluded on record (`data/DATASET_VERSIONS.md`).
The per-meet two-commit pattern above describes a plan execution outgrew,
and is left as written.

**Row 057 has no standalone artifact.** The PB-availability counts live in
the exclusion funnel of `results/validation/report_v0_2.md` ("usable with
pre-race PB: 110") and the per-meet "with PB" column of
`data/DATASET_VERSIONS.md`. Reading those as row 057 is an INFERRED fold — a
judgment about where the planned content ended up, not a commit that names
the row — and is recorded as exactly that.

## Band G — Registered fits, held-out comparison, statistics (059-072) [ORDER]

The pre-registered analysis, run exactly once on the frozen expanded dataset.
Order locked by `docs/validation_plan.md`.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 059 | feat(validation) | held-out evaluation script | `scripts/evaluate_holdout.py` | loads frozen fits and test rows, computes registered metrics; refuses to run on stale or missing fits | 026, 055 |
| 060 | test(validation) | evaluator on a synthetic frozen fixture | `tests/test_validation.py` | the registered command proven correct before it ever sees real test rows | 059 |
| 061 | results | registered training-set fits | `results/validation/fits_train.csv` | Task 14 proper, on pilot-v0.2 train rows only | 059 |
| 062 | results | registered held-out comparison | `results/validation/holdout_comparison.csv` | Task 15: one table, all five models, the primary metric, no retuning after | 061 |
| 063 | feat(viz) | held-out comparison figures | `scripts/empirical_analysis.py` | code for the final comparison plots | 062 |
| 064 | results | generated held-out figures | `figures/empirical/` | outputs committed beside the numbers they draw | 063 |
| 065 | docs | RESULTS.md empirical section rewrite | `docs/RESULTS.md` | the registered outcome, winners and losers both | 062 |
| 066 | docs | validation plan completion annotations | `docs/validation_plan.md` | what ran, exactly as registered, plus any logged amendments | 062 |
| 067 | feat(stats) | bootstrap CIs for RMSE differences | `src/stats.py`, `tests/test_stats.py` | uncertainty on the model ranking, swimmer-level resampling | 062 |
| 068 | results | CI table and figure | `results/validation/`, `figures/empirical/` | the ranking with error bars | 067 |
| 069 | feat(stats) | H1 test implementation | `src/stats.py`, `tests/test_stats.py` | deviation-from-optimal vs performance, PB-normalized, synthetic-tested | 057 |
| 070 | results | H1 outcome | `results/validation/` | the registered hypothesis test, or a documented untestable status with counts | 069 |
| 071 | feat(stats) | mixed-effects model | `src/stats.py` | random swimmer intercepts over repeated swims, statsmodels | 055 |
| 072 | results | mixed-effects report | `results/validation/` | within- vs between-swimmer pacing variance | 071 |


**Rows 068 and 072 have no standalone artifacts (annotation 2026-09-04).**
The bootstrap CIs of 068 are columns of
`results/validation/model_comparison.csv` (`RMSE_ci_lo/hi`, `diff_ci_lo/hi`)
and the §comparison table of `report_v0_2.md`; the mixed-effects report of
072 is the `RE var` / `resid var` columns of the H1 table in the same report,
fitted via `src/stats.py`. Both readings are INFERRED folds — judgments about
where the planned content ended up, not commits naming the rows — recorded as
exactly that. The 2026-09-03 execution note covers the band's ordering.

## Band H — Literature completion (073-082)

Each commit is preceded by verification in-session under the standing policy:
found and confirmed, access level recorded, nothing reconstructed from memory.
A planned row that finds no verifiable source becomes a documented gap, not a
fabricated entry.

**Executed 2026-09-01 (annotation added 2026-09-03).** Rows 073, 074 and 075
landed in the 2026-09-01 literature pass, recorded in `docs/parameters.md`
under "What the turn literature implies phi should be" (Cuenca-Fernandez 2022,
Born 2021, Born 2022, Veiga 2022; derived band phi in 0.80-0.95). The band
table below was never updated. Band H therefore has 7 remaining rows, not 10.
Row 078's planned title also carried a citation error, corrected in that row.

**Further annotation 2026-09-03.** Rows 078 and 079 were also already done.
keller1973theory, keller1974optimal and maronski1996minimum were in
`literature/references.bib` before this session; re-executing them appended
duplicate keys and broke the paper build. Band H has 5 remaining rows, not 7.
The bibliography, not this table, is the source of truth for what has been
cited. Check it before executing any literature row.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 073 | docs(lit) | turn-time contribution sources | `literature/references.bib`, `literature/literature_review.csv`, `docs/literature_notes.md` | the biggest remaining gap; what phi stands in for | none |
| 074 | docs(lit) | underwater and breakout speed sources | same trio | second half of the turn story | none |
| 075 | docs(lit) | synthesis: what turns imply phi should be | `docs/literature_notes.md`, `docs/parameters.md` | converts sourced turn values into an expected phi band, testable against the calibrated one | 073,074 |
| 076 | docs(lit) | numeric critical speed and W' values | trio | open-access route to the CS/W' numbers already identified but paywalled | none |
| 077 | docs(lit) | CS/W' plausibility check against R and E0 | `docs/parameters.md` | ties the engine block to an independent literature anchor | 076 |
| 078 | docs(lit) | Keller 1974 verified entry | trio, `docs/01_derivation.md` | positions M4 in the Keller line with a verified citation | none |
| 079 | docs(lit) | optimal control in endurance sport entries | trio | positions the paper against the running literature | none |
| 080 | docs(lit) | adolescent-specific energetics additions | trio | strengthens the population match of R and E0 if sources exist | none |
| 081 | chore(lit) | regenerate review CSV and coverage table | `literature/literature_review.csv`, `docs/literature_notes.md` | counts and coverage status refreshed once the passes land | 073-080 |
| 082 | docs | assumptions.md updates from new literature | `docs/assumptions.md` | tier assignments revisited where evidence changed | 081 |

**Row 082 executed partially 2026-09-03, ahead of its 081 dependency.** The
provenance summary in `docs/assumptions.md` had drifted from `parameters.md`
(`tau` at the superseded 20 s, PROVENANCE GAP on `tau` and `R` after the
2026-08-31 passes closed them, the pre-`Course` start-credit name), and A1/A3
predated the turn and economy-decay sources. Those are fixed. What still waits
on 081: no coverage or count claim in `assumptions.md` was touched, since those
are what the regenerated `literature_review.csv` will settle. No Tier 1/2/3
assignment moved; A3 gained contrary evidence but stays Tier 1.

**Row 081 executed 2026-09-04, and row 082 is complete after all.** 081 turned
out to be one row, not a regeneration: `sousa2014vo2kinetics` was the only bib
key missing from `literature_review.csv`, and the CSV and `references.bib` now
hold the same 48 keys. The coverage tally was recounted from the CSV's own
`access_level` column and was wrong independently of the missing row — it read
47 sources as 24/15/8 where that column gave 24/16/7; it is now 48 as 24/17/7.

Row 082's reserved remainder does not exist. It was held back for the coverage
and count claims 081 would settle, but `assumptions.md` makes no count or
coverage claim anywhere, so `d771a6a` was the whole row rather than a partial
one. Not padded into a second commit.

**Rows 076 and 080 were also already executed** and never annotated: 076 in
`8fe79b4` (CS/W' recorded as a characterized gap, the documented-gap outcome
this band's preamble allows) and 080 in `f7b9127` (adolescent energetics
sources). Band H therefore has ONE row left, 077, blocked on paywalled access
to Zacca et al. (2010). That is the third time this table has been found
behind the commits; treat `references.bib` and the git log as the record.


**Refinement, 2026-09-04, after a full ledger sweep.** Three claims above
need sharpening. Row 077 is HALF done: the dimensionless CS/v200 plausibility
check landed 2026-09-02 in `5d05ee4` (model 0.893 vs measured 0.898,
`docs/parameters.md`); what stays open, blocked on Zacca et al. (2010), is
the W'-in-joules half — and the notes record that no swimming W' in joules
exists anywhere reached. Rows 081 and 082 each executed TWICE: 081 as a proto
coverage refresh in `a39eef4` (2026-09-02, 47 sources, before row 080
existed), completed by `66e4247` (2026-09-04); 082 as the Tier-1 prose
updates of `b5e4aff` (2026-09-02, measured turn shares, the oscillation
counterpoint), completed by the provenance-table reconcile of `d771a6a`
(2026-09-04).

## Band I — Paper (083-098)

LaTeX lives in `paper/`, one section per commit, drawing on
`literature/references.bib`. Theory sections can start any time; empirical
sections wait for band G.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 083 | docs(paper) | LaTeX scaffold | `paper/main.tex`, `paper/sections/` | compilable skeleton wired to the shared .bib | none |
| 084 | build(ci) | paper compile job | `.github/workflows/` | every commit proves the PDF still builds; artifact uploaded | 083, 003 |
| 085 | docs(paper) | abstract | `paper/sections/` | one commit, one section, reviewable alone | 083 |
| 086 | docs(paper) | introduction and research question | `paper/sections/` | | 083 |
| 087 | docs(paper) | background and related work | `paper/sections/` | | 078,079 |
| 088 | docs(paper) | model formulation | `paper/sections/` | | 083 |
| 089 | docs(paper) | theorems and proofs | `paper/sections/` | even-pacing and shape-invariance results, from docs/01_derivation.md | 088 |
| 090 | docs(paper) | competing models M0-M4 | `paper/sections/` | | 088 |
| 091 | docs(paper) | data and pipeline | `paper/sections/` | | 056 |
| 092 | docs(paper) | pre-registered methods | `paper/sections/` | | 066 |
| 093 | docs(paper) | theoretical results | `paper/sections/` | | 089 |
| 094 | docs(paper) | empirical results | `paper/sections/` | | 065,068 |
| 095 | docs(paper) | discussion | `paper/sections/` | | 094 |
| 096 | docs(paper) | limitations and assumptions audit | `paper/sections/` | from docs/assumptions.md, honestly | 082,094 |
| 097 | docs(paper) | figures and captions integration | `paper/`, selected `figures/` | | 094 |
| 098 | docs(paper) | conclusion, future work, final bibliography pass | `paper/sections/` | | 095-097 |


**Rows 083-086 and 088-090 executed, one commit per row (annotation
2026-09-04, from git log).** 083 `8a4e0f7`, 084 `20ca309`, 085 `022c72c`,
086 `9c1c6e6`, 088 `b80e9c7`, 089 `ab1167b`, 090 `43b7bb2`. Rows 087 and
091-098 are covered by the execution note below.

## Execution note, 2026-09-03 (single large commit by owner's instruction)

Rows 055-058 (freeze), 059-072 (registered fits, held-out comparison,
bootstrap CIs, H1, mixed effects) and 091-098 (paper data, methods,
theoretical results, empirical results, discussion, limitations, figures,
conclusion) were executed together and delivered as ONE commit, at the
owner's request ("for this next commit just do a single large commit").
Deviations from the planned file names: fits land in
`results/model_calibration/fits_train_v0_2.csv` (validation_plan §11) and
the comparison in `results/validation/model_comparison.csv`; the evaluator
is `scripts/evaluate_holdout.py` with its synthetic tests in
`tests/test_evaluate_holdout.py`; rows 067/069/071 share `src/stats.py`.
Rows 063/064 produced emp06-08 from the evaluator rather than from
`empirical_analysis.py`, so the frozen pilot-v0.1 outputs stay untouched.
Row 087 (background) remains folded into the introduction; band J is open.
Also in this commit, outside the plan: age-aware identity matching in the
ingester (a false merge of two same-name swimmers found during expansion)
and the inner-solver restart fix in `src/calibration.py` (found during the
registered calibration, before the test set was opened; docs/calibration.md).

## CI repair, 2026-09-04 (outside the plan)

Row 003's premise — "every future commit gets verified buildable
automatically" — was false from 2026-09-01 to 2026-09-04. Row 018
(`5acbe6d`) pointed `tests/test_calibration.py` at
`data/processed/200_free_scy_processed.csv`, and `tests/test_ingest.py`
read `data/raw/200_free_scy_raw.csv` for its header; `.gitignore` has
excluded both since the base commit. The suite passed locally, where those
files sit in the working tree, and failed on every CI push for 51 commits.

Repaired by moving the behavioural tests onto `tests/fixtures/synthetic_raw.csv`
(invented swimmers, teams, meets and times in the real raw schema), derived
through the real pipeline by session fixtures in `tests/conftest.py`. The two
tests that assert properties of the real dataset — the published pilot
comparison and the frozen exploratory fit report — cannot be synthesised without
fabricating what they check, so they carry a new `requires_data` marker that CI
deselects. CI now covers 144 of 151 tests; the gap is recorded in
`DEV_WORKFLOW.md`. No real race data enters the repo: the dataset is on 15-18
year old swimmers and carries team, meet, date and age.

## Band J — Code quality and documentation (099-106)

Executed only where a real gain exists; any row that turns out cosmetic is
dropped rather than committed.

| # | Type | Title | Files/system | Purpose | Depends |
|---|---|---|---|---|---|
| 099 | docs(code) | docstring pass: model and calibration | `src/model.py`, `src/calibration.py` | the mathematical contracts (units, spaces, conventions) written at the definitions | 028 |
| 100 | docs(code) | docstring pass: pipeline modules | `src/preprocessing.py`, `src/data_split.py`, `src/hytek_parser.py` | same for the data path | none |
| 101 | test | parse_time and split-derivation edge cases from new meets | `tests/test_pipeline.py` | every parsing oddity band F surfaces becomes a pinned regression test | F |
| 102 | chore | figures index | `figures/README.md` | every figure mapped to the command that regenerates it | none |
| 103 | docs | architecture overview | `docs/architecture.md` | module map and data flow for a new reader | none |
| 104 | refactor | consolidate duplicated literals found during D-G | `src/`, `scripts/` | only if duplication actually accumulates; otherwise dropped | as found |
| 105 | chore | prune dead code found during D-G | `src/`, `scripts/` | same conditional standard | as found |
| 106 | docs | repo tour for faculty readers | `docs/TOUR.md` | a one-page entry point for the professor-outreach goal: what to read in what order | 103 |


**Rows 102 and 103 executed (annotation 2026-09-04, from git log).** 102
`0ca747c`, 103 `07441a3`. Rows 099-101 and 104-106 remain open; for
099-101/104/105, whether each is done or dropped under this band's own
cosmetic-rows-are-dropped rule is a decision still to be made.

---

## Delivered outside the plan

Work in the tree that no numbered row planned, listed here rather than
retrofitted into invented rows:

- `src/results_parsers.py`, `scripts/ingest_spreadsheet.py`,
  `scripts/ingest_swimcloud_pdfs.py` — band F needed parsers for official
  formats beyond the classic Hy-Tek section (`af07cd9`, `bccb4db`).
- `1d49198` — README test-tier correction after the CI marker change.
- `9763e7e` — gitignore for derived knowledge-graph output.
- Extras already noted in their own sections: age-aware identity matching and
  the inner-solver restart fix (execution note), the CI repair (`93cd232`),
  the bibliography dedupe (`929c99f`, band H).

## Count

Rewritten 2026-09-04. The paragraph that stood here was 2026-09-01 planning
text ("40 executable now with no new data...") that the annotations above had
overtaken row by row.

106 planned rows. Bands A-E executed in full (A, C, D, E one commit per row;
B re-scoped into the sign-fix arc). Band F executed as two commits covering
fifteen meets plus the 055-058 freeze block. Band G executed per the
2026-09-03 execution note, with 068 and 072 folded into the comparison and
H1 artifacts. Band H closed except the W'-in-joules half of 077, blocked on
paywalled source access. Band I executed in full, 087 folded into the
introduction. Band J: 102 and 103 done; 099-101 and 104-105 await an
explicit drop-vs-do decision; 106 open.

Open rows: 099, 100, 101, 104, 105 (conditional on that decision), 106, and
the blocked half of 077. Everything else is in the history. The counting
principle stands: honest granularity, not a target to hit.

