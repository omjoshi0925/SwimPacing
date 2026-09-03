"""
Statistics for the registered held-out comparison and the H1 analysis
(validation_plan §4, §8).

Everything here is deliberately plain: cluster bootstrap by swimmer for
confidence intervals (repeated races by one swimmer are not independent),
the §4 win criteria applied mechanically, and the §8 mixed-effects
regression with its pre-registered OLS fallback. No likelihood-based model
selection is offered, because the models carry no error model
(validation_plan §3).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MODEL_ORDER = ["M0", "M1", "M2", "M3", "M4"]


# ---------------------------------------------------------------------------
# per-race metrics
# ---------------------------------------------------------------------------


def race_rmse_pp(P: np.ndarray, shape: np.ndarray) -> np.ndarray:
    """Per-race RMSE (percentage points) of split proportions vs a shape."""
    P = np.asarray(P, dtype=float)
    return np.sqrt(np.mean((P - np.asarray(shape)[None, :]) ** 2, axis=1)) * 100


def race_mae_pp(P: np.ndarray, shape: np.ndarray) -> np.ndarray:
    P = np.asarray(P, dtype=float)
    return np.mean(np.abs(P - np.asarray(shape)[None, :]), axis=1) * 100


def signed_error_pp(P: np.ndarray, shape: np.ndarray) -> np.ndarray:
    """Mean per-split signed error (observed - model), pp, shape (4,)."""
    P = np.asarray(P, dtype=float)
    return (P - np.asarray(shape)[None, :]).mean(axis=0) * 100


# ---------------------------------------------------------------------------
# cluster bootstrap
# ---------------------------------------------------------------------------


def cluster_bootstrap(values: np.ndarray, clusters: np.ndarray,
                      stat=np.mean, n_boot: int = 10000, seed: int = 20260829,
                      alpha: float = 0.05) -> dict:
    """
    Percentile bootstrap CI of `stat(values)` resampling CLUSTERS (swimmers)
    with replacement. `values` may be 1-D (one statistic) or 2-D with one
    column per quantity; the same resample is applied to every column so
    that differences between columns are computed on matched draws.
    """
    values = np.asarray(values, dtype=float)
    clusters = np.asarray(clusters)
    ids, inv = np.unique(clusters, return_inverse=True)
    members = [np.flatnonzero(inv == k) for k in range(len(ids))]
    rng = np.random.default_rng(seed)
    est = stat(values, axis=0) if values.ndim == 2 else stat(values)
    draws = np.empty((n_boot,) + np.shape(est))
    for b in range(n_boot):
        pick = rng.integers(0, len(ids), len(ids))
        idx = np.concatenate([members[k] for k in pick])
        draws[b] = stat(values[idx], axis=0) if values.ndim == 2 else stat(values[idx])
    lo = np.quantile(draws, alpha / 2, axis=0)
    hi = np.quantile(draws, 1 - alpha / 2, axis=0)
    return {"estimate": est, "lo": lo, "hi": hi, "n_boot": n_boot,
            "n_clusters": int(len(ids)), "draws": draws}


# ---------------------------------------------------------------------------
# §4 win criteria
# ---------------------------------------------------------------------------


def apply_win_criteria(mean_rmse: dict, diff_ci: dict, P_mean: np.ndarray,
                       shapes: dict) -> dict:
    """
    validation_plan §4, applied mechanically.

    A model wins on SHAPE if its predicted sign of P4 - P1 matches the
    observed mean's and no other model's does. A model wins on ACCURACY if
    its held-out mean RMSE is lower than every other model's by more than
    the bootstrap 95% CI half-width of that difference: equivalently the CI
    of (other - best) excludes zero for every other model. Otherwise the
    registered conclusion is that the data do not distinguish the models.

    `diff_ci` maps model -> (lo, hi) of mean RMSE(model) - mean RMSE(best).
    """
    obs_sign = int(np.sign(np.round(P_mean[3] - P_mean[0], 6)))

    def _sign(shape):
        return int(np.sign(np.round(shape[3] - shape[0], 6)))

    matches = [m for m in shapes if _sign(shapes[m]) == obs_sign]
    # M0 and M1 are the same shape (even); treat the even class as one entry
    classes = sorted({("even" if m in ("M0", "M1") else m) for m in matches})
    shape_winner = matches[0] if len(classes) == 1 else None
    if shape_winner in ("M0", "M1"):
        shape_winner = "M0/M1"

    best = min(mean_rmse, key=mean_rmse.get)
    separated = all(lo > 0 for m, (lo, hi) in diff_ci.items() if m != best)
    accuracy_winner = best if separated else None
    return {"observed_sign_P4_minus_P1": obs_sign,
            "shape_matching_models": matches,
            "shape_winner": shape_winner,
            "lowest_rmse_model": best,
            "accuracy_winner": accuracy_winner,
            "conclusion": (f"{accuracy_winner} wins on accuracy"
                           if accuracy_winner else
                           "the data do not distinguish these models on "
                           "held-out accuracy (§4)")}


# ---------------------------------------------------------------------------
# §8 H1 regression
# ---------------------------------------------------------------------------


def h1_regression(df: pd.DataFrame, dev_col: str, perf_col: str = "I",
                  group_col: str = "swimmer_id") -> dict:
    """
    I_ij = b0 + b1*D_ij + b2*D_ij^2 + u_i + e_ij with a random intercept per
    swimmer (statsmodels MixedLM, REML). If the random-effect variance is not
    identifiable (fit fails, does not converge, or the variance collapses to
    the boundary), fall back to OLS with cluster-robust standard errors by
    swimmer and say so — the fallback the plan pre-registered.

    D is expressed in percentage points and centered at its mean so that b1
    is the local slope at a typical deviation; b2 is the curvature the
    theory predicts to be positive (a penalty growing quadratically away
    from the optimum) — positive b2 with negative b1 would say larger
    deviations hurt increasingly.
    """
    import warnings

    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.tools.sm_exceptions import ConvergenceWarning

    d = df[[group_col, dev_col, perf_col]].dropna().copy()
    d = d.rename(columns={dev_col: "D_raw", perf_col: "I"})
    d["D"] = d["D_raw"] - d["D_raw"].mean()
    d["D2"] = d["D"] ** 2
    n, n_sw = len(d), d[group_col].nunique()
    out = {"n_races": int(n), "n_swimmers": int(n_sw),
           "D_center_pp": float(d["D_raw"].mean()), "deviation_column": dev_col}

    used_mixed = False
    n_repeat = int((d.groupby(group_col).size() > 1).sum())
    out["n_swimmers_with_repeats"] = n_repeat
    try:
        if n_repeat < 2:
            raise RuntimeError("random intercept needs repeated swimmers")
        md = smf.mixedlm("I ~ D + D2", d, groups=d[group_col])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mf = md.fit(reml=True, method=["lbfgs"], maxiter=500)
        ill = any(issubclass(w.category, ConvergenceWarning) for w in caught)
        re_var = float(np.asarray(mf.cov_re).ravel()[0])
        converged = bool(getattr(mf, "converged", True)) and not ill
        if converged and np.isfinite(re_var) and re_var > 1e-10:
            used_mixed = True
            ci = mf.conf_int()
            for k in ("Intercept", "D", "D2"):
                out[f"{k}_est"] = float(mf.params[k])
                out[f"{k}_lo"] = float(ci.loc[k, 0])
                out[f"{k}_hi"] = float(ci.loc[k, 1])
                out[f"{k}_p"] = float(mf.pvalues[k])
            out["random_intercept_var"] = re_var
            out["residual_var"] = float(mf.scale)
            out["method"] = "MixedLM random intercept per swimmer (REML)"
    except Exception as e:  # noqa: BLE001 - the fallback is pre-registered
        out["mixed_error"] = str(e)[:200]

    if not used_mixed:
        X = sm.add_constant(d[["D", "D2"]])
        ols = sm.OLS(d["I"], X).fit(cov_type="cluster",
                                    cov_kwds={"groups": d[group_col]})
        ci = ols.conf_int()
        names = {"const": "Intercept", "D": "D", "D2": "D2"}
        for k, name in names.items():
            out[f"{name}_est"] = float(ols.params[k])
            out[f"{name}_lo"] = float(ci.loc[k, 0])
            out[f"{name}_hi"] = float(ci.loc[k, 1])
            out[f"{name}_p"] = float(ols.pvalues[k])
        out["random_intercept_var"] = float("nan")
        out["residual_var"] = float(ols.mse_resid)
        out["method"] = ("OLS with cluster-robust SE by swimmer (pre-registered "
                         "fallback: random-effect variance not identifiable)")
    out["used_mixed_effects"] = used_mixed
    return out
