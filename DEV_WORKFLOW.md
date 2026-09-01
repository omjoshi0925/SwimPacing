# Developer workflow

How a checkpoint is verified and how generated artifacts stay in sync with the
code that makes them. Every commit is expected to leave this whole page true.

## Verification tiers

```bash
python -m pytest tests -q -m "not slow"   # quick tier, ~6 s, what CI runs
python -m pytest tests -q                 # full tier, ~2 min, before any delivery
```

The `slow` marker (registered in `pytest.ini`) covers the tests that re-solve
ODE optima live. Run the full tier before anything that changes model code,
cached predictions, or the pipeline; the quick tier is enough for docs and
analysis-script edits.

## What regenerates what

| You changed | Regenerate with |
|---|---|
| `src/parameters.py` MODELS registry | `python -m scripts.refresh_predictions`, then full test tier (the cache-vs-live test enforces freshness) |
| model/optimizer code | `python scripts/run_all.py` (theoretical results + figures) |
| `src/preprocessing.py` or raw data | `python -m src.preprocessing data/raw/200_free_scy_raw.csv` |
| anything feeding the empirical analysis | `python scripts/empirical_analysis.py` (figures `emp*`, `results/validation/pilot_report.md`, comparison CSVs) |

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
