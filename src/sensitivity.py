"""
Sensitivity and robustness analysis (Phase 8).

The question this module answers is narrower than "what happens when I change a
parameter". Almost every parameter changes the optimal race time; that is not
interesting. The interesting question is which parameters change the optimal
*shape*, that is the split fractions P_i = t_i / T.

The analytic result in model.optimal_solution_closed_form already tells us the
answer for the constant-economy model: the optimal shape depends on the weights
w_i alone. Since w_i = 1 + beta_x x_i / L, the only parameter that can move the
shape is beta_x. Everything else - k, R, E0, rho, C_D, A, p, tau - moves the
race time and leaves the shape at exactly even.

One caveat, and it is a real one. That statement holds while the energy path
constraint E(x) >= 0 is slack. It is slack over the whole parameter range swept
here, but not everywhere: push tau past about 40 s and the reserve dips negative
near the 150, the constraint binds, and the true optimum shades the third 50 and
finishes faster. So "only beta_x bends the shape" is a statement about the
interior of the feasible region, not an unconditional one.

The sweeps here exist to confirm that numerically, to quantify how much time
each parameter is worth, and to map the one axis that does bend the shape.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .parameters import Course, Swimmer, SCY_200, REFERENCE, WORKING
from . import model
from . import optimization
from . import simulator


# ---------------------------------------------------------------------------
# One-at-a-time sweeps
# ---------------------------------------------------------------------------

#: Parameters swept in the headline sensitivity table, with the multiplicative
#: range applied to the baseline value.
SWEEP_SPEC = {
    "E0": (0.60, 1.60),
    "R": (0.80, 1.20),
    "Cd": (0.75, 1.25),
    "A": (0.85, 1.15),
    "rho": (0.99, 1.01),
    "eta_p": (0.85, 1.15),
    "eta_g": (0.85, 1.15),
    "tau": (0.00, 2.00),
    "beta_x": (0.00, 2.00),
}


def sweep_parameter(name: str, values: Sequence[float], sw: Swimmer = REFERENCE,
                    course: Course = SCY_200) -> pd.DataFrame:
    """
    Re-optimize across a range of values for one parameter.

    Returns a tidy frame with the optimal race time, the four optimal split
    fractions, and two shape summaries:

        P1              first-50 fraction, the headline pacing number
        shape_spread    P_max - P_min, zero for perfectly even pacing
    """
    rows = []
    for val in values:
        trial = sw.with_(**{name: float(val)})
        try:
            opt = optimization.optimize(trial, course)
        except Exception as exc:  # pragma: no cover - diagnostic path
            rows.append({"parameter": name, "value": float(val), "error": str(exc)})
            continue
        P = np.asarray(opt["split_fractions"], dtype=float)
        rows.append({
            "parameter": name,
            "value": float(val),
            "race_time": opt["race_time"],
            "P1": P[0], "P2": P[1], "P3": P[2], "P4": P[3],
            "first_half_frac": P[0] + P[1],
            "shape_spread": float(P.max() - P.min()),
            "v1": float(np.asarray(opt["velocities"])[0]),
            "k": trial.k,
        })
    return pd.DataFrame(rows)


def sweep_all(sw: Swimmer = REFERENCE, course: Course = SCY_200,
              n: int = 21, spec: dict | None = None) -> pd.DataFrame:
    """Run every sweep in SWEEP_SPEC and stack the results."""
    spec = spec if spec is not None else SWEEP_SPEC
    frames = []
    for name, (lo_mult, hi_mult) in spec.items():
        base = getattr(sw, name)
        if base == 0.0:
            # tau and beta_x are zero in REFERENCE; sweep an absolute range.
            absolute = {"tau": (0.0, 40.0), "beta_x": (0.0, 0.60)}
            lo, hi = absolute.get(name, (0.0, 1.0))
        else:
            lo, hi = base * lo_mult, base * hi_mult
        vals = np.linspace(lo, hi, n)
        f = sweep_parameter(name, vals, sw, course)
        f["baseline"] = base
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


#: Excluded from the elasticity figure. Water density enters the model only
#: through the product rho*Cd*A, so its elasticity is identical to Cd's by
#: construction, but a +/-10% swing in rho is physically impossible: pool water
#: spans well under 1% across any legal competition temperature. Showing it
#: beside Cd would imply the two are equally worth worrying about. It is still
#: swept over its realistic 0.99-1.01 band in sweep_all.
ELASTICITY_EXCLUDE = ("rho",)


def elasticity_table(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                     rel: float = 0.10, exclude: Sequence[str] = ELASTICITY_EXCLUDE
                     ) -> pd.DataFrame:
    """
    Local sensitivity of race time and pacing shape to a +/- `rel` change in
    each parameter, reported as seconds and as an elasticity

        e = (dT / T) / (dtheta / theta)

    An elasticity of -0.5 means a 10% increase in that parameter buys a 5%
    faster race. Sorting by |e| ranks what actually matters, which is what a
    reader wants from a sensitivity section.
    """
    base_opt = optimization.optimize(sw, course)
    T0 = base_opt["race_time"]
    P0 = np.asarray(base_opt["split_fractions"], dtype=float)

    rows = []
    for name in SWEEP_SPEC:
        if name in exclude:
            continue
        base = getattr(sw, name)
        if base == 0.0:
            # No baseline to scale, so perturb by an absolute step from zero.
            # An elasticity is undefined here and is reported as NaN rather than
            # as a number that would invite comparison with the scaled rows.
            step = {"tau": 2.0, "beta_x": 0.05}.get(name, 0.05)
            lo_v, hi_v = 0.0, step
            denom = None
            how = f"0 -> {step:g} (absolute step)"
        else:
            lo_v, hi_v = base * (1 - rel), base * (1 + rel)
            denom = 2 * rel
            how = f"±{rel:.0%} of {base:g}"

        try:
            lo = optimization.optimize(sw.with_(**{name: lo_v}), course)
            hi = optimization.optimize(sw.with_(**{name: hi_v}), course)
        except Exception:  # pragma: no cover
            continue

        dT = hi["race_time"] - lo["race_time"]
        dP1 = float(np.asarray(hi["split_fractions"])[0]
                    - np.asarray(lo["split_fractions"])[0])
        rows.append({
            "parameter": name,
            "baseline": base,
            "perturbation": how,
            "low": lo_v,
            "high": hi_v,
            "T_low": lo["race_time"],
            "T_high": hi["race_time"],
            "dT_s": dT,
            "elasticity_T": (dT / T0) / denom if denom else np.nan,
            "dP1": dP1,
            "moves_shape": abs(dP1) > 1e-6,
        })
    out = pd.DataFrame(rows)
    out["abs_dT_s"] = out["dT_s"].abs()
    return out.sort_values("abs_dT_s", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Two-parameter maps
# ---------------------------------------------------------------------------


def aerobic_anaerobic_map(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                          r_mult=(0.80, 1.20), e_mult=(0.60, 1.60),
                          n: int = 21) -> dict:
    """
    Grid over the aerobic ceiling R and the anaerobic reserve E0, the two
    parameters that define a swimmer's engine.

    Answers secondary questions 4 and part of 6: does an anaerobically
    dominant swimmer want a different opening from an aerobically dominant one?
    Returns both the race-time surface and the first-50 fraction surface, so
    the two can be read against each other.
    """
    R_vals = np.linspace(sw.R * r_mult[0], sw.R * r_mult[1], n)
    E_vals = np.linspace(sw.E0 * e_mult[0], sw.E0 * e_mult[1], n)
    T = np.zeros((n, n))
    P1 = np.zeros((n, n))
    for i, E0 in enumerate(E_vals):
        for j, R in enumerate(R_vals):
            opt = optimization.optimize(sw.with_(R=float(R), E0=float(E0)), course)
            T[i, j] = opt["race_time"]
            P1[i, j] = float(np.asarray(opt["split_fractions"])[0])
    return {"R": R_vals, "E0": E_vals, "race_time": T, "P1": P1,
            "anaerobic_fraction": E_vals[:, None] / (E_vals[:, None] + R_vals[None, :] * T)}


def exponent_map(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                 p_range=(2.0, 4.5), b_range=(0.0, 0.6), n: int = 21) -> dict:
    """
    Grid over the cost exponent p and the position-fatigue coefficient beta_x.

    This is the map that matters for the shape question. p controls how sharply
    cost rises with speed and beta_x controls how much dearer late speed is.
    The closed form says P_i is proportional to w_i^{1/p} normalized, so this
    surface should be smooth and monotone in both directions: larger beta_x
    means more positive split, larger p means the swimmer is less willing to
    let the splits drift apart.
    """
    p_vals = np.linspace(*p_range, n)
    b_vals = np.linspace(*b_range, n)
    P1 = np.zeros((n, n))
    T = np.zeros((n, n))
    for i, b in enumerate(b_vals):
        for j, p in enumerate(p_vals):
            trial = sw.with_(p=float(p), beta_x=float(b))
            opt = model.optimal_solution_closed_form(trial, course)
            P1[i, j] = float(opt["split_fractions"][0])
            T[i, j] = opt["race_time"]
    return {"p": p_vals, "beta_x": b_vals, "P1": P1, "race_time": T}


# ---------------------------------------------------------------------------
# Archetype comparison (Phase 13 groundwork)
# ---------------------------------------------------------------------------


def compare_archetypes(archetypes: dict, course: Course = SCY_200,
                       match_time: float | None = None,
                       knob: str = "E0") -> pd.DataFrame:
    """
    Optimal pacing for a set of swimmer profiles.

    If `match_time` is given, each archetype is first calibrated to that same
    race time by moving one parameter. This is the fair comparison: it isolates
    "two swimmers who go the same time should pace differently" from the
    trivial "the faster swimmer goes faster".
    """
    rows = []
    for name, sw in archetypes.items():
        trial, used = sw, "none"
        if match_time:
            # E0 is the natural knob but has a limited reach: a swimmer whose
            # purely aerobic pace already beats the target cannot be slowed by
            # emptying the reserve. R spans a much wider range, so fall back to
            # it rather than dropping the archetype from the comparison.
            for candidate in (knob, "R" if knob == "E0" else "E0"):
                try:
                    trial, used = model.calibrate(match_time, sw, course,
                                                  knob=candidate), candidate
                    break
                except ValueError:
                    continue
            else:
                used = "FAILED"
        opt = optimization.optimize(trial, course)
        P = np.asarray(opt["split_fractions"], dtype=float)
        t = np.asarray(opt["split_times"], dtype=float)
        rows.append({
            "archetype": name,
            "label": trial.label,
            "calibrated_on": used,
            "R": trial.R, "E0": trial.E0, "k": trial.k,
            "beta_x": trial.beta_x, "tau": trial.tau,
            "race_time": opt["race_time"],
            "t1": t[0], "t2": t[1], "t3": t[2], "t4": t[3],
            "P1": P[0], "P2": P[1], "P3": P[2], "P4": P[3],
            "shape_spread": float(P.max() - P.min()),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Robustness of the pacing penalty
# ---------------------------------------------------------------------------


def penalty_robustness(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                       strategies: Sequence[str] | None = None,
                       n_draws: int = 200, cv: float = 0.10,
                       seed: int = 0) -> pd.DataFrame:
    """
    Monte Carlo over the parameter set: how stable is the estimated pacing
    penalty when the physiological parameters are only known to about 10%?

    Each draw perturbs R, E0, Cd, A, eta_p and eta_g lognormally with
    coefficient of variation `cv`, re-solves for the optimum, and re-scores
    every named strategy at that draw's matched energy budget. Reporting the
    interquartile range of Delta T alongside the point estimate is the honest
    way to present a penalty derived from parameters this uncertain.
    """
    rng = np.random.default_rng(seed)
    names = list(strategies) if strategies is not None else list(simulator.STRATEGY_SHAPES)
    sigma = np.sqrt(np.log(1.0 + cv**2))
    fields = ("R", "E0", "Cd", "A", "eta_p", "eta_g")

    rows = []
    for draw in range(n_draws):
        pert = {f: float(getattr(sw, f) * rng.lognormal(-0.5 * sigma**2, sigma))
                for f in fields}
        trial = sw.with_(**pert)
        try:
            T_opt = optimization.optimize(trial, course)["race_time"]
            for name in names:
                shape = np.asarray(simulator.STRATEGY_SHAPES[name], dtype=float)
                shape = shape / shape.mean()
                a = model.scale_shape_to_budget(shape, trial, course)
                T = float(np.sum(course.split_distance_m / (a * shape)))
                rows.append({"draw": draw, "strategy": name,
                             "penalty_s": T - T_opt, "T_optimal": T_opt})
        except Exception:  # pragma: no cover
            continue

    df = pd.DataFrame(rows)
    return (df.groupby("strategy")["penalty_s"]
              .agg(median="median",
                   q25=lambda s: s.quantile(0.25),
                   q75=lambda s: s.quantile(0.75),
                   lo=lambda s: s.quantile(0.05),
                   hi=lambda s: s.quantile(0.95))
              .sort_values("median")
              .reset_index())
