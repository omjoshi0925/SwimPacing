"""
Core mathematics of the 200 freestyle pacing model.

This module contains the objective, the cost function, the energy accounting,
and the closed-form results that the numerical work in optimization.py is
checked against. Nothing here calls an optimizer; everything is either an
explicit formula or a one-dimensional root find with a proven bracket.

The three layers of the model
-----------------------------
Layer 1  discrete four-split, static energy budget      (Phase 3)
Layer 2  cost exponent and coefficient derived from drag (Phase 4)
Layer 3  continuous energy state with kinetics and fatigue (Phase 5, simulator.py)

Layers 1 and 2 admit closed-form answers. Layer 3 does not, which is why the
simulator exists.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .parameters import Course, Swimmer, SCY_200, REFERENCE


# ---------------------------------------------------------------------------
# Hydrodynamics  (Phase 4)
# ---------------------------------------------------------------------------


def drag_force(v, sw: Swimmer = REFERENCE):
    """
    Active drag force, newtons.

        F_D = 1/2 rho C_D A v^2

    The quadratic form assumes fully developed turbulent flow with a drag
    coefficient that does not vary over the narrow velocity range raced in a
    200 free (roughly 1.6 to 2.0 m/s).

    The defaults give K_d = 1/2 rho C_D A = 34.4 N s^2/m^2, from separately
    measured C_D and active frontal area (Zamparo et al. 2009). For comparison,
    directly measured lumped coefficients are 38 kg/m for elite male sprinters
    (Cortesi et al. 2024) and 22-30 for top swimmers (Toussaint 2002), so the
    default sits inside the measured spread rather than being fitted.

    Berger et al. (1999, reported in Toussaint 2002) measured a drag-force
    exponent of 2.22 rather than 2.00, which would imply p = 3.22 rather than 3.
    The sweep in sensitivity.py covers that.
    """
    v = np.asarray(v, dtype=float)
    return sw.drag_factor * v**2


def economy_penalty(sw: Swimmer = REFERENCE, depleted=0.0, progress=0.0):
    """
    Multiplier applied to the metabolic cost of a given velocity.

        1 + beta_E * D + beta_x * (x / L)

    D is the spent fraction of the anaerobic reserve and x/L is the fraction of
    the race completed. The two terms are deliberately kept separate: they are
    different physical claims about what causes stroke economy to decay, and
    they push the optimal pacing shape in opposite directions.
    """
    depleted = np.clip(depleted, 0.0, 1.0)
    progress = np.clip(progress, 0.0, 1.0)
    return 1.0 + sw.beta_E * depleted + sw.beta_x * progress


def metabolic_rate(v, sw: Swimmer = REFERENCE, depleted=0.0, progress=0.0):
    """
    Metabolic cost rate C(v), watts.

        C(v) = k v^p,   k = (1/2 rho C_D A) / (eta_p eta_g),   p = 3

    The exponent is derived, not assumed: power against a quadratic drag law
    scales with the cube of velocity. The coefficient absorbs two efficiencies,
    propelling efficiency and gross mechanical efficiency.

    With both fatigue coefficients at zero this is the constant-economy cost
    used throughout Phases 3 and 4.
    """
    v = np.asarray(v, dtype=float)
    return sw.k * v**sw.p * economy_penalty(sw, depleted, progress)


# ---------------------------------------------------------------------------
# Aerobic supply
# ---------------------------------------------------------------------------


def aerobic_rate(t, sw: Swimmer = REFERENCE):
    """
    Instantaneous aerobic supply rate, watts.

        R(t) = R (1 - e^{-t/tau}),   tau > 0
        R(t) = R,                    tau = 0

    Oxygen uptake does not reach its ceiling instantly. The default in the
    model registry is tau = 16.5 s, the measured primary-component time
    constant at severe intensity in well-trained male swimmers (Pessoa Filho
    et al. 2012). Swimming-specific measurements span 9.6-17.8 s, and elite
    adults at actual 200 m race pace measure 10.5 s (Sousa et al. 2011).
    """
    t = np.asarray(t, dtype=float)
    if sw.tau <= 0.0:
        return np.full_like(t, sw.R, dtype=float)
    return sw.R * (1.0 - np.exp(-t / sw.tau))


def aerobic_supply(T, sw: Swimmer = REFERENCE):
    """
    Total aerobic energy delivered over a race of duration T, joules.

        tau = 0:  R T
        tau > 0:  R [ T - tau (1 - e^{-T/tau}) ]

    This is the key structural fact behind Result 3 in the write-up: the
    aerobic contribution depends on the race duration alone and not on how
    velocity is distributed within the race. Two profiles that finish in the
    same time receive exactly the same aerobic energy, so the terminal budget
    cannot tell them apart and oxygen kinetics cannot, by themselves, make
    uneven pacing optimal.

    The qualifier matters. Kinetics change *when* that energy arrives, and past
    roughly tau = 40 s with the default parameters it arrives too late to keep
    the reserve non-negative through the middle of the race. At that point the
    path constraint binds and the optimum does move off even. See
    optimal_solution_closed_form.
    """
    T = np.asarray(T, dtype=float)
    if sw.tau <= 0.0:
        return sw.R * T
    return sw.R * (T - sw.tau * (1.0 - np.exp(-T / sw.tau)))


# ---------------------------------------------------------------------------
# Discrete four-split model  (Phase 3)
# ---------------------------------------------------------------------------


def split_times(v, course: Course = SCY_200):
    """t_i = d / v_i, seconds."""
    v = np.asarray(v, dtype=float)
    return course.split_distance_m / v


def race_time(v, course: Course = SCY_200) -> float:
    """
    Objective function.

        T(v) = sum_i d / v_i

    This is the quantity the whole project minimizes.
    """
    return float(np.sum(split_times(v, course)))


def split_weights(sw: Swimmer = REFERENCE, course: Course = SCY_200):
    """
    Per-split cost multiplier from position-coupled economy decay.

        w_i = 1 + beta_x * xbar_i / L,   xbar_i = midpoint of split i

    This midpoint form is not an approximation. Over split i,

        integral of C dt = integral of k v^{p-1} (1 + beta_x x/L) dx
                         = k d v^{p-1} [ 1 + beta_x xbar_i / L ]

    because the multiplier is linear in x, so the midpoint rule is exact.
    With beta_x = 0 every weight is 1 and the static model is recovered.
    """
    n = course.n_splits
    d = course.split_distance_m
    L = course.total_distance_m
    x_mid = (np.arange(n) + 0.5) * d
    return 1.0 + sw.beta_x * x_mid / L


def split_energy_demand(v, course: Course = SCY_200, sw: Swimmer = REFERENCE):
    """
    Energy spent on each split, joules.

        C(v_i) t_i = k v_i^p (d / v_i) w_i = k d w_i v_i^{p-1}

    Note the exponent drops by one. Cost per unit *distance* scales with
    v^{p-1}, not v^p. With p = 3 the cost of a split is quadratic in its
    velocity, which is the source of the convexity that drives the result.

    Valid whenever economy does not depend on the reserve (beta_E = 0). The
    reserve-coupled mechanism makes the cost path dependent and needs the ODE.
    """
    v = np.asarray(v, dtype=float)
    w = split_weights(sw, course)
    return sw.k * course.split_distance_m * w * v ** (sw.p - 1.0)


def energy_trace(v, course: Course = SCY_200, sw: Swimmer = REFERENCE) -> dict:
    """
    Energy bookkeeping at each split boundary for the static-budget model.

    Returns cumulative time, demand, aerobic supply, and the remaining
    reserve E_j after each split. E_0 = E0 is prepended, so the arrays have
    length n_splits + 1.
    """
    v = np.asarray(v, dtype=float)
    t = split_times(v, course)
    cum_t = np.concatenate([[0.0], np.cumsum(t)])

    demand = split_energy_demand(v, course, sw)
    cum_demand = np.concatenate([[0.0], np.cumsum(demand)])

    # aerobic_supply is evaluated on cumulative time so that the kinetics term
    # is handled correctly; with tau = 0 it reduces to R * cum_t.
    cum_supply = aerobic_supply(cum_t, sw)

    E = sw.E0 + cum_supply - cum_demand
    return {
        "cum_time": cum_t,
        "split_time": t,
        "demand": demand,
        "cum_demand": cum_demand,
        "cum_supply": cum_supply,
        "energy": E,
        "race_time": float(cum_t[-1]),
        "terminal_energy": float(E[-1]),
        "min_energy": float(E.min()),
    }


def terminal_energy(v, course: Course = SCY_200, sw: Swimmer = REFERENCE) -> float:
    """
    Energy remaining at the touch, joules. The binding constraint is
    terminal_energy >= 0. At the optimum it equals zero: any leftover reserve
    is unused fuel and could have bought speed.
    """
    return energy_trace(v, course, sw)["terminal_energy"]


# ---------------------------------------------------------------------------
# Closed-form results
# ---------------------------------------------------------------------------


def _closed_form_ok(sw: Swimmer) -> bool:
    """
    The closed forms below need economy to be independent of the reserve and
    the velocity ceiling to be flat. beta_x is fine: it makes the cost of a
    split depend on where the split sits in the race, which is a fixed weight,
    not a path-dependent state.
    """
    return sw.beta_E == 0.0 and sw.gamma == 0.0


def even_pace_velocity(sw: Swimmer = REFERENCE, course: Course = SCY_200) -> float:
    """
    The single velocity v that exhausts the reserve exactly, solving

        k d (sum_i w_i) v^{p-1} = E0 + AerobicSupply(L / v)

    where L is the total race distance. The left side is strictly increasing
    in v and the right side strictly decreasing, so the root is unique and
    brentq is guaranteed to find it.

    Requires beta_E = gamma = 0; the reserve-coupled mechanism is path
    dependent and needs the simulator.
    """
    if not _closed_form_ok(sw):
        raise ValueError(
            "closed form requires beta_E = 0 and gamma = 0; "
            "use simulator.solve_even_pace"
        )

    L = course.total_distance_m
    Lw = course.split_distance_m * float(np.sum(split_weights(sw, course)))

    def gap(v: float) -> float:
        return sw.k * Lw * v ** (sw.p - 1.0) - sw.E0 - aerobic_supply(L / v, sw)

    lo, hi = 0.20, 6.00
    return float(brentq(gap, lo, hi, xtol=1e-12, rtol=1e-14))


def optimal_solution_closed_form(sw: Swimmer = REFERENCE,
                                 course: Course = SCY_200) -> dict:
    """
    Exact optimum of the weighted static-budget problem.

    Stationarity (see docs/01_derivation.md) gives

        w_i t_i^{-p} = constant   =>   t_i proportional to w_i^{1/p}

    so the whole optimal *shape* is fixed by the weights alone and does not
    depend on k, R, E0 or the drag parameters. Those set the overall speed and
    therefore the race time, but not how the race is divided.

    Writing t_i = c w_i^{1/p} and W = sum_i w_i^{1/p}, the budget condition

        k d^p c^{1-p} W = E0 + AerobicSupply(c W)

    is monotone in c and solved by brentq.

    With beta_x = 0 all weights are 1, every t_i is equal, and this reduces to
    perfectly even pacing: the central Phase 3 result.

    IMPORTANT CAVEAT. This solves the problem with only the TERMINAL energy
    constraint. The full problem also requires E(x) >= 0 at every point in the
    race, and that path constraint is not always slack. With slow oxygen
    kinetics the aerobic supply arrives too late to cover the middle of the
    race, the reserve dips below zero around the 150, and the true constrained
    optimum is no longer even. The returned dict carries `path_feasible`; when
    it is False this solution is a lower bound on the race time, not the
    answer, and the numerical solver in optimization.py should be used instead.

    With the default parameters the path constraint stays slack for tau up to
    roughly 40 s and binds beyond that.
    """
    if not _closed_form_ok(sw):
        raise ValueError("closed form requires beta_E = 0 and gamma = 0")

    d, p, k, E0 = course.split_distance_m, sw.p, sw.k, sw.E0
    w = split_weights(sw, course)
    shape = w ** (1.0 / p)
    W = float(np.sum(shape))

    def gap(c: float) -> float:
        return k * d**p * c ** (1.0 - p) * W - E0 - aerobic_supply(c * W, sw)

    c = float(brentq(gap, 1e-3, 1e3, xtol=1e-13, rtol=1e-14))
    t = c * shape
    v = d / t
    trace = energy_trace(v, course, sw)
    tol = 1e-9 * sw.E0
    return {
        "method": "closed_form",
        "velocities": v,
        "split_times": t,
        "split_fractions": t / t.sum(),
        "race_time": float(t.sum()),
        "terminal_energy": trace["terminal_energy"],
        "min_energy": trace["min_energy"],
        "energy": trace["energy"],
        "weights": w,
        "path_feasible": bool(trace["energy"].min() >= -tol),
    }


def even_pace_solution(sw: Swimmer = REFERENCE, course: Course = SCY_200) -> dict:
    """
    Full description of the closed-form even-pacing solution.

    No internal callers, kept on purpose (roadmap row 105): the named entry
    point a reader tries first for this project's central result. Composes
    even_pace_velocity and energy_trace, both pinned by the test suite.
    """
    v = even_pace_velocity(sw, course)
    vv = np.full(course.n_splits, v)
    tr = energy_trace(vv, course, sw)
    return {
        "velocities": vv,
        "split_times": tr["split_time"],
        "race_time": tr["race_time"],
        "energy": tr["energy"],
        "terminal_energy": tr["terminal_energy"],
        "split_fractions": tr["split_time"] / tr["race_time"],
    }


def scale_shape_to_budget(shape, sw: Swimmer = REFERENCE, course: Course = SCY_200) -> float:
    """
    Given a pacing *shape* s (relative velocities, any positive scale), find the
    scalar alpha such that v = alpha s exhausts the energy reserve exactly.

    This is what makes strategy comparison fair. Two pacing strategies can only
    be compared meaningfully if they spend the same energy; otherwise a
    "better" strategy is just a swimmer who tried harder. Scaling every shape
    to terminal_energy = 0 puts them all on the same fuel budget, and the
    resulting differences in T are pure pacing effects.

    Solves   k L_eff(alpha) = E0 + AerobicSupply(T(alpha))   in one variable.
    """
    if not _closed_form_ok(sw):
        raise ValueError(
            "closed form requires beta_E = 0 and gamma = 0; use simulator.scale_shape"
        )

    s = np.asarray(shape, dtype=float)
    d = course.split_distance_m
    w = split_weights(sw, course)

    def gap(a: float) -> float:
        v = a * s
        demand = np.sum(sw.k * d * w * v ** (sw.p - 1.0))
        T = np.sum(d / v)
        return demand - sw.E0 - aerobic_supply(T, sw)

    return float(brentq(gap, 0.05, 10.0, xtol=1e-13, rtol=1e-14))


def kkt_stationarity_residual(v, sw: Swimmer = REFERENCE, course: Course = SCY_200):
    """
    Residual of the first-order conditions, used as a numerical proof that the
    optimizer landed on the analytic solution.

    Working in split times t_i (see docs/01_derivation.md) the problem is

        minimize   sum t_i
        subject to k d^p sum w_i t_i^{1-p} - R sum t_i - E0 <= 0

    which is a linear objective over a convex feasible set. Stationarity gives

        1 + mu [ k d^p w_i (1-p) t_i^{-p} - R ] = 0     for every i

    so the bracketed quantity must be identical across splits. The returned
    residual is the spread of the implied multiplier; it is zero exactly at the
    optimum, which for equal weights means equal splits.

    Only valid for tau = 0, beta_E = 0 and gamma = 0.
    """
    v = np.asarray(v, dtype=float)
    d = course.split_distance_m
    t = d / v
    w = split_weights(sw, course)
    grad_c = sw.k * d**sw.p * w * (1.0 - sw.p) * t ** (-sw.p) - sw.R
    mu = -1.0 / grad_c
    return float(np.max(mu) - np.min(mu))


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def calibrate(target_time: float, sw: Swimmer = REFERENCE, course: Course = SCY_200,
              knob: str = "E0", bracket=None) -> Swimmer:
    """
    Return a copy of `sw` whose optimal race time equals `target_time`.

    Only one parameter is moved, named by `knob`. E0, R and phi are all monotone
    in the right direction (more reserve, more aerobic power, or a cheaper
    course all mean a faster optimum), so a bracketed root find is safe.

    This is the mechanism Phase 13 personalization is built on: hold the
    hydrodynamic block fixed, and let the physiological block absorb what makes
    one swimmer faster than another.
    """
    if not _closed_form_ok(sw):
        raise ValueError("calibrate requires beta_E = 0 and gamma = 0")
    if knob not in ("E0", "R", "phi"):
        raise ValueError("knob must be 'E0', 'R' or 'phi'")

    default = {"E0": (1.0e0, 1.0e7), "R": (1.0e0, 1.0e5), "phi": (1.0e-3, 1.0e2)}
    lo, hi = bracket if bracket is not None else default[knob]

    def gap(value: float) -> float:
        trial = sw.with_(**{knob: float(value)})
        return optimal_solution_closed_form(trial, course)["race_time"] - target_time

    # Neither knob spans every target time. Driving E0 to zero does not make a
    # swimmer arbitrarily slow: they converge on their purely aerobic pace,
    # v = (R / (k w))^{1/p}, and cannot be slower than that however small the
    # reserve. A swimmer whose aerobic pace already beats the target is not
    # calibratable on E0 at all. Check the bracket and say so, rather than
    # letting brentq raise a sign error that says nothing useful.
    g_lo, g_hi = gap(lo), gap(hi)
    if g_lo * g_hi > 0:
        T_lo = g_lo + target_time
        T_hi = g_hi + target_time
        raise ValueError(
            f"cannot hit {target_time:.2f} s for {sw.label!r} by moving {knob}: "
            f"reachable race times span {min(T_lo, T_hi):.2f} to {max(T_lo, T_hi):.2f} s "
            f"over {knob} in [{lo:g}, {hi:g}]. Try the other knob or a slower target."
        )

    root = float(brentq(gap, lo, hi, xtol=1e-9, rtol=1e-13))
    return sw.with_(**{knob: root})


def split_fractions(v, course: Course = SCY_200):
    """P_i = t_i / T, the normalized pacing profile used for validation."""
    t = split_times(v, course)
    return t / t.sum()


def raced_to_recorded(t_splits, course: Course = SCY_200):
    """
    Model free-swimming splits -> recorded-split space.

    The dive start makes a recorded lap 1 FASTER than swimming that lap at
    race pace, so mapping model output into recorded space credits the dive:
    lap 1 loses `course.start_credit_s`. A constant time credit cannot change
    which velocity profile is optimal; these transforms exist only so model
    output and real split sheets can be laid side by side in ONE space.
    """
    return apply_start_offset(t_splits, course.start_credit_s)


def recorded_to_raced(s_splits, course: Course = SCY_200):
    """
    Recorded splits -> free-swimming-equivalent space.

    Inverse of `raced_to_recorded`: removing the dive from a recorded race
    means lap 1 would have taken LONGER swum at pace, so lap 1 gains
    `course.start_credit_s`. Exact round-trip with `raced_to_recorded`.
    """
    out = np.array(s_splits, dtype=float).copy()
    out[0] += course.start_credit_s
    return out


def apply_start_offset(t_splits, offset: float):
    """
    Raced -> recorded with an explicit offset (legacy entry point).

    Prefer `raced_to_recorded` / `recorded_to_raced`, which take the credit
    from the course and name their direction.
    """
    out = np.array(t_splits, dtype=float).copy()
    out[0] -= offset
    return out


def format_time(seconds: float) -> str:
    """Seconds as m:ss.xx, the way a split sheet reads."""
    m = int(seconds // 60)
    s = seconds - 60 * m
    return f"{m}:{s:05.2f}" if m else f"{s:.2f}"
