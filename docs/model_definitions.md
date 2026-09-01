# Competing models M0 through M4

Task 5. Each model is a complete, separately falsifiable claim about what makes
late-race swimming different from early-race swimming. They are compared, not
combined.

All five share the same objective, the same measured hydrodynamic block, and the
same engine (`R` = 1250 W, `E0` = 50.32 kJ) and, in M1-M4, the same measured
oxygen-kinetics constant `tau` = 16.5 s (Pessoa Filho et al. 2012). They differ
only in which fatigue mechanism is active, plus a per-model course economy
factor `phi` calibrated so every variant reproduces a 1:40.0 optimum. Holding the engine fixed is what makes
the comparison about mechanism rather than about fitness.

---

## Shared framework

**States.** `t(x)` elapsed time, `E(x)` remaining energy reserve, with distance
`x` as the independent variable.

**Control.** `v(x)`, piecewise constant over the four 50s.

**Dynamics.**

```
dt/dx = 1 / v(x)
dE/dx = [ R(t) - C(v, E, x) ] / v(x)
```

**Initial conditions.** `t(0) = 0`, `E(0) = E0`.

**Boundary condition.** `x` runs 0 to `L` = 182.88 m.

**Path constraint.** `E(x) >= 0` for all `x`. A swimmer cannot borrow energy.

**Objective.** Minimize `T = t(L)`.

**Cost.** `C(v, E, x) = k·v^p·(1 + beta_E·D + beta_x·x/L)` where
`D = 1 - E/E0` and `k = phi·K_d/(eta_p·eta_g)`, `p = 3`.

**Supply.** `R(t) = R·(1 - e^(-t/tau))`, with `tau = 0` meaning instantaneous.

**Velocity ceiling.** `v(x) <= v_max·(1 - gamma·D)`.

Setting `beta_E = beta_x = gamma = 0` and `tau = 0` recovers M0.

---

## M0 — constant economy

**Purpose.** Baseline. What does the optimum look like if nothing about the
swimmer changes during the race?

| | |
|---|---|
| Parameters | `tau` = 0, `beta_E` = 0, `beta_x` = 0, `gamma` = 0, `phi` = 1.000 |
| Cost | `C(v) = k·v³`, constant economy |
| Supply | `R` constant from the gun |

**Prediction: exactly even pacing.** Split fractions 0.2500 each, `T` = 1:40.00.

This is not an approximation or a numerical result. In split-time coordinates
the problem is a linear objective over a convex feasible set, and the KKT
conditions force all four split times equal for every `p > 1` and every
`k`, `R`, `E0`. See `docs/01_derivation.md` §3.

**Biological interpretation.** A swimmer who is metabolically identical at the
150 to what they were at the 50, and who is limited only by a fixed fuel budget.

**Assumptions.** Constant economy; no oxygen kinetics; velocity constant within
each 50; starts, turns and underwaters absorbed into `phi`.

**Weaknesses.** Predicts even pacing, and real 200s are positively split. As a
model of observed behaviour it is wrong. As a null hypothesis it is exactly
right, and it is the benchmark every other model has to beat.

---

## M1 — oxygen kinetics

**Purpose.** Test the most intuitive physiological story for going out fast:
the aerobic system is not up to speed at the start, so early swimming is paid
for anaerobically.

| | |
|---|---|
| Parameters | `tau` = 16.5 s, all fatigue terms 0, `phi` = 0.8826 |
| Supply | `R(t) = R(1 - e^(-t/16.5))` |

**Prediction: exactly even pacing, and a slower race.** Split fractions 0.2500
each.

**Why.** Total aerobic supply over the race is
`R[T - tau(1 - e^(-T/tau))]`, a function of race *duration* alone. Two velocity
profiles finishing in the same time receive identical aerobic energy, so the
terminal budget cannot distinguish them and the optimum is unmoved.

**This is a useful negative result.** The intuitive story does not survive
contact with the algebra. Delayed oxygen uptake makes the race slower without
making an uneven race better.

**Boundary.** With a small enough reserve and slow enough kinetics the energy
path constraint can bind and shade the optimum off even; at the calibrated
`E0` this does not occur for any `tau` tested up to 200 s (see docs/RESULTS.md,
retraction note).

