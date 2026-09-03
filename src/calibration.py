"""
Calibration of fatigue parameters against observed split proportions (Task 14).

Spaces, stated once: observed data enters in the free-swimming-equivalent
space (the `P{i}_corrected` columns: dive credit ADDED back to lap 1), and
model predictions are raced-space split fractions. One transform per
comparison, per docs/model_definitions.md.

The registered loss (docs/validation_plan.md §3) is the per-race RMSE over the
four split proportions, averaged over races, in percentage points. Because a
candidate parameter produces ONE model shape shared by every race, the
race-to-race dispersion around the observed mean does not depend on the
parameter; minimizing this loss is therefore equivalent to minimizing distance
to the mean observed shape. The code still computes the registered per-race
form directly, so what is minimized is literally what the plan registered.

Nothing in this module reads the held-out test set. Data access for fitting
goes through `training_frame` (added with the fitting CLI), which returns
train rows only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from . import model as _model
from .parameters import MODELS, SCY_200, Course

#: The observed columns the registered loss is computed on.
OBS_COLS = [f"P{i}_corrected" for i in range(1, 5)]


def observed_shares(df: pd.DataFrame) -> np.ndarray:
    """
    The free-swimming-equivalent share matrix (n x 4) from a processed frame.

    Refuses rows with missing or non-normalized shares rather than silently
    dropping or renormalizing them: by the time a frame reaches calibration,
    the pipeline's quality gates are supposed to have done that job.
    """
    P = df[OBS_COLS].to_numpy(dtype=float)
    if not np.isfinite(P).all():
        raise ValueError(
            f"{np.count_nonzero(~np.isfinite(P).all(axis=1))} rows have missing "
            "corrected shares; filter to usable rows before calibrating")
    if not np.allclose(P.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("corrected shares do not sum to 1; regenerate the "
                         "processed dataset (see DEV_WORKFLOW.md)")
    return P


def shares_at_credit(df: pd.DataFrame, start_credit_s: float) -> np.ndarray:
    """
    Free-swimming-equivalent shares recomputed at a NON-default start credit,
    directly from the recorded split times. Used by the start-credit
    sensitivity analyses; `observed_shares` is the registered default.
    """
    laps = df[[f"split{i}_time" for i in range(1, 5)]].to_numpy(dtype=float)
    if not np.isfinite(laps).all():
        raise ValueError("missing split times; filter to usable rows first")
    laps = laps.copy()
    laps[:, 0] += start_credit_s  # recorded -> free-swimming equivalent
    return laps / laps.sum(axis=1, keepdims=True)


def mean_rmse_pp(model_shape, shares: np.ndarray) -> float:
    """
    The registered loss: per-race RMSE over the four proportions against one
    raced-space model shape, averaged over races, in percentage points.

    Matches `preprocessing.add_model_deviations` (which stores the per-race
    values) by construction; the test suite pins the agreement.
    """
    star = np.asarray(model_shape, dtype=float)
    if star.shape != (4,):
        raise ValueError(f"model shape must be 4 fractions, got {star.shape}")
    per_race = np.sqrt(np.mean((shares - star[None, :]) ** 2, axis=1))
    return float(per_race.mean() * 100.0)


def mean_shape(shares: np.ndarray) -> np.ndarray:
    """Mean observed share vector, for reporting next to fitted shapes."""
    return shares.mean(axis=0)


# ---------------------------------------------------------------------------
# Fitters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FitResult:
    """One fitted fatigue parameter and the evidence around it."""

    model: str            # registry key, e.g. "M3_position_fatigue"
    param: str            # which field was fitted
    value: float          # fitted value
    loss_pp: float        # registered loss at the fitted value
    baseline_pp: float    # registered loss at the registry (pre-fit) value
    shape: tuple          # raced-space split fractions at the fitted value
    n_races: int
    n_evals: int          # objective evaluations spent
    bounds: tuple
    notes: str = ""
    extra: dict = field(default_factory=dict)

    def improved(self) -> bool:
        return self.loss_pp <= self.baseline_pp + 1e-12


class CalibrationLeakageError(RuntimeError):
    """Raised when a fitting path would see held-out test rows."""


def training_frame(processed_csv: str, seed: int | None = None):
    """
    The ONLY sanctioned data source for fitting: loads the processed dataset,
    keeps usable rows, applies the registered swimmer-grouped split, and
    returns (train_rows, meta). Test rows never leave this function.
    """
    from . import data_split

    seed = data_split.DEFAULT_SEED if seed is None else seed
    df = pd.read_csv(processed_csv, low_memory=False)
    ok = df[df["usable"] == True]  # noqa: E712
    train, test = data_split.split_by_swimmer(ok, seed=seed)
    meta = {
        "seed": seed,
        "n_train_races": int(len(train)),
        "n_train_swimmers": int(train["swimmer_id"].nunique()),
        "n_test_races_unopened": int(len(test)),
        "start_credit_s": float(train["start_offset_used"].iloc[0]),
    }
    _TEST_SWIMMERS[(processed_csv, seed)] = frozenset(test["swimmer_id"])
    return train, meta


#: test-side swimmer ids per (dataset, seed), populated by training_frame so
#: the guard can check frames without re-reading the file.
_TEST_SWIMMERS: dict = {}


def assert_no_test_rows(df: pd.DataFrame, processed_csv: str,
                        seed: int | None = None) -> None:
    """
    Structural leakage guard: raises CalibrationLeakageError if any row in
    `df` belongs to a held-out test swimmer under the registered split.
    """
    from . import data_split

    seed = data_split.DEFAULT_SEED if seed is None else seed
    key = (processed_csv, seed)
    if key not in _TEST_SWIMMERS:
        training_frame(processed_csv, seed)  # populates the registry
    bad = set(df["swimmer_id"]) & set(_TEST_SWIMMERS[key])
    if bad:
        raise CalibrationLeakageError(
            f"{len(bad)} held-out test swimmers present in a fitting frame "
            f"(seed {seed}). The registered split forbids this; fit on "
            f"training_frame(...) output only.")


def fit_report_frame(fits: list, meta: dict,
                     baselines: dict | None = None) -> pd.DataFrame:
    """
    One auditable table for a fitting run: every fitted parameter with its
    loss, the registry value it started from, the eval budget it spent, and
    the run metadata (dataset version, seed, start credit, train counts,
    exploratory flag, UTC timestamp). `baselines` adds unfitted reference
    rows (e.g. M0's loss) so the table stands alone.
    """
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for name, loss in (baselines or {}).items():
        rows.append({"model": name, "param": "", "fitted_value": np.nan,
                     "registry_value": np.nan, "train_loss_pp": round(loss, 4),
                     "registry_loss_pp": round(loss, 4), "n_evals": 0,
                     "shape": "", "bounds": "", "notes": "no free parameter"})
    for f in fits:
        rows.append({
            "model": f.model, "param": f.param,
            "fitted_value": round(f.value, 6),
            "registry_value": float(getattr(MODELS[f.model], f.param)),
            "train_loss_pp": round(f.loss_pp, 4),
            "registry_loss_pp": round(f.baseline_pp, 4),
            "n_evals": f.n_evals,
            "shape": "/".join(f"{s:.4f}" for s in f.shape),
            "bounds": f"[{f.bounds[0]:g}, {f.bounds[1]:g}]",
            "notes": f.notes,
        })
    out = pd.DataFrame(rows)
    for k, v in meta.items():
        out[k] = v
    out["generated_utc"] = stamp
    return out


def write_fit_report(path: str, fits: list, meta: dict,
                     baselines: dict | None = None) -> pd.DataFrame:
    """Write the fit-report table to CSV and return it."""
    frame = fit_report_frame(fits, meta, baselines)
    frame.to_csv(path, index=False)
    return frame


def m3_shape(beta_x: float, course: Course = SCY_200) -> np.ndarray:
    """
    Raced-space split fractions of the position-fatigue model at `beta_x`.

    Closed form (t_i proportional to w_i^(1/p)), so evaluation costs
    microseconds and the fit is exact. By the shape-invariance theorem the
    fractions depend only on `beta_x` and `p`; the registry's phi is kept
    fixed and does not enter the shape.
    """
    sw = MODELS["M3_position_fatigue"].with_(beta_x=float(beta_x))
    return np.asarray(_model.optimal_solution_closed_form(sw, course)["split_fractions"])


#: Minimum restart count for inner ODE solves during fitting. The pilot-era
#: ladder (1, 2, 5) escalated only on EXCEPTIONS, and on pilot-v0.2 the
#: single-start M4 solve was found to return non-global inner optima
#: (race time 0.1 s slower and a shape 0.35 pp off the 12-start solution at
#: the registry gamma), which corrupts the loss landscape without raising.
#: Five starts reproduce the cached 12-start registry shapes to 4 decimals.
INNER_STARTS_LADDER = (5, 12)


def _ode_shape(registry_key: str, param: str, value: float,
               course: Course, cache: dict,
               n_starts_ladder=INNER_STARTS_LADDER) -> np.ndarray:
    """
    Raced-space split fractions of an ODE model (M2/M4) with one fatigue
    parameter overridden. Solves through `optimization.optimize_full`, walking
    up a restart ladder on failure, and caching by rounded value because
    scalar minimizers revisit points. See INNER_STARTS_LADDER for why the
    ladder starts at five: an inner solve that converges to a local optimum
    is worse than one that fails, because it returns quietly.
    """
    from . import optimization  # local import; optimization pulls the solver stack

    key = (registry_key, param, round(float(value), 6))
    hit = cache.get(key)
    if hit is not None:
        return hit
    sw = MODELS[registry_key].with_(**{param: float(value)})
    last_err = None
    for n_starts in n_starts_ladder:
        try:
            sol = optimization.optimize_full(sw, course, n_starts=n_starts)
            shape = np.asarray(sol["split_fractions"], dtype=float)
            cache[key] = shape
            return shape
        except Exception as e:  # noqa: BLE001 - deliberate ladder, re-raised below
            last_err = e
    raise RuntimeError(
        f"ODE solve failed for {registry_key} {param}={value:.4f} at every "
        f"restart count {n_starts_ladder}") from last_err


def _fit_ode_param(registry_key: str, param: str, shares: np.ndarray,
                   bounds: tuple, course: Course, coarse: int,
                   refine_iters: int) -> FitResult:
    """
    Shared 1-D fitter for the ODE models: coarse grid to bracket the minimum,
    then bounded Brent refinement inside the bracketing interval. Every
    objective evaluation is an ODE optimization (seconds), so the eval budget
    is explicit: `coarse + refine_iters` solves, cached against revisits.
    """
    shares = np.asarray(shares, dtype=float)
    cache: dict = {}
    evals = {"n": 0}

    def objective(v: float) -> float:
        evals["n"] += 1
        return mean_rmse_pp(_ode_shape(registry_key, param, v, course, cache),
                            shares)

    grid = np.linspace(bounds[0], bounds[1], coarse)
    losses = np.array([objective(v) for v in grid])
    i = int(np.argmin(losses))
    lo = grid[max(i - 1, 0)]
    hi = grid[min(i + 1, coarse - 1)]
    res = minimize_scalar(objective, bounds=(lo, hi), method="bounded",
                          options={"xatol": 2e-3, "maxiter": refine_iters})
    # the refiner can stop above a grid point; keep whichever is truly best
    cand = [(float(res.fun), float(res.x)), (float(losses[i]), float(grid[i]))]
    best_loss, best_v = min(cand)
    registry_value = float(getattr(MODELS[registry_key], param))
    baseline = objective(registry_value)
    # inner-solver reliability check: at the registry value the solve must
    # reproduce the cached 12-start registry shape (parameters.py)
    from .parameters import PREDICTED_SHAPES_SCY200
    solver_note = ""
    if course is SCY_200 and registry_key in PREDICTED_SHAPES_SCY200:
        got = _ode_shape(registry_key, param, registry_value, course, cache)
        dev = float(np.abs(got - np.asarray(PREDICTED_SHAPES_SCY200[registry_key])).max() * 100)
        solver_note = f"; inner solve vs cached registry shape: max |dP| = {dev:.3f} pp"
        if dev > 0.05:
            solver_note += " (UNRELIABLE inner solve; do not use this fit)"
    return FitResult(
        model=registry_key, param=param, value=best_v, loss_pp=best_loss,
        baseline_pp=baseline,
        shape=tuple(np.round(_ode_shape(registry_key, param, best_v, course,
                                        cache), 6)),
        n_races=int(shares.shape[0]), n_evals=evals["n"], bounds=tuple(bounds),
        notes=(f"ODE inner solve (>= {INNER_STARTS_LADDER[0]} starts); "
               f"{coarse}-point grid + bounded Brent; cached" + solver_note),
    )


def fit_gamma(shares: np.ndarray, bounds: tuple = (0.02, 0.45),
              course: Course = SCY_200, coarse: int = 7,
              refine_iters: int = 10) -> FitResult:
    """
    Fit M4's velocity-ceiling coupling `gamma`. The lower bound stays off zero
    because at gamma = 0 the ceiling never binds and the shape degenerates to
    even pacing, where the parameter is unidentified.
    """
    return _fit_ode_param("M4_velocity_ceiling", "gamma", shares, bounds,
                          course, coarse, refine_iters)


def fit_beta_E(shares: np.ndarray, bounds: tuple = (0.02, 1.0),
               course: Course = SCY_200, coarse: int = 7,
               refine_iters: int = 10) -> FitResult:
    """
    Fit M2's reserve-coupling `beta_E`. Included although the pilot
    sign-contradicts M2: hiding poor models is forbidden, and a fitted-and-
    still-losing M2 is stronger evidence than an unfitted one. Expect the fit
    to press toward the lower bound on positively split data, since smaller
    `beta_E` means a weaker negative split; at `beta_E` = 0 the mechanism is
    absent and the parameter unidentified, hence the off-zero lower bound.
    """
    return _fit_ode_param("M2_reserve_fatigue", "beta_E", shares, bounds,
                          course, coarse, refine_iters)


def fit_beta_x(shares: np.ndarray, bounds: tuple = (0.0, 1.5),
               course: Course = SCY_200) -> FitResult:
    """
    Fit M3's `beta_x` to observed shares by minimizing the registered loss.

    Bounded scalar minimization over the closed-form shape. The objective is
    smooth and unimodal in `beta_x` (the shape moves monotonically from even
    toward steeper positive splits), so a bounded Brent search is enough and
    is deterministic.
    """
    shares = np.asarray(shares, dtype=float)
    evals = {"n": 0}

    def objective(b: float) -> float:
        evals["n"] += 1
        return mean_rmse_pp(m3_shape(b, course), shares)

    res = minimize_scalar(objective, bounds=bounds, method="bounded",
                          options={"xatol": 1e-6})
    b_hat = float(res.x)
    registry = float(MODELS["M3_position_fatigue"].beta_x)
    return FitResult(
        model="M3_position_fatigue", param="beta_x", value=b_hat,
        loss_pp=float(res.fun),
        baseline_pp=mean_rmse_pp(m3_shape(registry, course), shares),
        shape=tuple(np.round(m3_shape(b_hat, course), 6)),
        n_races=int(shares.shape[0]), n_evals=evals["n"], bounds=tuple(bounds),
        notes="closed-form inner solve; deterministic bounded Brent",
    )
