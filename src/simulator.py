"""
Race simulator (Phase 5 and Phase 6).

Given a pacing strategy the simulator integrates the physiological state
forward and returns distance, velocity, energy reserve and total race time.

State equations
---------------
Independent variable is distance x, which is convenient because the terminal
condition x(T) = L is then a fixed integration limit rather than an event to
detect.

    dt/dx = 1 / v(x)
    dE/dx = [ R(t) - C(v, E) ] / v(x)

with

    C(v, E, x) = k v^p (1 + beta_E * D + beta_x * x/L),   D = clip(1 - E/E0, 0, 1)
    R(t)       = R (1 - e^{-t/tau})                        (tau = 0 gives R(t) = R)

    t(0) = 0,  E(0) = E0,  x runs from 0 to L.

Feasibility requires E(x) >= 0 for all x. The simulator does not enforce this:
it integrates the strategy as written and reports the minimum reserve, so an
infeasible strategy is visible rather than silently repaired. A real swimmer
cannot run the reserve negative, they slow down instead, so a strategy with
min_energy < 0 should be read as "not physically executable" rather than as a
race that happened.

Two special cases are worth knowing, because they are how the simulator is
verified:

  * tau = 0 with constant economy reproduces the closed-form static-budget
    model in model.py to solver tolerance.
  * With constant economy, total aerobic supply is a function of race duration
    alone, so the optimal shape is unchanged from the static case no matter
    what tau is.
"""

from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from .parameters import Course, Swimmer, SCY_200, REFERENCE


# ---------------------------------------------------------------------------
# Velocity profiles
# ---------------------------------------------------------------------------


def piecewise_velocity(v_splits: Sequence[float], course: Course = SCY_200) -> Callable:
    """
    Turn four split velocities into v(x), constant within each split.

    This is the control used everywhere except the optimal-control extension.
    It matches how races are actually measured: a split sheet reports mean
    velocity over 50, not an instantaneous trace.
    """
    v = np.asarray(v_splits, dtype=float)
    d = course.split_distance_m
    n = len(v)

    def v_of_x(x: float) -> float:
        idx = int(np.clip(np.floor(x / d), 0, n - 1))
        return float(v[idx])

    return v_of_x


# ---------------------------------------------------------------------------
# Core integration
# ---------------------------------------------------------------------------


def simulate(v_profile, sw: Swimmer = REFERENCE, course: Course = SCY_200,
             n_out: int = 801, rtol: float = 1e-10, atol: float = 1e-10) -> dict:
    """
    Integrate one race.

    Parameters
    ----------
    v_profile : sequence of split velocities, or a callable v(x)
    sw        : Swimmer parameters
    course    : Course geometry
    n_out     : number of points on the returned distance grid

    Returns a dict with the full trajectory plus summary scalars.
    """
    if callable(v_profile):
        v_of_x = v_profile
        v_splits = None
    else:
        v_splits = np.asarray(v_profile, dtype=float)
        v_of_x = piecewise_velocity(v_splits, course)

    L = course.total_distance_m
    E0, R, tau, k, p = sw.E0, sw.R, sw.tau, sw.k, sw.p
    beta_E, beta_x = sw.beta_E, sw.beta_x

    def rhs(x, y):
        t, E = y
        v = v_of_x(x)
        D = min(max(1.0 - E / E0, 0.0), 1.0)
        C = k * v**p * (1.0 + beta_E * D + beta_x * min(max(x / L, 0.0), 1.0))
        Rt = R if tau <= 0.0 else R * (1.0 - np.exp(-t / tau))
        return [1.0 / v, (Rt - C) / v]

    x_eval = np.linspace(0.0, L, n_out)
    sol = solve_ivp(
        rhs, (0.0, L), [0.0, E0],
        t_eval=x_eval, rtol=rtol, atol=atol, method="LSODA", max_step=course.split_distance_m / 4,
    )
    if not sol.success:
        raise RuntimeError(f"integration failed: {sol.message}")

    x = sol.t
    t = sol.y[0]
    E = sol.y[1]
    v = np.array([v_of_x(xi) for xi in x])

    D = np.clip(1.0 - E / E0, 0.0, 1.0)
    progress = np.clip(x / L, 0.0, 1.0)
    cost_rate = k * v**p * (1.0 + beta_E * D + beta_x * progress)

    # Fatigue-coupled velocity ceiling. With gamma = 0 this is a flat v_max and
    # the headroom is simply v_max - v.
    v_ceiling = sw.v_max * (1.0 - sw.gamma * D)
    ceiling_headroom = float(np.min(v_ceiling - v))

    # split boundaries
    d = course.split_distance_m
    bounds = np.array([i * d for i in range(course.n_splits + 1)])
    t_at_wall = np.interp(bounds, x, t)
    E_at_wall = np.interp(bounds, x, E)
    splits = np.diff(t_at_wall)

    return {
        "x": x,
        "t": t,
        "v": v,
        "E": E,
        "depleted": D,
        "cost_rate": cost_rate,
        "aerobic_rate": (np.full_like(t, R) if tau <= 0.0
                         else R * (1.0 - np.exp(-t / tau))),
        "v_ceiling": v_ceiling,
        "ceiling_headroom": ceiling_headroom,
        "wall_time": t_at_wall,
        "wall_energy": E_at_wall,
        "split_times": splits,
        "split_fractions": splits / splits.sum(),
        "race_time": float(t[-1]),
        "terminal_energy": float(E[-1]),
        "min_energy": float(E.min()),
        # Tolerance scales with the reserve: an absolute joule threshold is
        # meaningless when E0 spans tens of kJ.
        "feasible": bool(E.min() >= -1e-6 * E0 and ceiling_headroom >= -1e-6),
        "v_splits": v_splits,
    }


