# Assumptions

Every assumption the model currently makes, what it buys, and what it costs.
Grouped by how likely each is to change a conclusion. This document is meant to
be the honest half of the project and should be sent to any reviewer along with
the results.

---

## Tier 1: assumptions that could change the headline conclusions

### A1. Starts, turns and underwaters are not modelled

The model describes free swimming. A SCY 200 has a dive start and seven turns,
and the underwater phase after each is faster and differently economical from
surface swimming.

**Why it matters most.** This is the single largest reason real splits are
positively split. Split 1 contains a dive worth roughly 1.7 to 3.0 s relative
to racing into that 50 at pace, the band implied by measured 15 m start times
(Tor et al. 2014; Rudnik et al. 2023). If the start is not credited back before
comparing with the model, the entire dive advantage is misattributed to
physiology.

**Current handling.** A constant credit (`Course.start_credit_s` = 1.80 s)
maps between raced and recorded space: subtracted from model lap 1, or added
to observed lap 1 — one transform per comparison (`docs/model_definitions.md`,
"Raced space vs recorded space"; a sign error that double-counted the credit
was found and fixed 2026-09-01). Because it is constant it shifts `T` by a
constant and cannot change the optimum, which is why it is applied only at
comparison time and never inside the optimizer.

**Why this is still weak — now with measurements (2026-09-01).** 1.80 s is
elite-anchored, and the credit is provably pace-dependent: S ≈ 15/v − t15
gives 3.1-3.4 s at the pilot field's race pace, and the pilot model ranking
changes across the registered 1.2-3.4 s band, so per validation-plan §7.3 the
surviving models are not distinguishable until S is measured. The turn
literature now quantifies what the un-modelled walls carry: turn sections are
~51% of 200 m SC race time (Cuenca-Fernández 2022; Born 2021), push-off
leaves the wall at 2.96 m/s vs 1.41 m/s swimming (Born 2022), and underwater
kicking is 21-28% faster than surface swimming within the same swimmers
(Veiga 2022). Turns 2-7 are still not credited at all, on the assumption
their effect distributes roughly evenly across laps 2-4.

**Fix.** Measure the start: 15 m or 25 m splits wherever published, or a
per-race pace-dependent credit S(v) = 15/v − t15 as the minimum upgrade; then
the Task 19 eight-segment model, whose target is driving `phi` toward 1.

**The minimum upgrade, tried exploratorily (2026-09-06, roadmap band K).**
S(v) = 15/v − t15 with v = 182.88/T and t15 from the literature
(`docs/parameters.md`) was run per race, with the test set already open, so
as an exploratory analysis only (`docs/validation_plan.md`, declaration of
2026-09-06; `results/validation/exploratory_start_credit_report.md`). What
it does NOT fix is stated here so it is not mistaken for the eight-segment
model: S(v) compares the dive to swimming 15 m at with-turns race pace, not
to a turn push-off over the same 15 m. Laps 2-4 also open with a push-off
and an underwater phase, which the free-swimming model does not carry
either, so the per-race credit inherits the constant-S model's approximation
that the walls' contribution distributes across laps 2-4 and cancels in the
comparison. Only the eight-segment model removes it. Two further limits are
structural: v is the whole-race velocity, which contains the dive-assisted
lap 1 (a stated circularity), and an elite t15 applied to this field's slow
tail assigns an elite start to a ~2:40 swimmer, where the regime stops being
physical (the exploratory report states the boundary for each regime).

### A2. Velocity is constant within each 50

**Cost.** Real velocity oscillates within every stroke cycle and spikes off every
wall. Because `C(v)` is convex, the cost of a fluctuating velocity is strictly
greater than the cost of its mean, by Jensen's inequality. **The model
systematically understates energy cost**, and understates it more for swimmers
with more variable velocity.

**Direction of the bias.** This inflates the fitted `E0` and `R`, absorbing the
missing cost into the engine parameters.

**A sharper edge to this assumption (2026-09-01).** Aftalion & Bonnans (2014)
prove that in a runner model with anaerobic energy re-creation on
deceleration, constant speed is NOT optimal — deliberate velocity variation
pays. This model excludes re-creation and within-lap dynamics by assumption,
which is what makes even pacing a theorem here (docs/01_derivation.md §9).
Split-sheet data cannot see within-lap oscillation either way, so this
assumption is untestable at the data's resolution and is stated rather than
defended.

