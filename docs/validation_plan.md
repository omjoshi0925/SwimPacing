# Validation plan

Task 6. Written **before any data exists**, so it functions as a
pre-registration. Every decision below is fixed now; departures from it later
must be labelled as exploratory rather than confirmatory.

Date written: 2026-08-29. Races in hand at time of writing: **0**.
Amendment log: 2026-08-31, start-credit band widened (see §7); no data had been
used for calibration and the test set remained unopened at amendment time.

---

## 1. Research question

> Which mathematical fatigue mechanism best explains observed pacing behaviour
> in competitive 200 yard freestyle swimming, and what pacing strategy does the
> best-supported model predict?

## 2. Hypotheses

**Primary (Task 16).**

- **H0:** deviation from the model-predicted optimal pacing strategy is not
  associated with performance relative to expectation.
- **H1:** swimmers whose pacing profiles are closer to the predicted optimum
  perform better relative to expectation.

**Secondary (Task 15).** The five models make three distinct qualitative shape
predictions. The observed mean pacing profile, after start correction, is
consistent with exactly one of: even (M0/M1), negative split (M2), linear
positive split (M3), front-loaded positive split (M4).

## 3. Primary metric

For each race, normalized split proportions:

```
P_i = S_i / T,     i = 1..4,     sum_i P_i = 1
```

For each model, predicted proportions `P_i*`. The primary metric is

```
RMSE = sqrt[ (1/4) * sum_i (P_i - P_i*)^2 ]
```

reported in percentage points. This is scale-free, so a 1:35 swimmer and a
1:55 swimmer contribute comparably.

**Note on degrees of freedom.** The `P_i` sum to 1, so only three of the four
residuals are free. RMSE over four terms is still a valid comparison statistic
because every model is scored identically, but it must not be treated as having
four independent components in any test.

### Secondary metrics

- MAE over the same proportions.
- Per-split signed error, which is what actually distinguishes M3 from M4.
- **Split 1→2 drop versus split 3→4 drop.** This is the discriminating
  statistic: M3 predicts these roughly equal, M4 predicts the first much larger.
  Recorded as a pre-registered secondary outcome because it is more informative
  than aggregate RMSE.
- Race-time prediction error, reported but **not** used for model selection,
  because race time depends on parameters the data cannot identify.

### Metrics deliberately not used for selection

- **AIC/BIC.** These need a likelihood, and the models as written are
  deterministic with no error model. Adding a Gaussian error term to justify a
  likelihood would be a modelling choice made for the convenience of the
  statistic. If a likelihood-based comparison is wanted later, the error model
  must be specified and defended first.
- **Visual fit.** A figure is not evidence for model selection.

## 4. What counts as a win

Decided in advance:

- A model **wins on shape** if its predicted sign of `P_4 - P_1` matches the
  observed mean and the others' do not.
- A model **wins on accuracy** if its held-out RMSE is lower than every other
  model's by more than the bootstrap 95% CI half-width of the difference.
- If no model separates by that standard, the reported conclusion is **"the
  data do not distinguish these models"**. That is a publishable result and it
  is the expected outcome at n = 50.

## 5. Train and test protocol

**Split by swimmer, not by race.** Task 13. Multiple races from one swimmer
share that swimmer's technique, physiology and start quality, so a random race
split would leak information and inflate apparent accuracy.

- Training set: ~75% of **swimmers**
- Test set: ~25% of **swimmers**
- No swimmer appears in both. Enforced in `src/data_split.py`
  (`GroupShuffleSplit` on `swimmer_id`) and unit-tested.
- Seed fixed at 20260829 and recorded in the output.

**The test set is opened once.** Parameters are fitted on training data only
(Task 14). If the test set is examined and then anything is changed, every
subsequent result is exploratory and must be labelled as such.

## 6. What gets fitted, and what does not

This follows directly from the identifiability analysis in
`docs/parameters.md`, and it is the most important methodological decision here.

**Fitted to pacing data:** `beta_E` (M2), `beta_x` (M3), `gamma` (M4).

**Never fitted to pacing data:** `E0`, `R`, `phi`, `tau`, `C_D`, `A`, `rho`,
`eta_p`, `eta_g`.

**Why.** The optimal split distribution is provably `P_i ∝ w_i^(1/p)` with
`w_i = 1 + beta_x·x̄_i/L`. None of the excluded parameters appear. Fitting them
to split shapes would produce estimates that are pure noise, and reporting those
estimates as physiological findings would be the single worst error this project
could make.

