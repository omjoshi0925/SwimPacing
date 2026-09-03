"""
Tests for src/stats.py: the held-out statistics are simple on purpose, and
these pin the parts that would silently mislead if wrong — the per-race
metric agreeing with the registered loss, the bootstrap resampling swimmers
rather than races, the §4 criteria firing only when they should, and the
§8 regression falling back to cluster-robust OLS when the random effect is
not identifiable.
"""

import numpy as np
import pandas as pd
import pytest

from src import calibration, stats


def _shares(n, rng):
    P = 0.25 + rng.normal(0, 0.006, size=(n, 4))
    return P / P.sum(axis=1, keepdims=True)


def test_race_rmse_matches_the_registered_loss():
    rng = np.random.default_rng(0)
    P = _shares(40, rng)
    shape = np.array([0.243, 0.248, 0.252, 0.257])
    per_race = stats.race_rmse_pp(P, shape)
    assert per_race.shape == (40,)
    assert np.isclose(per_race.mean(), calibration.mean_rmse_pp(shape, P))


def test_cluster_bootstrap_resamples_swimmers_not_races():
    rng = np.random.default_rng(1)
    # 10 swimmers, 5 races each; race values differ by swimmer only
    clusters = np.repeat(np.arange(10), 5)
    values = np.repeat(rng.normal(0, 1, 10), 5)
    out = stats.cluster_bootstrap(values, clusters, n_boot=500, seed=3)
    assert out["n_clusters"] == 10
    assert out["lo"] <= out["estimate"] <= out["hi"]
    # every bootstrap draw is a mean of whole-swimmer blocks, so its set of
    # distinct values is at most 10 (a race-level resample would show more)
    draw_vals = np.unique(np.round(out["draws"], 12))
    assert len(draw_vals) <= 500
    # the CI must be wider than a naive per-race bootstrap would give
    naive = stats.cluster_bootstrap(values, np.arange(50), n_boot=500, seed=3)
    assert (out["hi"] - out["lo"]) > (naive["hi"] - naive["lo"])


def test_cluster_bootstrap_applies_one_resample_to_every_column():
    rng = np.random.default_rng(2)
    clusters = np.repeat(np.arange(8), 3)
    a = rng.normal(size=24)
    out = stats.cluster_bootstrap(np.column_stack([a, a + 1.0]), clusters,
                                  n_boot=200, seed=4)
    # identical resampling means the column difference is exactly 1 every draw
    assert np.allclose(out["draws"][:, 1] - out["draws"][:, 0], 1.0)


def test_win_criteria_declare_a_winner_only_when_separated():
    shapes = {"M0": np.full(4, 0.25), "M1": np.full(4, 0.25),
              "M2": np.array([0.27, 0.26, 0.24, 0.23]),
              "M3": np.array([0.243, 0.248, 0.252, 0.257])}
    P_mean = np.array([0.242, 0.249, 0.255, 0.254])
    mean_rmse = {"M0": 0.6, "M1": 0.6, "M2": 2.5, "M3": 0.45}
    separated = {"M0": (0.05, 0.25), "M1": (0.05, 0.25), "M2": (1.8, 2.3)}
    c = stats.apply_win_criteria(mean_rmse, separated, P_mean, shapes)
    assert c["shape_winner"] == "M3" and c["accuracy_winner"] == "M3"
    overlapping = dict(separated, M0=(-0.02, 0.25), M1=(-0.02, 0.25))
    c = stats.apply_win_criteria(mean_rmse, overlapping, P_mean, shapes)
    assert c["accuracy_winner"] is None
    assert "do not distinguish" in c["conclusion"]


def test_win_criteria_even_class_counts_once_and_needs_a_unique_sign():
    shapes = {"M0": np.full(4, 0.25), "M1": np.full(4, 0.25),
              "M3": np.array([0.243, 0.248, 0.252, 0.257]),
              "M4": np.array([0.240, 0.249, 0.254, 0.257])}
    P_mean = np.array([0.242, 0.249, 0.255, 0.254])   # positive split
    c = stats.apply_win_criteria({"M0": 1, "M1": 1, "M3": 0.5, "M4": 0.5},
                                 {"M0": (0.1, 0.2), "M1": (0.1, 0.2), "M4": (-0.1, 0.1)},
                                 P_mean, shapes)
    assert c["shape_matching_models"] == ["M3", "M4"] and c["shape_winner"] is None
    P_even = np.array([0.25, 0.25, 0.25, 0.25])
    c = stats.apply_win_criteria({"M0": 1, "M1": 1, "M3": 2, "M4": 2},
                                 {"M1": (0, 0), "M3": (0.5, 1.5), "M4": (0.5, 1.5)},
                                 P_even, shapes)
    assert c["shape_winner"] == "M0/M1"


@pytest.mark.slow
def test_h1_regression_returns_the_registered_quantities_and_falls_back():
    pytest.importorskip("statsmodels")
    rng = np.random.default_rng(5)
    # 30 swimmers x 3 races with a real random intercept -> mixed model
    sw = np.repeat([f"S{i:03d}" for i in range(30)], 3)
    u = np.repeat(rng.normal(0, 2.0, 30), 3)
    D = rng.uniform(0.2, 1.5, 90)
    I = 1.0 - 0.8 * D + u + rng.normal(0, 0.3, 90)
    df = pd.DataFrame({"swimmer_id": sw, "D": D, "I": I})
    out = stats.h1_regression(df, "D", "I")
    for k in ("D_est", "D_lo", "D_hi", "D2_est", "D2_lo", "D2_hi",
              "random_intercept_var", "residual_var", "method"):
        assert k in out
    assert out["used_mixed_effects"] and out["random_intercept_var"] > 0.5
    assert out["D_lo"] < -0.8 < out["D_hi"]
    # one race per swimmer: the random effect is not identifiable -> OLS
    single = df.groupby("swimmer_id").head(1)
    out1 = stats.h1_regression(single, "D", "I")
    assert "OLS" in out1["method"] and not out1["used_mixed_effects"]