# ---------------------------------------------------------------------------
# Budget matching
# ---------------------------------------------------------------------------


def scale_shape(shape: Sequence[float], sw: Swimmer = REFERENCE,
                course: Course = SCY_200, bracket=(0.05, 6.0)) -> float:
    """
    Scale a pacing shape so the race finishes with exactly zero reserve.

    Works for the full model including tau and beta, by root finding on the
    simulated terminal energy. This is the general version of
    model.scale_shape_to_budget.
    """
    s = np.asarray(shape, dtype=float)

    def terminal(a: float) -> float:
        return simulate(a * s, sw, course, n_out=201)["terminal_energy"]

    lo, hi = bracket
    return float(brentq(terminal, lo, hi, xtol=1e-11, rtol=1e-13))


def solve_even_pace(sw: Swimmer = REFERENCE, course: Course = SCY_200) -> dict:
    """Even pacing scaled to exhaust the reserve, using the full model."""
    a = scale_shape(np.ones(course.n_splits), sw, course)
    return simulate(np.full(course.n_splits, a), sw, course)


# ---------------------------------------------------------------------------
# Named strategies (Phase 6)
# ---------------------------------------------------------------------------

# Shapes are relative velocities. Each is normalized to mean 1 so that the
# scaling step is the only thing that sets absolute speed.
STRATEGY_SHAPES = {
    "even":                 (1.000, 1.000, 1.000, 1.000),
    "positive_split":       (1.030, 1.010, 0.990, 0.970),
    "negative_split":       (0.970, 0.990, 1.010, 1.030),
    "aggressive_opening":   (1.080, 1.000, 0.970, 0.950),
    "very_aggressive":      (1.150, 1.000, 0.950, 0.900),
    "conservative_opening": (0.940, 0.990, 1.020, 1.050),

    # OBSERVED shapes, traceable to real races. Velocity shapes are normalized
    # to mean 1, computed as 1/t from mean lap times in the free-swimming-
    # equivalent space: the dive credit (start_credit_s = 1.80 s) is ADDED
    # back to recorded lap 1 before converting, per model.recorded_to_raced.
    # (Recomputed 2026-09-01: the previous tuples subtracted the credit,
    # the same sign error fixed in preprocessing; see validation_plan log.)
    #
    # elite: Robertson, Pyne, Hopkins & Anson (2009), J Sports Sci 27(4),
    # men's 200 m free international finalists, mean recorded laps
    # 25.33/27.24/27.74/27.61 s (LCM; course differs from SCY, noted).
    "observed_elite_corrected": (1.0110, 1.0069, 0.9887, 0.9934),
    # pilot: this project's own 80 usable races (male 15-18, SCY, Orinda SC
    # Senior Open Jan 2025 official splits), mean recorded laps
    # 26.47/29.18/30.21/29.98 s. See results/validation/.
    "observed_pilot_corrected": (1.0397, 1.0071, 0.9728, 0.9804),
}


def strategy_velocities(name: str, sw: Swimmer = REFERENCE,
                        course: Course = SCY_200) -> np.ndarray:
    """Absolute split velocities for a named strategy at matched energy budget."""
    shape = np.asarray(STRATEGY_SHAPES[name], dtype=float)
    shape = shape / shape.mean()
    a = scale_shape(shape, sw, course)
    return a * shape


def run_strategy(name: str, sw: Swimmer = REFERENCE, course: Course = SCY_200) -> dict:
    """Simulate a named strategy at matched energy budget."""
    v = strategy_velocities(name, sw, course)
    out = simulate(v, sw, course)
    out["strategy"] = name
    return out
