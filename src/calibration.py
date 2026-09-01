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
