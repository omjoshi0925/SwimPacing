# Architecture

The repository in one page: what each module owns, and how data flows from an
official results page to a figure in the paper.

## Module map

```
src/parameters.py    every constant, the Swimmer/Course dataclasses, the
                     M0-M4 registry, cached predicted shapes. Nothing imports
                     "magic numbers" from anywhere else.
src/model.py         cost function, drag, energy accounting, closed-form
                     optima, KKT residuals, calibration to a target time,
                     raced<->recorded start transforms, format_time.
src/simulator.py     ODE integration of (t, E) over distance, named strategy
                     shapes (incl. observed ones), budget-matched scaling.
src/optimization.py  SLSQP in split-time space (convex) and over the full ODE
                     (optimize_full), strategy comparison, opening-penalty
                     curve.
src/sensitivity.py   parameter sweeps, elasticities, archetypes, seeded
                     Monte Carlo robustness.
src/calibration.py   the registered loss, fitters for beta_x/gamma/beta_E,
                     the train-only data door and leakage guard, fit audit
                     trail.
src/hytek_parser.py  strict parser for official Hy-Tek result sections;
                     refuses malformed input loudly.
src/preprocessing.py raw->processed pipeline: split derivation, quality
                     flags, pacing metrics (raw + free-swimming-equivalent),
                     per-race model deviations, pre-race PB rule.
src/data_split.py    swimmer-grouped train/test split, seed 20260829.
src/visualization.py styling + every theoretical figure.
```

## Scripts (entry points)

```
scripts/run_all.py            all theoretical results + figures
scripts/refresh_predictions.py recompute cached M2/M4 optima after editing MODELS
scripts/ingest_hytek.py       config-driven meet ingestion (configs/meets/*.json)
scripts/ingest_swimcloud_pdfs.py the pilot's SwimCloud final-times ingest
scripts/empirical_analysis.py  empirical figures + pilot report + sensitivity
scripts/fit_models.py          the only sanctioned fitting entry point
```

## Data flow

```
official results page (pacswim.org)
   | verbatim save + sha256              [data/private/sources/, gitignored]
   v
configs/meets/<meet>.json  ->  scripts/ingest_hytek.py
   | anonymize via private id map; idempotent by meet_id;
   | public sha256 recorded in data/DATASET_VERSIONS.md
   v
data/raw/200_free_scy_raw.csv          [committed, anonymized]
   |  python -m src.preprocessing
   v
data/processed/200_free_scy_processed.csv   [flags, metrics, deviations]
   |                          \
   |  empirical_analysis       \  calibration.training_frame (train rows only;
   v                            v  test rows structurally withheld)
figures/empirical/*, pilot_report   scripts/fit_models.py -> fits_*.csv
```

Theory side, independent of any data:

```
parameters.py -> model/optimization/simulator -> run_all.py
             -> results/theoretical, results/sensitivity, figures/fig*.png
```

Paper: `paper/main.tex` inputs `paper/sections/*.tex`, cites
`literature/references.bib` (the same file the review CSV mirrors), and pulls
figures from `figures/`. CI compiles it on every paper or bibliography push.

## Invariants the design protects

1. Names never leave `data/private/`; published artifacts carry S-numbers and
   checksums only.
2. The held-out test rows are reachable only through `data_split`, and the
   calibration layer refuses frames containing them.
3. Committed outputs and the code that generates them move in the same
   commit (DEV_WORKFLOW.md), so no commit shows results its own code cannot
   reproduce.
4. Every constant lives in `parameters.py` with provenance in
   `docs/parameters.md`; cached model shapes are pinned to live solves by a
   slow-tier test.