**Assumptions.** Mono-exponential kinetics; no slow component; `tau` independent
of intensity.

**Weaknesses.** Split shapes carry essentially no information about `tau`, so
this model is nearly unfalsifiable from split data alone. It is included because
ruling it out is informative, not because it is expected to win. (`tau` itself
is now a cited measured value; see docs/parameters.md.)

---

## M2 — reserve-coupled fatigue

**Purpose.** Economy degrades as the fuel tank empties.

| | |
|---|---|
| Parameters | `tau` = 16.5 s, `beta_E` = 0.28, `phi` = 0.7719 |
| Cost | `C = k·v³·(1 + beta_E·D)`, `D = 1 - E/E0` |

**Prediction: a strong negative split.** Optimal splits 27.68 / 25.90 / 24.01 /
22.41, fractions 0.277 / 0.259 / 0.240 / 0.224.

**Why.** Holding back early keeps `E` high, which keeps economy good, which
leaves more usable energy later. The reserve becomes worth protecting for its
own sake. At the finish there is no future left to protect, so the optimum
empties the tank.

**Biological interpretation.** A swimmer whose stroke falls apart in proportion
to how much they have spent, independent of how long they have been racing.

**Assumptions.** Economy is a function of the current reserve only, with no
memory of the path taken to reach it.

**Weaknesses.** **Predicts the wrong sign.** Real 200 frees are positively
split, and remain so after crediting the dive start. The last-50 dump is also an
end-game artifact: the model stops caring about economy exactly when the race
ends. Included as a genuine competitor that the data should reject, which makes
its rejection informative rather than assumed.

---

## M3 — position-coupled fatigue

**Purpose.** Economy degrades with time and accumulated stroke count, regardless
of effort.

| | |
|---|---|
| Parameters | `tau` = 16.5 s, `beta_x` = 0.28, `phi` = 0.7755 |
| Cost | `C = k·v³·(1 + beta_x·x/L)` |

**Prediction: a smooth, near-linear positive split.** Optimal splits 24.22 /
24.75 / 25.27 / 25.76, fractions 0.2422 / 0.2475 / 0.2527 / 0.2576.

**Why.** The same velocity is simply cheaper early than late, so speed is worth
banking early. Because the multiplier is linear in `x`, the per-split weight
`w_i = 1 + beta_x·x̄_i/L` is **exact** rather than a quadrature approximation, and
the optimum has a closed form: `t_i ∝ w_i^(1/p)`.

**Biological interpretation.** Declining propelling efficiency as the race
progresses, from rising body position, falling stroke length, and accumulating
metabolite.

**Assumptions.** Decay is linear in distance. There is no strong physiological
reason it should be linear rather than accelerating over the last 50.

**Weaknesses.** The mechanism now has a measured basis: Figueiredo et al.
(2011) report propelling efficiency falling significantly from lap 1 to lap 4
of a 200 m front crawl (0.40-0.43, p = 0.002). But their measured lap energy
cost is U-shaped (1.71/1.56/1.44/1.70 kJ/m), not linearly rising, so the linear
form is a first approximation at best. And `beta_x` and the unmodelled dive
start push observed splits in the **same direction**, so a fit without a good
start correction will absorb the dive into the fatigue parameter. Measuring the
start credit is a prerequisite for taking any fitted `beta_x` seriously.

---

## M4 — fatigue-coupled velocity ceiling

**Purpose.** Reach positive splitting through a *constraint* rather than through
cost. The swimmer does not choose to slow down; they become unable to go fast.

| | |
|---|---|
| Parameters | `tau` = 16.5 s, `gamma` = 0.18, `phi` = 0.8378 |
| Constraint | `v(x) <= v_max·(1 - gamma·D)` |

**Prediction: a front-loaded positive split with a step.** Optimal splits 23.96
/ 24.92 / 25.41 / 25.71 (fractions .2396/.2492/.2541/.2571). The ceiling is
**binding at the optimum** (headroom 0.0000 m/s).

