# The differential-equation model

Phase 5. The discrete model treats energy as a single budget checked at the end.
This phase makes energy a state variable that evolves through the race, which
lets the model express things the budget version cannot: that oxygen uptake takes
time to rise, and that stroke economy degrades.

---

## 1. State equations

Distance `x` is the independent variable rather than time. The terminal condition
`x(T) = L` is then a fixed integration limit instead of an event to detect.

**States**

- `t(x)`, elapsed time at distance `x`, seconds
- `E(x)`, remaining anaerobic reserve, joules

**Control**

- `v(x)`, swimming velocity, piecewise constant over the four 50s

**Equations**

```
dt/dx = 1 / v(x)
dE/dx = [ R(t) - C(v, E, x) ] / v(x)
```

**Initial conditions**

```
t(0) = 0,    E(0) = E0
```

**Boundary and path conditions**

```
x runs from 0 to L = 182.88 m
E(x) >= 0   for all x
```

**Objective**

```
minimize T = t(L)
```

### Reading the equations

`dt/dx = 1/v` is bookkeeping: going slower takes longer.

`dE/dx` is the physiology. The numerator is supply minus demand, in watts. When
the swimmer races above their aerobic ceiling the numerator is negative and the
reserve drains. Dividing by `v` converts a rate per second into a rate per metre.

The path constraint `E >= 0` is the one that has teeth. The simulator does **not**
enforce it. It integrates the prescribed strategy and reports `min_energy`, so an
impossible strategy shows up as a negative reserve rather than being silently
repaired. A real swimmer with an empty reserve does not go into debt, they slow
down, so `min_energy < 0` means "this plan cannot be executed", not "this is what
the race looked like".

---

## 2. Oxygen kinetics

Oxygen uptake does not jump to its ceiling at the gun. Modelled as a
first-order approach with time constant `tau`:

```
R(t) = R (1 - e^{-t/tau})
```

`tau` near 20 s is standard for the primary component of VO2 kinetics in trained
athletes. Setting `tau = 0` recovers the constant-`R` model.

### The total supply depends only on race duration

Integrating over the race:

```
AerobicSupply(T) = integral_0^T R(1 - e^{-s/tau}) ds
                 = R [ T - tau (1 - e^{-T/tau}) ]
```

**This is a function of `T` alone.** Two velocity profiles that finish in the same
time receive exactly the same aerobic energy, no matter how the velocity was
distributed. The terminal budget constraint therefore cannot tell them apart.

> ### Result 3
>
> **Adding realistic oxygen kinetics slows the race but does not change the
> optimal pacing shape, as long as the energy path constraint stays slack.**

Numerically, over `tau` from 0 to 40 s the optimal race time moves from 100.0 s
to 111.9 s and the optimal split fractions stay at 0.25 each to eight decimal
places.

This is a useful negative result. "The swimmer starts before their aerobic
system is up to speed" is the most intuitive physiological story for why one
might go out fast, and within this model it is simply not a reason to.

### Where it stops holding: RETRACTED

An earlier version reported that past `tau` ≈ 40 s the energy path constraint
binds and the optimum moves slightly off even. **That was an artifact of an
undersized `E0`** (35 kJ, since corrected to 50.32 kJ during the drag-parameter
fix). With a correctly sized reserve the constraint is slack for every `tau`
tested up to 200 s.

The mechanism is genuine and still implemented and tested. A small reserve with
slow kinetics does still produce an infeasible terminal-constraint solution, for
example `E0` = 20 kJ at `tau` = 20 s, and in that regime the closed form is only
a lower bound on the true race time. It simply does not occur near the calibrated
parameters, so at this calibration the even-pacing result under M1 holds
unconditionally.

---

## 3. Two fatigue mechanisms that disagree

Something must make late-race swimming different from early-race swimming, or
the model can never produce a positive split. The obvious candidate is that
economy degrades as the swimmer tires. There are two natural ways to write that,
and **they make opposite predictions**, which makes them empirically separable.

### 3a. Reserve-coupled decay

Economy depends on how much fuel is left:

```
C = k v^p (1 + beta_E * D),     D = 1 - E/E0
```

The intuition is that a swimmer with an empty tank has lost their stroke.

**Prediction: a strong negative split.** Holding back early keeps `E` high, which
keeps economy good, which leaves more usable energy for later. The reserve is
worth preserving for its own sake. And at the very end there is no future left to
protect, so the optimum dumps everything.

Numerically, `beta_E = 0.30` gives split fractions
`[0.298, 0.264, 0.232, 0.206]`, meaning the last 50 is much the fastest.

