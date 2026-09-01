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

import numpy as np
import pandas as pd

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
