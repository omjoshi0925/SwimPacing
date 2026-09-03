# Figure index

Every committed figure, what it shows, and the exact command that regenerates
it. PNG and PDF are emitted together; a figure changes only in the commit that
changes its inputs or its code.

## Theoretical (`python scripts/run_all.py`)

| Figure | Shows |
|---|---|
| fig01_velocity_energy | optimal velocity profile and reserve trajectory |
| fig02_cost_of_velocity | the drag-derived cost function and its components |
| fig03_strategy_comparison | named strategies at matched energy budget |
| fig04_drag_sensitivity | race-time sensitivity to the drag block |
| fig05_opening_penalty | cost of opening-lap errors, re-optimized rest |
| fig07_physiology_vs_shape | engine parameters do not move the shape |
| fig09_theory_vs_observed | model optima vs observed strategy shapes |
| fig12_archetypes | swimmer archetypes calibrated to target times |
| fig13_elasticity | race-time elasticities per parameter |
| fig14_shape_heatmap | optimal shape over the fatigue-parameter plane |
| fig15_penalty_robustness | pacing penalties under Monte Carlo parameter draws (seeded) |

(fig06, fig08, fig10, fig11 were retired in earlier revisions; numbers are
not reused, so stale references fail loudly.)

## Empirical (`python scripts/empirical_analysis.py`, needs the processed dataset)

| Figure | Shows |
|---|---|
| empirical/emp01_split_share_distributions | observed share distributions, raw and corrected |
| empirical/emp02_mean_profile_vs_models | mean observed profile vs M0-M4 predictions |
| empirical/emp03_model_deviations | per-race RMSE vs each model |
| empirical/emp04_start_effect | lap-1 advantage vs dive value; ranking across the credit band |
| empirical/emp05_fitted_shapes | exploratory fits vs training mean; the start-credit confound |

## Registered held-out evaluation (`python -m scripts.evaluate_holdout`, pilot-v0.2)

| Figure | Shows |
|---|---|
| empirical/emp06_holdout_comparison | held-out mean RMSE per model with swimmer-cluster bootstrap CIs; held-out mean profile vs fitted shapes |
| empirical/emp07_start_band_holdout | held-out ranking across the registered 1.2-3.4 s start-credit band, fitted parameters fixed |
| empirical/emp08_deviation_vs_performance | H1: improvement on pre-race PB vs deviation from the best-supported model's optimum, with the registered quadratic fit |

`evaluate_holdout.py` is the one script that opens the test set; it is not
part of `run_all.py` and is not re-run casually (validation_plan §5).

Order to regenerate everything from scratch:

```bash
python -m src.preprocessing data/raw/200_free_scy_raw.csv
python scripts/run_all.py
python scripts/empirical_analysis.py      # pilot-v0.1 descriptive figures (emp01-05)
python -m scripts.fit_models --registered --dataset pilot-v0.2 \
    --out results/model_calibration/fits_train_v0_2.csv   # training side only
python -m scripts.evaluate_holdout        # emp06-08; opens the test set ONCE
```