**Why.** This is the Keller structure: go as fast as the ceiling allows while
the ceiling is still high, then follow it down. Speed early is not just cheaper,
it is *available*, and later it is not.

**Biological interpretation.** Peripheral fatigue imposing a hard limit on
attainable velocity as the reserve empties, rather than merely making speed
expensive.

**This is the most empirically interesting competitor**, because it is
distinguishable from M3 by shape rather than only by magnitude:

| | split 1→2 drop | split 3→4 drop | shape |
|---|---|---|---|
| M3 | 0.53 s | 0.49 s | near-linear fade |
| M4 | 0.99 s | 0.24 s | front-loaded step, then flattening |

M3 predicts an even fade. M4 predicts most of the loss between the first and
second 50 and comparatively little at the end. **Real split sheets can tell
these apart**, and doing so is more informative than any RMSE comparison of
overall fit.

**Assumptions.** The ceiling falls linearly with the spent fraction of the
reserve; `v_max` is known.

**Weaknesses.** `v_max` is assumed (Category C) and is load-bearing here, unlike
in M0-M3 where it is slack. `gamma` and `v_max` are partly confounded: a lower
ceiling with gentler decay resembles a higher ceiling with steeper decay. Also
the most expensive model to solve, since it has no closed form and needs the
ceiling enforced on the full integration grid.

---

## Summary

| Model | Mechanism | Predicted shape | `phi` | Split fractions |
|---|---|---|---|---|
| M0 | none | exactly even | 1.000 | .2500 .2500 .2500 .2500 |
| M1 | oxygen kinetics | exactly even | 0.883 | .2500 .2500 .2500 .2500 |
| M2 | reserve-coupled cost | strong negative | 0.772 | .2768 .2590 .2401 .2241 |
| M3 | position-coupled cost | linear positive | 0.776 | .2422 .2475 .2527 .2576 |
| M4 | fatigue-coupled ceiling | front-loaded positive | 0.838 | .2396 .2492 .2541 .2571 |

(phi and the M2/M4 shapes recalibrated 2026-08-31 at the cited `tau` = 16.5 s.)

### Raced space vs recorded space

The tables above are **raced space**: free swimming, no dive. A recorded split
sheet lives in **recorded space**, where the dive makes lap 1 faster by the
course start credit `S` (`SCY_200.start_credit_s` = 1.80 s). One transform per
comparison, never both: model → recorded subtracts `S` from model lap 1
(`model.raced_to_recorded`); data → raced adds `S` to observed lap 1
(`model.recorded_to_raced`, the "free-swimming equivalent"). At `T` = 100 s
and `S` = 1.80 the recorded-space predictions are:

| Model | Recorded split fractions (S = 1.8 s) |
|---|---|
| M0 / M1 | .2363 .2546 .2546 .2546 |
| M2 | .2635 .2637 .2445 .2282 |
| M3 | .2283 .2520 .2573 .2623 |
| M4 | .2257 .2538 .2588 .2618 |

Recorded-space fractions depend (weakly) on `T` because `S` is a time, not a
share; the raced-space tables are the scale-free ones. The pipeline compares
free-swimming-equivalent observed shares against raced-space predictions.

Three distinct qualitative predictions across five models: even, negative, and
two different kinds of positive. That is a real model comparison rather than a
contest between near-identical curves, and it means the first fifty races will
already be informative about *sign* even if they are too few to settle
*magnitude*.

**M0 and M1 make identical shape predictions**, so split data alone can never
separate them. They are separable only by race time, which depends on parameters
the data cannot identify. Report them as a single shape hypothesis and say so.

## What each model would need to be believed

- **M0** wins if observed pacing is even after start correction. It is the null.
- **M1** cannot win on shape. Do not claim support for it from split data.
- **M2** wins if observed pacing is *negatively* split after start correction.
- **M3** wins if the fade is close to linear across the four 50s.
- **M4** wins if the loss is concentrated between the first and second 50.

If the answer is M3 or M4, the follow-up question is immediately whether the
fitted fatigue parameter is doing physiological work or is standing in for the
dive start. Task 19's eight-segment model is what settles that, and `phi` moving
toward 1 is the signal that it worked.
