"""
Constrained optimization of the four split velocities (Phase 7).

Two solvers live here.

optimize_static
    The Phase 3 / Phase 4 problem with a static energy budget. Solved in split
    *times* rather than velocities, because in that parametrization the problem
    is convex and SLSQP is guaranteed to reach the global optimum:

        minimize    T = sum_i t_i                       (linear)
        subject to  f_j(t) <= 0 for each split boundary j
                    t_lo <= t_i <= t_hi

        f_j(t) = k d^p sum_{i<=j} t_i^{1-p}
                 - AerobicSupply( sum_{i<=j} t_i ) - E0

    Each term t^{1-p} is convex for p > 1, the aerobic supply term is concave
    in T and enters with a minus sign, so each f_j is convex and the feasible
    set is an intersection of convex sets. A linear objective over a convex set
    has no interior local minima to get trapped in.

optimize_full
    The Phase 5 problem in its path-dependent form: reserve-coupled economy
    decay (beta_E) or a fatigue-coupled velocity ceiling (gamma). Neither has a
    closed form or a convexity guarantee, so it is solved over velocities with
    the simulator in the loop and run from many starting points.

Both return the same result dictionary so downstream code does not care which
one produced it.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.optimize import minimize, NonlinearConstraint

from .parameters import Course, Swimmer, SCY_200, REFERENCE
from . import model
from . import simulator


#: Constraint violation, as a fraction of the energy reserve, that still counts
#: as a converged solve.
FEASIBILITY_TOL = 1e-7


def _acceptable(res, constraint_fn) -> bool:
    """
    Whether an SLSQP result should be kept.

    `res.success` is too strict. SLSQP frequently terminates with "Positive
    directional derivative for linesearch" at a point that satisfies every
    constraint and cannot be improved, and discarding those silently loses
    correct solutions. What matters is that the iterate is finite and feasible.
    """
    x = np.asarray(res.x, dtype=float)
    if not np.all(np.isfinite(x)) or not np.isfinite(res.fun):
        return False
    return float(np.min(constraint_fn(x))) >= -FEASIBILITY_TOL


# ---------------------------------------------------------------------------
# Static-budget optimizer
# ---------------------------------------------------------------------------


def optimize_static(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                    n_starts: int = 24, seed: int = 0) -> dict:
    """
    Solve the convex static-budget problem in split-time space.

    Returns optimal velocities, split times, race time, and diagnostics that
    let the caller confirm the solve actually converged to the analytic answer.
    """
    d = course.split_distance_m
    n = course.n_splits
    k, p, E0 = sw.k, sw.p, sw.E0
    w = model.split_weights(sw, course)   # position-coupled economy weights

    t_lo = d / sw.v_max
    t_hi = d / sw.v_min

    # The objective is O(1e2) seconds and the raw energy constraint is O(1e4)
    # joules. SLSQP is sensitive to that mismatch, so the constraint is
    # expressed as a dimensionless fraction of the reserve and both the
    # objective and constraint Jacobians are supplied analytically.
    # The objective is also normalized: SLSQP's ftol is absolute, so on a raw
    # objective of ~100 s a tolerance of 1e-12 sits at machine epsilon and the
    # solver stops early. Dividing by a reference duration makes ftol relative.
    T_scale = float(n * 0.5 * (t_lo + t_hi))

    def objective(t):
        return float(np.sum(t)) / T_scale

    def objective_grad(t):
        return np.ones_like(t) / T_scale

    def constraints(t):
        """Remaining energy at each split boundary, as a fraction of E0."""
        t = np.asarray(t, dtype=float)
        cum_t = np.cumsum(t)
        cum_demand = np.cumsum(k * d**p * w * t ** (1.0 - p))
        return (E0 + model.aerobic_supply(cum_t, sw) - cum_demand) / E0

    def constraints_jac(t):
        t = np.asarray(t, dtype=float)
        cum_t = np.cumsum(t)
        if sw.tau <= 0.0:
            dS = np.full(n, sw.R)
        else:
            dS = sw.R * (1.0 - np.exp(-cum_t / sw.tau))
        dD = k * d**p * w * (p - 1.0) * t ** (-p)      # magnitude, positive
        lower = np.tril(np.ones((n, n)))                 # lower[j, i] = 1 iff i <= j
        return (lower * (dS[:, None] + dD[None, :])) / E0

    nlc = NonlinearConstraint(constraints, 0.0, np.inf, jac=constraints_jac)

    # Seed the search with the closed-form point. It is the answer whenever the
    # energy path constraint is slack, and a good warm start when it is not.
    closed = model.optimal_solution_closed_form(sw, course) if model._closed_form_ok(sw) else None

    rng = np.random.default_rng(seed)
    best = None
    for j in range(n_starts):
        if j == 0 and closed is not None:
            t0 = np.asarray(closed["split_times"], dtype=float)
        elif j <= 1:
            t0 = np.full(n, 0.5 * (t_lo + t_hi))
        else:
            t0 = rng.uniform(t_lo, t_hi, size=n)
        res = minimize(
            objective, t0, jac=objective_grad, constraints=[nlc],
            bounds=[(t_lo, t_hi)] * n, method="SLSQP",
            options={"maxiter": 800, "ftol": 1e-12},
        )
        # SLSQP routinely returns "Positive directional derivative for
        # linesearch" at a point that is converged and feasible. Judging the
        # result by the constraint residual rather than by res.success avoids
        # throwing away correct answers.
        if _acceptable(res, constraints) and (best is None or res.fun < best.fun - 1e-14):
            best = res

    if best is None:
        raise RuntimeError("no acceptable solve from any start")

    t = np.asarray(best.x, dtype=float)
    # SLSQP stops on a tolerance; the closed form does not. When the closed-form
    # point is path-feasible and at least as fast, prefer it, so the reported
    # optimum is exact rather than converged-to-1e-4.
    if (closed is not None and closed["path_feasible"]
            and float(np.sum(closed["split_times"])) <= float(np.sum(t)) + 1e-12):
        t = np.asarray(closed["split_times"], dtype=float)
    v = d / t
    trace = model.energy_trace(v, course, sw)

    out = {
        "method": "static/SLSQP",
        "velocities": v,
        "split_times": t,
        "split_fractions": t / t.sum(),
        "race_time": float(t.sum()),
        "terminal_energy": trace["terminal_energy"],
        "min_energy": trace["min_energy"],
        "energy": trace["energy"],
        "n_starts": n_starts,
        "solver_message": best.message,
    }

    # Diagnostics: how far from perfectly even, and how far from closed form.
    out["max_split_spread_s"] = float(t.max() - t.min())
    if model._closed_form_ok(sw):
        closed = model.optimal_solution_closed_form(sw, course)
        out["closed_form_race_time"] = closed["race_time"]
        out["closed_form_velocities"] = closed["velocities"]
        out["closed_form_gap_s"] = float(abs(t.sum() - closed["race_time"]))
        out["closed_form_max_v_gap"] = float(np.max(np.abs(v - closed["velocities"])))
        out["kkt_residual"] = (model.kkt_stationarity_residual(v, sw, course)
                               if sw.tau == 0 else None)
    return out


# ---------------------------------------------------------------------------
# Full-model optimizer
# ---------------------------------------------------------------------------


def optimize_full(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                  n_starts: int = 12, seed: int = 0, n_out: int = 201) -> dict:
    """
    Solve the ODE model, including oxygen kinetics and fatigue-degraded
    economy, over the four split velocities.

    The energy path constraint is enforced on the integration grid rather than
    only at the walls, because with beta_E > 0 the reserve trajectory is no
    longer guaranteed to be monotone within a split.
    """
    n = course.n_splits

    # SLSQP evaluates the objective and the constraint at the same point, so a
    # one-entry cache roughly halves the number of ODE integrations.
    _cache: dict = {}

    def sim(v):
        key = tuple(np.round(np.asarray(v, dtype=float), 12))
        hit = _cache.get(key)
        if hit is None:
            hit = simulator.simulate(np.asarray(v, dtype=float), sw, course, n_out=n_out)
            _cache.clear()
            _cache[key] = hit
        return hit

    def objective(v):
        return sim(v)["race_time"]

    def energy_floor(v):
        # Scaled to a fraction of the reserve so the constraint and the
        # objective sit on comparable numerical scales.
        return sim(v)["min_energy"] / sw.E0

    def ceiling_floor(v):
        # M4: the attainable velocity falls as the reserve empties, so v_max is
        # a moving target rather than a fixed box bound. Scaled by v_max for the
        # same conditioning reason as above. With gamma = 0 this is slack
        # wherever the box bounds already hold.
        return sim(v)["ceiling_headroom"] / sw.v_max

    cons = [NonlinearConstraint(energy_floor, 0.0, np.inf)]
    if sw.gamma > 0.0:
        cons.append(NonlinearConstraint(ceiling_floor, 0.0, np.inf))
    bounds = [(sw.v_min, sw.v_max)] * n

    # A sensible warm start: even pacing scaled to the budget.
    v_even = float(simulator.scale_shape(np.ones(n), sw, course))

    rng = np.random.default_rng(seed)
    best, best_res = None, np.inf
    for j in range(n_starts):
        if j == 0:
            v0 = np.full(n, v_even)
        else:
            v0 = np.clip(v_even * (1.0 + rng.normal(0.0, 0.05, size=n)), sw.v_min, sw.v_max)
        res = minimize(
            objective, v0, constraints=cons, bounds=bounds, method="SLSQP",
            options={"maxiter": 300, "ftol": 1e-10, "eps": 1e-6},
        )
        feasible = (_acceptable(res, energy_floor)
                    and (sw.gamma <= 0.0 or _acceptable(res, ceiling_floor)))
        if feasible and res.fun < best_res - 1e-9:
            best, best_res = res, res.fun

    if best is None:
        raise RuntimeError("no acceptable solve from any start")

    v = np.asarray(best.x, dtype=float)
    out = sim(v)
    return {
        "method": "ODE/SLSQP",
        "velocities": v,
        "split_times": out["split_times"],
        "split_fractions": out["split_fractions"],
        "race_time": out["race_time"],
        "terminal_energy": out["terminal_energy"],
        "min_energy": out["min_energy"],
        "energy": out["wall_energy"],
        "trajectory": out,
        "n_starts": n_starts,
        "max_split_spread_s": float(out["split_times"].max() - out["split_times"].min()),
        "solver_message": best.message,
    }


def optimize(sw: Swimmer = REFERENCE, course: Course = SCY_200, **kw) -> dict:
    """Dispatch to the cheaper solver when the model admits it."""
    if model._closed_form_ok(sw):
        return optimize_static(sw, course, **{k: v for k, v in kw.items()
                                              if k in ("n_starts", "seed")})
    return optimize_full(sw, course, **kw)


# ---------------------------------------------------------------------------
# Strategy comparison and pacing penalty
# ---------------------------------------------------------------------------


def compare_strategies(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                       strategies: Sequence[str] | None = None) -> "list[dict]":
    """
    Run every named strategy at matched energy budget and tabulate the pacing
    penalty against the optimum:

        Delta T = T_strategy - T_optimal

    Because every strategy is scaled to finish with exactly zero reserve, the
    penalty is not the cost of trying less hard. It is the cost of spending the
    same fuel in the wrong order.
    """
    names = list(strategies) if strategies is not None else list(simulator.STRATEGY_SHAPES)
    opt = optimize(sw, course)
    T_opt = opt["race_time"]

    rows = []
    rows.append({
        "strategy": "OPTIMAL",
        "v": np.asarray(opt["velocities"]),
        "splits": np.asarray(opt["split_times"]),
        "fractions": np.asarray(opt["split_fractions"]),
        "race_time": T_opt,
        "penalty_s": 0.0,
        "terminal_energy": opt["terminal_energy"],
    })
    for name in names:
        r = simulator.run_strategy(name, sw, course)
        rows.append({
            "strategy": name,
            "v": np.asarray(r["v_splits"]),
            "splits": np.asarray(r["split_times"]),
            "fractions": np.asarray(r["split_fractions"]),
            "race_time": r["race_time"],
            "penalty_s": r["race_time"] - T_opt,
            "terminal_energy": r["terminal_energy"],
        })
    return rows


def opening_penalty_curve(overspeeds, sw: Swimmer = REFERENCE,
                          course: Course = SCY_200) -> dict:
    """
    Time cost of opening the race at a chosen percentage above or below the
    optimal first-50 velocity.

    For each overspeed the first split is fixed and the remaining three splits
    are re-optimized, so the curve answers the right question: given that you
    have already gone out at this speed, and you will race the rest of it as
    well as possible, how much did the opening cost you?
    """
    opt = optimize(sw, course)
    T_opt = opt["race_time"]
    v_opt = float(np.asarray(opt["velocities"])[0])

    d = course.split_distance_m
    n = course.n_splits
    k, p, E0 = sw.k, sw.p, sw.E0
    w = model.split_weights(sw, course)

    out_x, out_dt, out_T = [], [], []
    for f in np.asarray(overspeeds, dtype=float):
        v1 = v_opt * (1.0 + f)
        if not (sw.v_min <= v1 <= sw.v_max):
            continue
        t1 = d / v1

        def objective(t_rest):
            return float(t1 + np.sum(t_rest)) / (n * d / v_opt)

        def constraints(t_rest):
            t = np.concatenate([[t1], t_rest])
            cum_t = np.cumsum(t)
            cum_demand = np.cumsum(k * d**p * w * t ** (1.0 - p))
            return (E0 + model.aerobic_supply(cum_t, sw) - cum_demand) / E0

        nlc = NonlinearConstraint(constraints, 0.0, np.inf)
        t_lo, t_hi = d / sw.v_max, d / sw.v_min
        res = minimize(
            objective, np.full(n - 1, d / v_opt), constraints=[nlc],
            bounds=[(t_lo, t_hi)] * (n - 1), method="SLSQP",
            options={"maxiter": 600, "ftol": 1e-13},
        )
        if not _acceptable(res, constraints):
            continue
        T = float(t1 + np.sum(res.x))
        out_x.append(f)
        out_T.append(T)
        out_dt.append(T - T_opt)

    return {
        "overspeed": np.array(out_x),
        "race_time": np.array(out_T),
        "penalty_s": np.array(out_dt),
        "T_optimal": T_opt,
        "v_optimal_first": v_opt,
    }
