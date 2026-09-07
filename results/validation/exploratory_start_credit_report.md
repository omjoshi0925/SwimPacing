# Exploratory: a per-race, pace-aware start credit S(v) = 15/v − t15

**EXPLORATORY.** The held-out test set was opened on 2026-09-03 for the
registered evaluation (`report_v0_2.md`). Everything here was run after
that, under the 2026-09-06 declaration in `docs/validation_plan.md`, and
cannot become a registered result. No registered artifact changed. Roadmap
band K (rows 107-113); produced by `scripts/explore_start_credit_per_race.py`
from `data/processed/200_free_scy_processed.csv` (pilot-v0.2, frozen);
rows in `exploratory_start_credit_per_race.csv`; figure `emp09`.

## The question

The registered comparison found the model ranking moves across the 1.2-3.4 s
constant start-credit band (§7.3: the data cannot distinguish the surviving
models given start uncertainty), and the M3 refit showed `beta_x` absorbing
the assumed credit almost one-for-one, 0.3335 → 0.0103 across that band. The
pilot report's Phase 7 verdict named a per-race, pace-aware credit as the
minimum upgrade. This run asks only: **with S(v) = 15/v − t15 per race, is
`beta_x`'s range across the plausible t15 band narrower than 0.3335 → 0.0103,
and does the held-out ranking stabilize?**

## Method, in one paragraph

v = 182.88/T for each race (whole-race velocity, the definition validation_plan
§7 amendment (b) used; T includes the dive-assisted lap 1, a circularity
carried knowingly). t15 is a literature quantity — `docs/parameters.md`,
Category A: Tor 2014 6.12 ± 0.16 s and Rudnik 2023 6.410 ± 0.45 s for elite
males, van Dijk 2020 6.42-8.22 s per-swimmer best times for a mixed-sex
national-level group — and is never fitted. Three regimes: **(i)** constant
t15 swept 6.1-7.5 s in 0.2 s steps; **(ii)** t15 = 0.839·15/v, so an elite
~1:33 gets 6.4 s; **(iii)** S ≡ 1.80 s for every race, the registered
constant, as the reference row. Per cell, `beta_x` (closed form), `gamma` and
`beta_E` (ODE, five-restart inner solve) were refitted on the 256 training
races through `calibration.training_frame` with the leakage guard applied,
and M0-M4 were scored on the 89 held-out races. Credits are added to lap 1
through the single transform `model.recorded_to_raced` (row 109).

**Gate.** The reference row ran first and alone. The per-race path at
S ≡ 1.80 reproduced the stored pipeline columns to 1.1e-16 and the scalar
path exactly; held-out RMSEs reproduced `model_comparison.csv` exactly at four
decimals for the closed-form models. The ODE models' evaluation-time re-solve
does not reproduce the 2026-09-03 run bit-for-bit (M2 0.771022 vs 0.7709 pp;
M4 0.460854 vs 0.4609) — a property of the registered artifact, reproduced by
`evaluate_holdout`'s own code — so by the owner's decision they are held to
2e-4 pp (`docs/calibration.md`). The reference refit then reproduced the
registered `beta_x` (0.2277 vs 0.2277), `beta_E` (0.020, at its bound) and
ranking. `gamma` refit to 0.2699 against the registered 0.2687, with a
training loss of 0.4603 pp against the registered 0.4608 at that value, so
the reference row's M4 held-out RMSE is 0.4605 rather than 0.4609 — a
4e-4 pp shift, consistent with a flat `gamma` loss surface under the
re-solve drift, not separately verified.

## Results

| cell | S on held-out, mean [min, max] s | beta_x | gamma | beta_E | RMSE M0 / M2 / M3 / M4 (pp) | best | ranking | sign(P4−P1) |
|---|---|---|---|---|---|---|---|---|
| reference, S ≡ 1.80 s | 1.80 [1.80, 1.80] | 0.2277 | 0.2699 | 0.020 | 0.6535 / 0.7710 / 0.4539 / 0.4605 | M3 | M3>M4>M0>M1>M2 | +1 |
| (i) t15 = 6.1 s | 3.16 [2.07, 5.81] | 0.0463 | 0.4331 | 0.020 | 0.4654 / 0.5212 / 0.4516 / 0.4419 | M4 | M4>M3>M0>M1>M2 | +1 |
| (i) t15 = 6.3 s | 2.96 [1.87, 5.61] | 0.0744 | 0.4311 | 0.020 | 0.4615 / 0.5336 / 0.4300 / 0.4331 | M3 | M3>M4>M0>M1>M2 | +1 |
| (i) t15 = 6.5 s | 2.76 [1.67, 5.41] | 0.1038 | 0.4226 | 0.020 | 0.4710 / 0.5568 / 0.4132 / 0.4338 | M3 | M3>M4>M0>M1>M2 | +1 |
| (i) t15 = 6.7 s | 2.56 [1.47, 5.21] | 0.1345 | 0.4045 | 0.020 | 0.4926 / 0.5896 / 0.4018 / 0.4341 | M3 | M3>M4>M0>M1>M2 | +1 |
| (i) t15 = 6.9 s | 2.36 [1.27, 5.01] | 0.1665 | 0.3922 | 0.020 | 0.5245 / 0.6314 / 0.3960 / 0.4342 | M3 | M3>M4>M0>M1>M2 | +1 |
| (i) t15 = 7.1 s | 2.16 [1.07, 4.81] | 0.1997 | 0.3162 | 0.020 | 0.5655 / 0.6815 / 0.3959 / 0.4301 | M3 | M3>M4>M0>M1>M2 | +1 |
| (i) t15 = 7.3 s | 1.96 [0.87, 4.61] | 0.2338 | 0.2782 | 0.020 | 0.6160 / 0.7371 / 0.4013 / 0.4071 | M3 | M3>M4>M0>M1>M2 | +1 |
| (i) t15 = 7.5 s | 1.76 [0.67, 4.41] | 0.2688 | 0.2459 | 0.020 | 0.6734 / 0.7969 / 0.4118 / 0.3912 | M4 | M4>M3>M0>M1>M2 | +1 |
| (ii) t15 = 0.839·15/v | 1.49 [1.31, 1.92] | 0.2863 | 0.2290 | 0.020 | 0.7415 / 0.8657 / 0.4536 / 0.4196 | M4 | M4>M3>M0>M1>M2 | +1 |

