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

## Band B — Start term as a first-class model parameter (009-016)

The pilot's Phase 7 verdict: a dedicated start term is warranted (lap-1
advantage of roughly 1 s beyond the dive credit). This band promotes the start
credit from a constant buried in analysis code to a model parameter with
provenance, without yet fitting it.

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

## Band H — Literature completion (073-082)

Each commit is preceded by verification in-session under the standing policy:
found and confirmed, access level recorded, nothing reconstructed from memory.
A planned row that finds no verifiable source becomes a documented gap, not a
fabricated entry.

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

---

## Count

106 planned rows: 40 executable now with no new data (bands A-E), 10 literature
commits executable now (band H), 8 paper commits executable now (083-090 minus
087's literature dependency), the rest gated on data expansion [DATA] or locked
behind the pre-registered order [ORDER]. Band F scales with how many official
meet results we can pull; six meets is the nominal plan. If execution shows a
row is too thin to stand alone it merges into its neighbor with a note here;
the count is whatever honest granularity supports, not a target to hit.