Each model therefore has **exactly one free parameter** fitted to shape. That
makes the comparison fair without any complexity penalty, and it is why AIC is
not needed.

**Fitting procedure.** Grid search followed by scalar refinement over the single
free parameter, minimizing mean training RMSE of `P_i`. Search ranges,
optimizer, objective, final value and training error all recorded to
`results/model_calibration/`.

## 7. Handling the dive start

**This is the main threat to validity and it is stated up front.**

The model describes free swimming. Recorded split 1 contains a dive start worth
roughly 1.5-2.5 s. `beta_x` and the uncorrected start push observed splits in
the same direction, so a fit without correction will absorb the dive into the
fatigue parameter and overstate it.

Pre-registered handling:

1. Correct split 1 by `START_OFFSET_S` before computing `P_i`.
2. Report every headline result across a sensitivity band of 1.2 s to 2.8 s.
   [AMENDED 2026-08-31, before any calibration or test-set use: the original
   band was 1.2-2.4 s. Measured elite 15 m start times (Tor 2014; Rudnik 2023)
   imply a dive value up to ~3.0 s at this population's race pace, so the band
   was widened upward. Recorded as an amendment rather than silently edited.]
3. If the model ranking changes anywhere inside that band, **the conclusion is
   that the data cannot distinguish the models given start uncertainty.** Report
   that rather than picking the value that gives the cleanest answer.
4. Collect 15 m split times wherever available. They are the only way to measure
   the credit rather than assume it.

## 8. Primary analysis (Task 16)

Deviation from optimum and performance relative to expectation:

```
D_j = sqrt[ (1/4) * sum_i (P_ij - P_i*)^2 ]
I_j = (T_expected,j - T_actual,j) / T_expected,j
```

`T_expected` comes from `pre_race_pb` — the swimmer's best time **before** that
race. Using a later PB would leak the outcome into the predictor.

**Model:** mixed-effects regression with a random intercept per swimmer
(Task 17), because repeated races from one swimmer are not independent:

```
I_ij = b0 + b1*D_ij + b2*D_ij^2 + u_i + e_ij
```

Report `b1`, `b2`, 95% CIs, and the random-effect variance. A quadratic term is
included because theory predicts a **quadratic** penalty near the optimum, so a
linear-only model is mis-specified.

**Fall back to OLS with cluster-robust standard errors** if the random-effect
variance is not identifiable at the achieved sample size, and say so.

## 9. Statistical power, honestly

The predicted effect is small. A 5% opening error costs about 0.09 s out of
100 s, roughly 0.09% of race time. Meet-to-meet variation in a swimmer's 200
free is on the order of 1%.

**The theoretical effect is an order of magnitude smaller than the noise.**

Consequences, accepted in advance:

- 50 races will almost certainly **not** detect the deviation-performance
  relationship. That phase is a pipeline test, not a hypothesis test, exactly as
  Task 9 says.
- 200-300 races may still be underpowered for H1. The model-comparison question
  (Task 15) is better powered, because shape differences between M2, M3 and M4
  are large relative to noise.
- **A null result on H1 will be reported as a null result.** It is a real
  finding: it would mean pacing deviations of the size swimmers actually make
  cost less than the model implies, or that other factors dominate.

## 10. Pre-specified exclusions

Applied before any analysis:

- Missing or non-monotonic cumulative splits.
- `|split_200 - final_time| > 0.05 s`.
- Any 50 split outside 0.5x to 2.0x the race mean (relay-lead-off or timing
  errors).
- Relay lead-off legs (different start rules).
- Disqualified swims.
- Races where `pre_race_pb` is unknown, for the H1 analysis only. They are kept
  for the shape analysis, which does not need it.

Exclusion counts are reported. If exclusions exceed 15% of collected races, the
collection protocol gets revisited before analysis continues.

## 11. Deliverables

| Output | Path |
|---|---|
| Fitted parameters, training error | `results/model_calibration/` |
| Held-out comparison table | `results/validation/model_comparison.csv` |
| Deviation vs performance regression | `results/validation/` |
| Empirical descriptive figures | `figures/empirical/` |

## 12. Things that would invalidate the whole exercise

Stated now so they cannot be rationalized away later.

1. Fitted `beta_x` far outside a physiologically arguable range, which would
   mean it is fitting the dive start rather than fatigue.
2. Model ranking that flips within the start-credit sensitivity band.
3. Observed pacing that no model reproduces, in which case the missing mechanism
   is more interesting than the comparison.
4. Test-set RMSE much worse than training RMSE, indicating the single fitted
   parameter is absorbing sample idiosyncrasy.