### 3b. Position-coupled decay

Economy depends on how far into the race the swimmer is, regardless of effort:

```
C = k v^p (1 + beta_x * x/L)
```

The intuition is accumulated stroke count, rising body position, lactate
accumulation: things that happen because time has passed.

**Prediction: a positive split.** The same velocity is simply cheaper early than
late, so speed is worth banking early. From `01_derivation.md` section 5 the
optimal split times satisfy `ti ∝ wi^(1/p)` with `wi = 1 + beta_x xbar_i / L`.

Numerically, `beta_x = 0.30` gives `[0.242, 0.247, 0.253, 0.258]`.

### 3c. The comparison

| mechanism | prediction | matches real races? |
|---|---|---|
| none (constant economy) | exactly even | no |
| oxygen kinetics only | exactly even | no |
| reserve-coupled `beta_E` | strong negative split | no, backwards |
| position-coupled `beta_x` | positive split | yes |

Real 200 freestyles are positively split, and they remain positively split after
the dive start is credited back to split 1. That is evidence against `beta_E` as
the dominant mechanism and in favour of `beta_x`.

**This is the most useful thing the ODE model does.** It converts a vague claim
("swimmers get tired") into two rival specifications that differ in sign, so a
dataset of split sheets can choose between them. Phase 12 model comparison should
be built around exactly this contrast.

A caution: `beta_x` and the unmodelled dive start push observed splits in the
same direction, so estimating `beta_x` from raw split sheets without a start
correction will absorb the start into the fatigue parameter and overstate it.
The start credit exists to keep those separate, and its value is currently a
literature-informed guess rather than a measurement. Making it a measurement is
the highest-value item in Phase 9.

### 3d. A third route, not yet exercised

`gamma` implements a fatigue-coupled velocity ceiling:

```
v_max(D) = v_max (1 - gamma D)
```

This produces a positive split through a *constraint* rather than through cost:
the swimmer banks speed early because late in the race they physically cannot go
fast. It is implemented in the simulator and left at zero by default. It is worth
exercising, because it makes a different secondary prediction from `beta_x`
(a hard velocity floor at the finish rather than a smooth cost gradient) and the
two may be separable in the data.

---

## 4. Calibration of the working model

All five model variants share **one engine**: `R` = 1250 W and `E0` = 50.32 kJ.
That is deliberate. If each variant got its own reserve, the comparison would be
partly about fitness rather than purely about mechanism.

What moves instead is `phi`, the course economy factor, calibrated per variant so
every one reproduces a 1:40.0 optimum:

| Model | `phi` | Reading |
|---|---|---|
| M0 | 1.000 | no course discount claimed |
| M1 | 0.858 | 14% discount needed to pay for slow oxygen kinetics |
| M2 | 0.747 | 25% |
| M3 | 0.754 | 25% |
| M4 | 0.811 | 19% |

**`phi` is readable as a diagnostic.** A variant needing `phi` far from 1 is
demanding a large unexplained economy. A 200 SCY contains a dive, seven turns and
eight underwater phases over 182.88 m, so a discount of 15-25% is plausible, but
it is asserted rather than derived. Task 19's eight-segment start-and-turn model
is what would test it: an explicit turn model should drive `phi` toward 1, and if
it does not, the discount was never about turns.

**Do not read `E0` as physiology.** It is calibrated (Category B), it carries a
physiological name, and it absorbs modelling error. `docs/parameters.md` states
the language rule: "the model uses an effective energy-reserve parameter", never
"the swimmer has an anaerobic reserve of".

---

## 5. Numerical method

`scipy.integrate.solve_ivp` with LSODA, `rtol = atol = 1e-10`, and `max_step`
capped at a quarter of a split so the piecewise-constant control is never
stepped over.

Three independent solvers are cross-checked and agree to about 1e-11 s:

1. the closed form (`model.optimal_solution_closed_form`)
2. SLSQP in split-time space (`optimization.optimize_static`)
3. the ODE simulator (`simulator.simulate`)

Two numerical points worth recording, since both cost real debugging time:

- **Scaling matters.** The objective is order 1e2 seconds and the raw energy
  constraint is order 1e4 joules. With that mismatch SLSQP stops early and
  reports a converged solution that is 1e-4 s off. Normalizing the constraint by
  `E0` and the objective by a reference duration fixes it.
- **`res.success` is too strict.** SLSQP routinely returns "Positive directional
  derivative for linesearch" at a point that is fully converged and feasible.
  Discarding those throws away correct answers, so results are accepted on the
  constraint residual instead.
