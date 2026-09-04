# Developer workflow

How a checkpoint is verified and how generated artifacts stay in sync with the
code that makes them. Every commit is expected to leave this whole page true.

## Verification tiers

```bash
python -m pytest tests -q -m "not slow and not requires_data"   # what CI runs
python -m pytest tests -q -m "not slow"                         # + real-data checks
python -m pytest tests -q                                       # full, before delivery
```

The `slow` marker (registered in `pytest.ini`) covers the tests that re-solve
ODE optima live. Run the full tier before anything that changes model code,
cached predictions, or the pipeline; the quick tier is enough for docs and
analysis-script edits.

### What CI does NOT verify

`requires_data` marks tests that assert a property of the real dataset under
`data/`, which is gitignored. A clean checkout cannot see those files, so CI
deselects the marker and its green tick covers **144 of the 151 tests**: 5
`slow`, 2 `requires_data`. The two are
`test_loss_reproduces_the_published_pilot_comparison` and
`test_fit_beta_x_on_train_rows_matches_the_committed_report`, which pin the
calibration module to frozen published artifacts. Nothing but a local run with
`data/` present exercises them, so run at least the middle tier above before
any delivery.

This gap is deliberate. A synthetic fixture could only make those two assertions
pass by containing the numbers they check, which would turn a real anchor into a
fabricated green tick. Everything behavioural runs on
`tests/fixtures/synthetic_raw.csv` instead, put through the real pipeline by the
session fixtures in `tests/conftest.py`.

**Never point a test at `data/` without the `requires_data` marker.** Between
2026-09-01 and 2026-09-04 the CI suite was red on every push because two test
modules read gitignored files; it passed locally the whole time, because the
files sat in the working tree. A local pass is not evidence a test will run in
CI. Clone to a temp directory and run there if in doubt.

## What regenerates what

| You changed | Regenerate with |
|---|---|
| `src/parameters.py` MODELS registry | `python -m scripts.refresh_predictions`, then full test tier (the cache-vs-live test enforces freshness) |
| model/optimizer code | `python scripts/run_all.py` (theoretical results + figures) |
| `src/preprocessing.py` or raw data | `python -m src.preprocessing data/raw/200_free_scy_raw.csv` |
| anything feeding the pilot-v0.1 analysis | `python scripts/empirical_analysis.py` (figures `emp01-05`, `results/validation/pilot_report.md`, pilot CSVs) — note this rewrites the FROZEN pilot report; only run it to reproduce, never to update |
| the registered calibration (frozen dataset, training side) | `python -m scripts.fit_models --registered --dataset pilot-v0.2 --out results/model_calibration/fits_train_v0_2.csv` (~40 min; M2/M4 use the five-restart inner solve) |
| the registered held-out evaluation | `python -m scripts.evaluate_holdout` — this opens the test set; the first opening is recorded in the script and the plan, and re-running after any upstream change makes the result exploratory (validation_plan §5). `--dry-run` exercises the code on a re-split of the training rows only |

Generated CSVs, figures, and the pilot report are committed in the same commit
as the code change that alters them, never separately, so history never holds
a code state whose committed outputs disagree with it.

## Atomic-commit delivery protocol

Development is delivered as numbered atomic changes (`Change_NNN.zip`), each
containing only that change's files at repo-root-relative paths, applied with

```bash
cd ~/Documents/GitHub/SwimPacing && unzip -o ~/Downloads/Change_NNN.zip -d .
```

then committed with the message given in the change report. The sequence and
rationale live in `ATOMIC_COMMIT_ROADMAP.md`. Commits follow conventional
prefixes (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `build:`, `chore:`,
`data:`, `results:`).

## Non-negotiables

Real data only, `data/private/` never leaves the machine, the held-out test
set is not evaluated until the registered analysis, fitted parameters are
estimates rather than measured physiology, and errors get documented in place
(see the retraction note in `docs/RESULTS.md` for the house style).
