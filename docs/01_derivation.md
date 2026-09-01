# Derivation of the discrete four-split model

Phase 3 and Phase 7. This is the mathematical core of the project. Everything
later either relaxes an assumption made here or tests a prediction made here.

---

## 1. Setup

The 200 freestyle is divided into `n = 4` segments of equal distance `d`. For
SCY, `d = 50 yd = 45.72 m` and the total distance is `L = 4d = 182.88 m`.

**Decision variables.** The mean velocity on each segment:

```
v = (v1, v2, v3, v4),    vi > 0
```

**Objective.** Total race time:

```
T(v) = sum_i d / vi
```

**Goal.** Minimize `T(v)` subject to the swimmer's energetics.

### 1.1 Metabolic cost

Let `C(v)` be the rate at which the swimmer burns metabolic energy at velocity
`v`, in watts:

```
C(v) = k v^p
```

`p` is derived from hydrodynamics in `02_hydrodynamics.md` and equals 3. `k` is
also derived there. Both are treated as free parameters here so the structure of
the result does not depend on the physics.

Energy spent on segment `i` is the cost rate times the segment duration:

```
Ei = C(vi) * ti = k vi^p * (d / vi) = k d vi^(p-1)
```

**The exponent drops by one.** Cost per unit *time* scales with `v^p`, but cost
per unit *distance* scales with `v^(p-1)`. Since a race is a fixed distance, it
is `v^(p-1)` that matters. With `p = 3`, the cost of a 50 is quadratic in its
velocity.

### 1.2 Energy supply

Two sources, following the two-parameter critical-power framework:

- `R`, the aerobic ceiling in watts, available continuously
- `E0`, a finite anaerobic reserve in joules

The reserve after segment `j` is

```
Ej = E0 + R * (t1 + ... + tj) - (E1 + ... + Ej)
```

**Constraints.**

```
Ej >= 0     for j = 1, 2, 3, 4        (energy path constraint)
vmin <= vi <= vmax                     (kinematic bounds)
```

The `j = 4` case is the terminal constraint. The `j < 4` cases say the swimmer
cannot borrow against energy they have not produced yet.

---

## 2. The problem is convex in split times

Reparametrize by segment duration `ti = d / vi`, so `vi = d / ti`. This
substitution is a bijection on the positive reals and is the single most
important step in the derivation.

The objective becomes **linear**:

```
T(t) = sum_i ti
```

The energy demand on segment `i` becomes

```
Ei = k d (d/ti)^(p-1) = k d^p ti^(1-p)
```

so the terminal constraint is

```
f(t) = k d^p sum_i ti^(1-p) - R sum_i ti - E0  <=  0
```

**Claim.** `f` is convex on `t > 0` for any `p > 1`.

*Proof.* `f` is a sum of terms. Each `ti^(1-p)` has second derivative
`(1-p)(-p) ti^(-p-1) = p(p-1) ti^(-p-1) > 0` for `p > 1` and `ti > 0`, so each is
convex. The term `-R sum ti` is linear, hence convex. `-E0` is constant. A sum of
convex functions is convex. ∎

The feasible set `{t : f(t) <= 0}` is a sublevel set of a convex function, hence
convex. The bound constraints are a box, also convex. So:

> **The problem is a convex program: a linear objective over a convex feasible
> set.** Every local optimum is global, and KKT conditions are sufficient as
> well as necessary.

This is worth emphasizing because it is not obvious in the original variables.
In `v`-space the constraint function is a sum of a convex and a concave term and
is not convex at all. The same problem is well behaved in one parametrization and
ill behaved in the other.

---

## 3. First-order conditions

Assume the terminal constraint is the only active one (verified below) and write
the Lagrangian with multiplier `mu >= 0`:

```
Lag(t, mu) = sum_i ti + mu [ k d^p sum_i ti^(1-p) - R sum_i ti - E0 ]
```

Stationarity in `ti`:

```
1 + mu [ k d^p (1-p) ti^(-p) - R ] = 0
```

Rearranged:

```
mu k d^p (p-1) ti^(-p) = 1 - mu R
```

The right-hand side does not depend on `i`. Neither do `mu`, `k`, `d` or `p`.
Therefore `ti^(-p)` is the same for every `i`, and since `p > 0` and `ti > 0`:

```
t1 = t2 = t3 = t4
```

> ### Result 1
>
> **Under a static energy budget with a velocity-only cost function, perfectly
> even pacing is the unique global optimum of the 200 freestyle, for every
> exponent `p > 1` and every choice of `k`, `R` and `E0`.**

Even pacing is not an assumption in this model. It is a theorem. The optimal
velocity `v*` solves the one-dimensional budget equation

```
k L v^(p-1) = E0 + R L / v
```

whose left side increases in `v` and whose right side decreases in `v`, so the
root is unique. `model.even_pace_velocity` finds it with `brentq`.

### 3.1 Checking the assumptions

**The terminal constraint is active.** If it were slack, `mu = 0`, and
stationarity reduces to `1 = 0`. Contradiction. Physically: leftover reserve at
the touch is unused fuel that could have bought speed.

**`mu R < 1`.** Otherwise the left side of the stationarity equation is
non-positive while the right side is positive. `1/mu` has units of watts and is
the marginal energetic value of a second; the condition says the aerobic ceiling
does not on its own cover the cost of racing, which is what makes a 200 a 200.

**Intermediate constraints are slack.** At even pacing the reserve declines
monotonically, so if `E4 >= 0` then `Ej >= 0` for `j < 4`. This holds for the
default parameters, but it is *not* automatic once oxygen kinetics are added.
See section 5.

