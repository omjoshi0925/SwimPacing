# Calibration protocol (Task 14 machinery)

What gets fitted, what stays frozen, on which rows, with which loss, and how a
fit run is audited. The registered analysis choices live in
`docs/validation_plan.md`; this page is the implementation contract for
`src/calibration.py` and `scripts/fit_models.py`.

## What is fittable, and why only this

| Parameter | Model | Fittable from split shapes? |
|---|---|---|
| `beta_x` | M3 | **yes** — the shape depends on it (closed form) |
| `gamma` | M4 | **yes** — the shape depends on it (ODE solve) |
| `beta_E` | M2 | **yes** — the shape depends on it (ODE solve) |
| `E0`, `R`, `phi` | all | **no** — they trade off inside one race-time equation; split shapes carry no information about them (docs/parameters.md, Identifiability) |
| `v_max` | M4 | **no** — frozen; confounded with `gamma` (a lower ceiling with gentler decay resembles a higher ceiling with steeper decay) |
| `tau` | M1-M4 | **no** — measured (16.5 s, Pessoa Filho 2012), and shapes carry almost no information about it |
| start credit | course | **not from lap times** — estimating it from lap differences would absorb genuine pacing into the correction; it moves only on 15 m start-time evidence |

Fitting anything from the right column to split shapes would be fitting noise,
so the code simply provides no path to do it.

## The loss

The registered primary metric (validation_plan §3): per-race RMSE over the
four split proportions against the model's raced-space shape, averaged over
races, in percentage points (`calibration.mean_rmse_pp`). Observed shares are
the free-swimming-equivalent columns (`P{i}_corrected`, dive credit ADDED to
lap 1); one transform per comparison, per `docs/model_definitions.md`.

Because one parameter value yields one shape shared by all races, the
race-to-race dispersion term is parameter-independent, and minimizing this
loss is equivalent to minimizing distance to the mean observed shape. The
code minimizes the registered per-race form directly anyway.

## The fitters

- **M3 / `beta_x`** — closed-form inner solve, bounded Brent, deterministic,
  ~10 evaluations, milliseconds.
- **M4 / `gamma`**, **M2 / `beta_E`** — each objective evaluation is a full
  ODE optimization (`optimize_full`, minutes), so: coarse grid to bracket,
  bounded Brent inside the bracket, per-value caching, and a restart ladder
  on solver failure. Explicit eval budgets, printed and recorded.
  **Inner-solve reliability (found 2026-09-03, training side, before the
  test set was opened).** The pilot-era ladder started at ONE restart and
  escalated only on exceptions. On pilot-v0.2 the single-start M4 solve at
  the registry gamma returned a solution 0.1 s slower than the 12-start
  registry solution with a shape 0.35 pp away from it — a quiet local
  optimum, not a failure — and at the "fitted" gamma it returned a
  meaningless 2.7 pp shape. The registered fitter therefore starts the
  ladder at five restarts (`INNER_STARTS_LADDER = (5, 12)`), which
  reproduces the cached 12-start registry shapes to four decimals, and every
  ODE fit now records a reliability check ("inner solve vs cached registry
  shape: max |dP|") in its notes; a deviation above 0.05 pp marks the fit
  unusable. The exploratory pilot-v0.1 gamma fit in
  `results/validation/fits_train_pilot.csv` predates this and should be read
  with that caveat (it was never the calibration).
- Lower bounds sit off zero for `gamma` and `beta_E`: at zero the mechanism is
  absent and the parameter unidentified.
- `phi` is held at each model's registry value during fitting. By the
  shape-invariance theorem it cannot move M3's shape at all, and for M2/M4 its
  influence on shape is third-decimal; it remains a race-time calibration, not
  a shape parameter.

**Re-solve reproducibility of the ODE models (found 2026-09-06, band K
gate).** The held-out RMSEs in `results/validation/model_comparison.csv` for
M2 and M4 depend on an ODE re-solve of the fitted shape at evaluation time
(`evaluate_holdout.fitted_shapes`), not on the four-decimal shape recorded in
the fit report. That re-solve is deterministic within a session but did not
reproduce the registered run bit-for-bit: with the registered code path and
the registered fitted values, today's M2 shape scores 0.771022 pp against the
recorded 0.7709 (delta +1.2e-4 pp) and M4 0.460854 against 0.4609 (delta
-4.6e-5 pp, same four decimals). The recorded shapes are worse anchors, not
better: rounded to four decimals they score M2 at 0.772270, so the rounding
alone moves the number by 1.3e-3 pp. Consequences: the closed-form models
(M0, M1, M3) reproduce exactly and are held to exact equality; any regression
check on the ODE models carries a stated band of 2e-4 pp (band K's
`ODE_TOL_PP`); and the registered comparison's M2/M3/M4 differences, which
are of order 1e-2 pp with bootstrap CIs of order 1e-1 pp, are not affected at
the precision that matters. No registered artifact was changed.

## Rows: training only, structurally

Data enters fitting through exactly one door, `calibration.training_frame`:
usable rows, swimmer-grouped split at the registered seed (20260829), train
side returned, test side withheld. `calibration.assert_no_test_rows` raises
`CalibrationLeakageError` on any frame containing a held-out swimmer, and the
CLI runs it before evaluating anything. The held-out rows are not evaluated
against fitted models until the registered comparison (validation_plan §5).

## Exploratory vs registered runs

Fits on **pilot-v0.1** are labeled `exploratory` in the report CSV and
everywhere they are discussed. They exist to exercise the machinery, inform
priors, and expose the start-credit confound. The **registered** run happens
once, on the training side of the expanded frozen dataset (pilot-v0.2), after
which the held-out comparison uses those frozen fitted values with no
retuning. Fitted values are estimates under this model family, never measured
physiology.

## Audit trail

Every run writes one CSV row per model via `calibration.write_fit_report`:
fitted value, registry value, train loss vs registry loss, eval count, fitted
shape, bounds, dataset version, seed, train counts, start credit, exploratory
flag, UTC timestamp. M0 appears as a parameter-free baseline row so the table
stands alone.

## Known confound, restated

`beta_x`/`gamma` and the start credit push observed lap 1 the same way. Fits
at the default credit are conditional on it; `scripts/` therefore sweeps the
fitted values across the registered credit band wherever they are reported,
and validation_plan §7.3 governs what may be concluded when the ranking moves
inside the band.