### A3. Economy decay is linear in position

`C = k v^p (1 + beta_x x/L)` is the simplest specification that produces a
positive split. There is no strong physiological reason it should be linear
rather than, say, accelerating in the last 50.

**The decay is measured; the linear form is not (2026-09-03).** Figueiredo et
al. (2011, full text) measured arm-stroke propelling efficiency falling
significantly from lap 1 to lap 4 of a 200 m front crawl (p = 0.002), so
within-race economy decay is no longer an assumption. Their lap energy cost,
however, runs 1.71 / 1.56 / 1.44 / 1.70 kJ/m — **U-shaped, not monotone**. Lap
cost also moves with lap velocity, so this is a caution against the linear form
rather than a clean refutation of it, and `beta_x` is better read as a summary
of net within-race decay than as a decay rate. The assumption stays in Tier 1.

**Cost.** The optimal shape is `Pi ∝ wi^(1/p)`, so the *form* of the decay
directly determines the *form* of the prediction. A convex decay profile would
predict more fade at the end than the current one does.

**Fix.** Phase 12 should compare linear, quadratic and piecewise decay profiles
on the same data rather than assuming linear.

### A4. `E0` and `R` are constant within a race

No reserve recovery, no slow-component drift in oxygen cost, no decline in the
aerobic ceiling.

**Cost.** For a race of about 100 s this is defensible. It would not be for a
500 or a mile.

---

## Tier 2: assumptions that affect magnitudes but probably not conclusions

### A5. Quadratic drag with a constant `C_D`

`F_D = (1/2) rho C_D A v^2` across the whole raced velocity range. Real active
drag exponents measure a little above 2, and wave drag rises steeply near hull
speed.

**Mitigation.** `p` is swept from 2.0 to 4.5 and the optimal shape is unchanged
throughout, so the conclusions are not sensitive to getting the exponent exactly
right. The absolute race time is.

### A6. Efficiencies are constant

`eta_p = 0.60` and `eta_g = 0.20`, fixed. Propelling efficiency in particular
falls as a swimmer tires and as velocity rises.

**Note.** A falling `eta_p` through the race is mathematically equivalent to the
`beta_x` economy-decay term, so this assumption is not so much violated as
relocated into a parameter that is explicitly fitted.

### A7. The optimum exhausts the reserve exactly

Follows from the KKT conditions rather than being assumed, but it does depend on
`E0` being genuinely all-usable. Real swimmers hold something back, deliberately
or not.

### A8. The swimmer executes the plan exactly

No pacing noise. Real swimmers miss their target splits, and the miss is
correlated with how aggressive the plan is. Since the penalty function is convex,
**noise around a plan is itself costly**, so a plan that is optimal under perfect
execution is not necessarily optimal under realistic execution error. An
aggressive opening may be worse than the deterministic penalty suggests.

**Fix.** Worth modelling directly: minimize expected time under execution noise
rather than time under perfect execution. This is a genuinely novel extension and
a good candidate for the paper.

---

## Tier 3: scope limitations, stated rather than defended

- **A9.** One event (200 free), one course (SCY), one population (male, 15 to 18).
  Nothing here has been checked against LCM, other strokes, other distances or
  female swimmers.
- **A10.** No tactical or psychological effects. The model races a clock, not a
  field. Real 200s are affected by who is in the next lane, by whether a swimmer
  needs to win or to make a time standard, and by prelims-versus-finals context.
- **A11.** No temperature, altitude, suit or water-quality effects.
- **A12.** Four decision variables. The true control is continuous, `u(t)`. Phase
  14 addresses this; until then the four-split discretization is an approximation
  whose error is unmeasured.
- **A13.** All parameters are point values. No uncertainty is propagated except in
  `sensitivity.penalty_robustness`, which perturbs six parameters lognormally at
  10% CV and reports interquartile ranges on the pacing penalty.

---

## Parameter provenance