RMSEs are comparable **within** a row only: the credit changes the observed
shares being fitted, so a lower number in one cell than another is a
different observable, not a better model. M1 equals M0 in every cell (shape
identical by theorem) and is omitted from the RMSE column.

## Answer

**Narrower, but not narrow.** Across the plausible elite-to-sub-elite t15
band, `beta_x` runs 0.0463 → 0.2688, a span of 0.2225 against the
constant-credit sweep's 0.3232 — about two thirds of it. The dependence is
close to linear at roughly 0.03 per 0.2 s of t15 (emp09), i.e. the entire
measurement uncertainty on an elite 15 m time (Tor ± 0.16 s, Rudnik ± 0.45 s)
still moves `beta_x` by several hundredths. The per-race credit relocates the
degree of freedom from S to t15; it does not remove it.

**The ranking does not stabilize.** M3 wins six of the eight regime (i) cells
(6.3-7.3 s), M4 wins at both edges (6.1 s and 7.5 s) and in regime (ii). The
M3-M4 held-out difference where it flips is 0.010 pp (6.1 s), 0.021 pp
(7.5 s) and 0.034 pp (regime ii); no bootstrap was run in these cells and the
registered CIs do not transfer to them, so the conclusion rests on the flip
itself, not on the size of the gap. The
registered conclusion of record (§7.3: not distinguishable given start
uncertainty) stands, restated in t15 terms.

Three further things the run shows:

1. **At matched mean credit, the per-race rule gives a higher `beta_x` than
   the constant rule** (emp09: regime (i) sits above the constant-S trace by
   0.00-0.03 on the figure's axis, growing with t15; 0.01-0.04 at matched
   mean training credit). Within a cell the per-race credit spreads over
   5.2 s across the training field (3.7 s on the held-out rows; slow races
   get more), which raises slow swimmers' lap-1 share more than fast
   swimmers' and moves the mean shape. The within-field dispersion matters,
   not only the field mean.
2. **Regime (ii) is nearly a constant credit** — S = (1 − 0.839)·15/v spans
   only 1.31-1.92 s — and lands on the constant-S trace at its field-mean t15
   (7.74 s). A proportional t15 therefore reproduces the constant-credit
   picture rather than escaping it.
3. **`gamma` approaches its fitting bound at the elite floor** (0.4331 and
   0.4311 at 6.1 and 6.3 s against a 0.45 bound — interior optima, unlike
   `beta_E`, which returns its 0.02 lower bound exactly in every cell), so
   M4's win at 6.1 s is with `gamma` close to the edge of its allowed range.
   M2 is last everywhere. sign(P4−P1) is +1 in every cell: no regime
   produces a negatively split held-out mean.

## Where each regime stops being physical

- **Regime (i), slow tail.** A constant elite t15 is assigned to every race,
  including the slowest in this field (whole-race v 1.143 m/s, T ≈ 2:40, in
  the training rows), for which 15/v ≈ 13.1 s and the credit reaches 7.0 s at
  t15 = 6.12 (5.81 s on the slowest held-out race at 6.1 s). Those swimmers
  do not start like elites; the credit there is an extrapolation. The
  low-t15 cells are where `gamma` nears its bound; the winner flips at both
  ends of the band and under regime (ii), so the flip is not explained by
  this extrapolation alone.
- **Regime (ii), the same tail from the other side.** t15 = 0.839·15/v gives
  the slowest swimmer a 15 m time of ≈ 11 s, well outside anything measured
  (van Dijk's sub-elite ceiling is 8.22 s). Proportionality holds the credit
  nearly constant by construction and is unphysical exactly where regime (i)
  is: for the slow tail.
- **Both regimes** compare the dive to 15 m of with-turns race pace rather
  than to a turn push-off over the same 15 m; laps 2-4 also open with a
  push-off and an underwater phase that the free-swimming model does not
  carry. This is the constant-S model's approximation carried forward
  (`docs/assumptions.md`, A1). The eight-segment model (Task 19) is what
  removes it.

## What would change the answer

Measured 15 m splits for this field (`split_15m`, empty on all 345 usable
rows). With per-swimmer t15 the credit stops being a literature extrapolation
and `beta_x` stops carrying it. Nothing in this run substitutes for that
measurement.

## Reproduce

```
python -m scripts.explore_start_credit_per_race            # resumes from the CSV
python -m scripts.explore_start_credit_per_race --figure   # emp09
```

Run record: reference cell 2026-09-06 (gate passed on the split tolerance
after one strict-rule failure on M2, `docs/calibration.md`); the nine
remaining cells as one detached run the same day, relaunched once after the
gate's own monotonicity check was corrected to tolerate two held-out races
with identical final times. Dataset pilot-v0.2, seed 20260829, 256 training /
89 held-out races; every row carries `exploratory=True`.