**Bounds are slack.** `v* = 1.83 m/s` sits well below `vmax = 2.10`. For a 100
free the bound would bind and the structure of the answer would change.

---

## 4. Why this result is useful rather than disappointing

The model produces even pacing. Real 200 freestyles are positively split, by a
lot. A first reading is that the model failed.

The better reading is that the model has told us something specific: **no amount
of adjusting the engine or the hull will explain a positive split.** Any
parameter that enters only through `k`, `R` or `E0` cancels out of the
stationarity condition. So the real explanation must lie in one of:

1. the dive start and the underwaters, which are not physiological at all
2. a cost function whose shape changes over the course of the race
3. a constraint that binds part way through
4. something outside the model entirely, such as race tactics

That is a much sharper research question than "what is the optimal pacing
strategy", and it is what Phases 4 and 5 go after.

---

## 5. Extension: position-dependent economy

Suppose the cost of a given velocity rises as the race goes on, independently of
how hard the swimmer has been going:

```
C(v, x) = k v^p (1 + beta_x * x / L)
```

Integrating over segment `i`, whose midpoint is `xbar_i`:

```
Ei = integral of k v^(p-1) (1 + beta_x x/L) dx
   = k d vi^(p-1) [ 1 + beta_x xbar_i / L ]
   = k d wi vi^(p-1),        wi = 1 + beta_x xbar_i / L
```

The midpoint form is **exact**, not a quadrature approximation, because the
multiplier is linear in `x`.

Redoing section 3 with weights:

```
1 + mu [ k d^p wi (1-p) ti^(-p) - R ] = 0
=>  wi ti^(-p) = constant
=>  ti proportional to wi^(1/p)
```

> ### Result 2
>
> **The optimal split distribution is `Pi ∝ wi^(1/p)`, normalized. It depends
> only on the economy-decay profile and the cost exponent. It does not depend on
> `k`, `R`, `E0`, or any hydrodynamic parameter.**

Those parameters set how fast the race is swum. They have no influence at all on
how it is divided. With `beta_x = 0` all weights are 1 and Result 1 is recovered.

Since `wi` increases with `i`, the optimal splits get slower: a **positive
split**, which is what real races look like.

To get the absolute times, write `ti = c wi^(1/p)` and let `W = sum_i wi^(1/p)`.
The budget condition becomes one equation in `c`:

```
k d^p c^(1-p) W = E0 + AerobicSupply(c W)
```

monotone in `c`, solved by `brentq` in `model.optimal_solution_closed_form`.

---

## 6. The path constraint is not always slack

Section 3 assumed only the terminal constraint binds. With realistic oxygen
kinetics (see `03_ode_model.md`) the aerobic supply arrives late, and for slow
enough kinetics the reserve dips below zero in the middle of the race even though
it lands exactly on zero at the touch.

**At the current calibration this never happens.** The constraint is slack for
every `tau` tested up to 200 s. An earlier version of this document reported a
binding boundary near `tau = 40 s`; that was an artifact of an undersized `E0`
(35 kJ, corrected to 50.32 kJ during the drag-parameter fix), and it is now
retracted. See `docs/RESULTS.md`.

The mechanism is still real and still implemented. Shrink the reserve enough
(`E0` = 20 kJ at `tau` = 20 s, for instance) and the terminal-constraint solution
does run the reserve negative mid-race. In that regime the closed form is only a
**lower bound** on the true race time and the constrained optimum shades the
early splits to stay solvent.

`optimal_solution_closed_form` returns a `path_feasible` flag for exactly this
reason, and the numerical solver takes over when it is `False`. Result 1 is
stated with the condition attached because the condition is a real property of
the problem, even though it happens to hold everywhere the calibrated model
lives.

---

## 7. The pacing penalty

For a strategy that is not optimal, define

```
Delta T = T_strategy - T_optimal
```

For this to measure pacing rather than effort, every strategy is first rescaled
so it finishes with exactly zero reserve. A pacing *shape* `s` is scaled by a
scalar `alpha` chosen so the budget binds; then `Delta T` is the cost of
spending the same fuel in a different order.

Because `T` is smooth and the optimum is interior, the penalty is locally
quadratic:

```
Delta T ≈ (1/2) (v - v*)^T H (v - v*)
```

Three consequences, all confirmed numerically in `tests/test_model.py`:

- **Small pacing errors are cheap.** Opening 2% off costs about 0.01 s.
- **Errors compound quadratically.** Doubling the error quadruples the cost.
  Opening 10% off costs about 0.35 s.
- **Under constant economy, going out too fast and too slow cost about the
  same.** A coach would dispute this, and it is a genuine, testable weakness of
  the constant-economy model rather than a rounding artifact.

---

## 8. Assumptions in force

Listed in full in `assumptions.md`. The ones that matter most here:

1. Velocity is constant within each 50. Real velocity oscillates within a stroke
   cycle and spikes off every wall.
2. Starts, turns and underwater phases are not modelled. Split 1 gets a constant
   time credit when comparing with real races; since it is constant, it cannot
   change the optimum.
3. Economy does not depend on velocity beyond the `k v^p` form, and the cost
   coefficient carries a calibrated course economy factor `phi` that stands in
   for the unmodelled dive, turns and underwater phases.
4. `E0` and `R` are fixed within a race and there is no reserve recovery.
5. The swimmer executes the chosen velocities exactly. No pacing noise.
6. No tactical or psychological effects. The model races a clock, not a field.