**Superseded.** The authoritative provenance record is now
[`parameters.md`](parameters.md), which classifies every parameter as
Category A (literature-supported), B (calibrated) or C (exploratory) and marks
the ones with no citation yet as PROVENANCE GAP.

**Summary refreshed 2026-09-03.** The table below had drifted from that record:
it still carried `tau` at the superseded 20 s, two PROVENANCE GAP flags that the
2026-08-31 literature passes closed, and the pre-`Course` name for the start
credit. Categories now match `parameters.md`; fitted values are read from
`results/model_calibration/fits_train_v0_2.csv`.

| parameter | value | basis |
|---|---|---|
| `rho` | 997 kg/m^3 | A, physical |
| `C_D` | 0.30 | A, Zamparo et al. 2009. **Corrected from 0.70**, which was above every measured value. |
| `A` | 0.230 m^2 | A, Zamparo et al. 2009. **Corrected from 0.090**, which was below every measured value. |
| `eta_p` | 0.60 | A, Toussaint & Beek 1992; literature spans 0.40 to 0.71 |
| `eta_g` | 0.20 | A but **contested**: 0.20 (Zamparo 2005) vs 0.049-0.068 (Kolmogorov 2021) |
| `p` | 3.0 | derived from quadratic drag; measured exponent implies 3.22 |
| `phi` | 0.77 to 1.00 | B, calibrated per model variant; the SCY turn and underwater discount. The turn literature implies 0.80-0.95, which M2 and M3 sit just below. |
| `R` | 1250 W | B, calibrated jointly with `E0`; VO2max-plausible (Pessoa Filho et al. 2012). Residual gap: no absolute VO2max for trained males 15-18. |
| `E0` | 50.32 kJ | B, calibrated to a 1:40 optimum; sits inside the measured AOD band for age-matched swimmers (Campos et al. 2022) |
| `tau` | 16.5 s | A, Pessoa Filho et al. 2012 (16.5 +/- 5.1 s, severe intensity, well-trained males); Sousa et al. 2014 puts the fast-component range at 15-18 s in swimmers whose age spread covers this project's 15-18. **Was 20 s, C, PROVENANCE GAP.** |
| `beta_E`, `beta_x`, `gamma` | 0.28, 0.28, 0.18 | C, these registry values define M2, M3 and M4. Fitted once on pilot-v0.2 train (n=256): 0.02 (at the lower bound), 0.228, 0.269 — estimates, not measurements. |
| `v_max` | 2.10 m/s | C, assumed; slack except in M4 |
| `Course.start_credit_s` (legacy alias `START_OFFSET_S`) | 1.80 s | B, bracketed by measured 15 m start times (Tor et al. 2014; Rudnik et al. 2023) implying 1.7-3.0 s. No longer a provenance gap, but still the decisive number: the model ranking changes across the registered 1.2-3.4 s band. |

**Units warning.** `E0` is metabolic energy, not mechanical work. Published `W'`
values of 15 to 25 kJ are mechanical. The conversion is a **multiplication**:

```
mechanical energy = metabolic energy x efficiency
```

So E0 = 50.32 kJ metabolic is 50.32 x 0.20 = 10.06 kJ of mechanical work.
An earlier version of this document said "divide", which inflates the figure by
roughly an order of magnitude. Fixed.

---

## What would falsify the model

Stated in advance, so Phase 11 is a test rather than a search for confirmation.

1. **If real splits are negatively split after start correction**, the `beta_x`
   mechanism is wrong and `beta_E` deserves another look.
2. **If the optimal shape varies systematically with swimmer speed** in a way the
   model cannot reproduce by varying `beta_x` alone, then something other than
   economy decay is driving pacing.
3. **If deviation from the theoretical optimum is uncorrelated with performance**
   relative to expectation, the whole premise that pacing costs time is not
   supported at the magnitudes this model predicts.
4. **If the estimated `beta_x` needed to match observed splits is far outside a
   physiologically plausible range**, the model is fitting the dive start rather
   than fatigue.

Point 3 deserves emphasis: the predicted penalties are small. A 5% opening error
costs about 0.09 s. That is inside the noise of a single swim, so the empirical
test needs many races and a well-specified expectation model, and it may well
come back null. A null result would be worth reporting.
