# Mathematical optimization of pacing in the 200 freestyle

![tests](https://github.com/omjoshi0925/SwimPacing/actions/workflows/tests.yml/badge.svg)

A differential-equation and constrained-optimization model of optimal pacing in
the 200 yard freestyle (SCY), built to be validated against real race data.

**Status.** The theoretical model is complete and verified: discrete
optimization, drag-derived cost function, ODE energy model, five competing
fatigue models (M0-M4), sensitivity analysis, and the full data pipeline.

**Registered results, 2026-09-03 (pilot-v0.2, frozen).** The dataset now
holds **345 usable races** by 248 male swimmers aged 15-18 across eleven
meets (1,382 raw rows, 16 meets, official checksum-verified Hy-Tek sections
and spot-verified transcriptions; `data/DATASET_VERSIONS.md`). The
pre-registered analysis was run once: fatigue parameters fitted on the
training side only (`results/model_calibration/fits_train_v0_2.csv`), the
swimmer-grouped test set opened once (89 races / 60 swimmers), results in
[`results/validation/report_v0_2.md`](results/validation/report_v0_2.md)
and the paper draft in `paper/`. Headline, applied mechanically under
`docs/validation_plan.md` §4 and §7:

- Observed pacing is positively split (91% of races). The even models
  (M0/M1) and the negative-split model (M2) are rejected on held-out
  accuracy at the registered 1.80 s start credit: mean split-share RMSE
  0.653 and 0.771 pp against 0.454 (M3) and 0.461 (M4), with bootstrap
  intervals on the differences well clear of zero.
- M3 (position-coupled cost) and M4 (fatigue-coupled ceiling) **tie**:
  difference 0.007 pp, CI [−0.019, +0.030]. The observed fade is
  front-loaded in kind (M4) but between the two in degree, and the last lap
  is faster than the third in half the races — a finishing kick no monotone
  mechanism in the family can produce.
- The ranking changes inside the registered start-credit band
  (M4 best at 1.2-1.6 s, M3 at 1.8-2.6 s, M0 at 2.8-3.4 s), so by §7.3 the
  data cannot distinguish the surviving models given start uncertainty.
  Fitted beta_x runs from 0.33 to 0.01 across the band.
- H1 (closer to the optimum → better vs pre-race PB) returns the null the
  plan anticipated (b1 CI includes zero for every model). A post-hoc,
  labelled supplement shows the registered fit's curvature came from three
  four-year-old PBs.

The first 80-race pilot (`results/validation/pilot_report.md`, corrected
2026-09-01 after a sign error in the start transform) is preserved unchanged
as the exploratory baseline. Synthetic pipeline fixtures remain quarantined
in `results/placeholder_data/` and `tests/fixtures/`.

---

## The research question

> What pacing strategy minimizes 200 freestyle race time under realistic
> energetic and fatigue constraints, and how closely does that theoretically
> optimal strategy match successful real-world performances?

## What the model says so far

**1. Even pacing is optimal, and it is a theorem rather than an assumption.**
Under a static energy budget with a velocity-only cost function, the four-split
problem is a convex program in split times whose unique global optimum is
perfectly even pacing. This holds for every cost exponent `p > 1` and every
choice of `k`, `R` and `E0`.

**2. The optimal *shape* is independent of the engine and the hull.** With
position-coupled economy decay the exact optimum is `ti ∝ wi^(1/p)`, where
`wi = 1 + beta_x xbar_i / L`. Aerobic capacity, anaerobic capacity, drag
coefficient, frontal area and both efficiencies change how *fast* the race is
swum and have literally no effect on how it is *divided*. A swimmer with a bigger
anaerobic tank should not go out faster. Confirmed numerically: every parameter
except `beta_x` leaves the split fractions at 0.25 to eight decimal places.

**3. Oxygen kinetics slow the race but do not bend the shape at all.** Total
aerobic supply depends only on race duration, so two profiles finishing in the
same time receive identical aerobic energy. "The swimmer starts before their
aerobic system is up to speed" is the most intuitive story for going out fast,
and within this model it is not a reason to, for any value of `tau`.

**4. The five models make three distinct qualitative predictions**, which is
what makes this a real comparison rather than a contest between near-identical
curves:

| Model | Mechanism | Predicted shape |
|---|---|---|
| M0 | none | exactly even |
| M1 | oxygen kinetics | exactly even |
| M2 | reserve-coupled cost | strong **negative** split |
| M3 | position-coupled cost | linear **positive** split |
| M4 | fatigue-coupled velocity ceiling | front-loaded **positive** split |

M3 and M4 are separable by *shape*, not just magnitude: M3 predicts an even fade
across the four 50s, M4 predicts most of the loss between the first and second.
Fifty races will already be informative about sign even if they are too few to
settle magnitude.

**5. Pacing penalties are real but modest.** Opening 3% hot costs 0.03 s;
opening 15% hot costs about 0.9 s. The penalty is locally quadratic, so small
errors are nearly free and large ones compound.

Full numbers, tables and caveats in [`docs/RESULTS.md`](docs/RESULTS.md).

---

## Quick start

```bash
pip install -r requirements.txt
python scripts/run_all.py                # every result and figure
python scripts/run_all.py --quick        # coarser grids and fewer restarts
python -m pytest tests -q                # full verification suite (~2 min)
python -m pytest tests -q -m "not slow"  # quick subset (~6 s), what CI runs
```

Measured on this project's reference environment: the quick tier is 146
tests in about 6 s (what CI runs); the `slow` tier adds five ODE-heavy
tests (151 total) that take about 21 minutes, nearly all of it in the two
parameter-recovery fits, which now use the reliable five-restart inner
solve (docs/calibration.md). For `run_all.py`, runtime depends
on hardware and settings; `--quick` trades grid resolution and solver restarts
for speed. Results land in
`results/` as CSV, figures in `figures/` as PNG and PDF.

```bash
python -m src.preprocessing data/raw/200_free_scy_raw.csv   # rebuild the processed file
python -m scripts.refresh_predictions                        # after editing MODELS
python -m scripts.fit_models --registered --dataset pilot-v0.2 \
    --out results/model_calibration/fits_train_v0_2.csv      # training side only, ~40 min
python -m scripts.evaluate_holdout                           # opens the test set ONCE (see plan §5)
```

### Using it directly

```python
from src import model, optimization, simulator
from src.parameters import REFERENCE, WORKING, SCY_200

# closed-form optimum
opt = model.optimal_solution_closed_form(REFERENCE, SCY_200)
print(opt["split_times"])       # [25.00, 25.00, 25.00, 25.00]
print(model.format_time(opt["race_time"]))   # 1:40.02

# numerical optimum, agrees to 1e-11 s
optimization.optimize(REFERENCE, SCY_200)

# simulate a chosen strategy
simulator.simulate([1.90, 1.85, 1.80, 1.78], WORKING, SCY_200)

# what a named strategy costs, at a matched energy budget
optimization.compare_strategies(REFERENCE, SCY_200)

# personalize: hold the hull fixed, calibrate the engine to a target time
fast = model.calibrate(95.0, WORKING, SCY_200, knob="E0")
```

---

## The model

**Objective.** Minimize `T = sum_i d/vi` over the four split velocities.

**Cost.** `C(v) = k v^p`, with the exponent derived from drag physics and the
coefficient built from separately measured components:

```
F_D  = (1/2) rho C_D A v^2       =>   P = F_D v = K_d v^3
C(v) = phi * P / (eta_p eta_g)   =>   k = phi * K_d / (eta_p eta_g),  p = 3
```

`C_D` = 0.30 and `A` = 0.230 m² are measured values (Zamparo et al. 2009), and
the resulting `K_d` = 34.4 sits inside the independently measured 22-38 band.
`phi` is a **course economy factor**, the model's one openly calibrated scalar:
it represents the per-metre discount of racing in a 25 yard pool with a dive and
seven turns, and it is 0.75-1.00 depending on the model variant.

**Energy.** A two-parameter critical-power structure with a finite anaerobic
reserve `E0` and an aerobic ceiling `R`, evolving as

```
dt/dx = 1 / v(x)
dE/dx = [ R(t) - C(v, E, x) ] / v(x)
t(0) = 0,  E(0) = E0,  E(x) >= 0 for all x
```

with optional oxygen kinetics `R(t) = R(1 - e^{-t/tau})` and two competing
economy-decay mechanisms.

**Three solvers, cross-checked.** A closed form, SLSQP in split-time space (where
the problem is convex), and direct ODE integration. They agree to about 1e-11 s.

Derivations: [`docs/01_derivation.md`](docs/01_derivation.md),
[`docs/02_hydrodynamics.md`](docs/02_hydrodynamics.md),
[`docs/03_ode_model.md`](docs/03_ode_model.md).

Competing models M0-M4: [`docs/model_definitions.md`](docs/model_definitions.md).
Parameter provenance and the A/B/C classification:
[`docs/parameters.md`](docs/parameters.md).
Pre-registered validation plan: [`docs/validation_plan.md`](docs/validation_plan.md).
Data schema and collection protocol: [`data/data_dictionary.md`](data/data_dictionary.md).

---

## Layout

```
src/
  parameters.py     Swimmer/Course dataclasses, the M0-M4 registry, every default
  model.py          cost function, drag, energy accounting, closed forms, calibration
  simulator.py      ODE integration, velocity profiles, named strategies
  optimization.py   SLSQP solvers, strategy comparison, opening-penalty curve
  sensitivity.py    parameter sweeps, elasticities, archetypes, Monte Carlo robustness
  preprocessing.py  race-file cleaning, quality flags, normalized pacing metrics
  data_split.py     train/test splitting grouped by swimmer
  visualization.py  every figure
scripts/
  run_all.py            reproduces all theoretical results and figures
  refresh_predictions.py recomputes the cached M2/M4 optima
tests/                tests that pin the claims the write-up makes
docs/                 derivations, parameters, models, validation plan, assumptions
data/                 schema, collection protocol, templates (no races yet)
results/
  theoretical/        model output
  sensitivity/        parameter sweeps
  validation/         empty until real data exists
  placeholder_data/   SYNTHETIC, clearly quarantined
figures/              generated output
```

---

## Reading the caveats first

[`docs/assumptions.md`](docs/assumptions.md) lists every assumption in three
tiers, with the direction of each bias and what would falsify the model. The four
that matter most:

0. **Two drag parameters were wrong and have been corrected.** `C_D` was 0.70
   and `A` was 0.090 m²; every measured value found puts `C_D` at 0.23-0.61 and
   active frontal area at 0.13-0.40 m². They had been chosen so their *product*
   landed in the right place while each factor sat outside the evidence. Both
   are now measured values, and the discrepancy that fix exposed is now carried
   openly by `phi` rather than hidden. Recorded because it is the kind of error
   a reviewer checking components would find immediately.

1. **Starts, turns and underwaters are not modelled.** This is the single largest
   reason real splits are positively split. A constant 1.80 s credit is applied
   to split 1 when comparing with real races, and that number is a
   literature-informed guess, not a measurement. It is the weakest number in the
   project and it sits directly on the main comparison.
2. **Velocity is constant within each 50.** Since cost is convex in velocity,
   this systematically *understates* energy cost, and the missing cost gets
   absorbed into the fitted `E0` and `R`.
3. **Gross mechanical efficiency is not a settled number.** Zamparo et al.
   (2005) report 0.20 ± 0.03; Kolmogorov et al. (2021) report 0.049-0.068. That
   factor of 3-4 is definitional rather than experimental, and it means `k` is
   **not identifiable from the literature**. Every absolute energy figure this
   model produces is model-internal.

3b. **The fatigue coefficients are Category C**, chosen to define the competing
   models rather than to describe a measured swimmer. They become fitted
   parameters in Task 14, at which point they are estimates, still not
   measurements. Because `beta_x` and the unmodelled start push observed splits
   the same way, fitting without a good start correction will overstate it.
4. **The predicted penalties may be too small to detect.** A 5% opening error
   costs about 0.09 s, inside the noise of a single swim. The empirical test
   needs many races and a well-specified expectation model, and it may come back
   null. That would still be worth reporting.

---

## What comes next

1. **Measure the dive-start credit.** 15 m splits at even one meet would pin
   the credit for its field; failing that, a pace-dependent term
   `c(v) = 15/v - t15` replaces a constant that is wrong in a known direction
   for slower swimmers. This is the decisive open quantity: the registered
   comparison is hostage to it.
2. **A model that can produce the finishing kick.** Every mechanism in M0-M4
   is monotone; the data are not. A stochastic-state (uncertainty about own
   reserve) formulation is the natural candidate and makes a testable
   prediction (the kick should shrink with experience).
3. **A better expectation model for H1.** Many races of few swimmers, with
   seed or season-best trajectories as expectation, rather than few races of
   many swimmers with a stale in-file PB.
4. **Upgrade the Tier-2 meets** (workbook transcriptions) to Tier-1 from the
   official PDFs, and admit the withheld meets (ALTO Valentine, Palooza 2025
   splits, TCA/TERA) once their official files are verified.
5. **Replicate elsewhere**: other regions, LCM, female and older swimmers.

Deliberately not started: the public tool, optimal control, other events,
machine learning. All of it comes after the start credit is measured.

---

## License

MIT. See `LICENSE`.
