"""
Tests for scripts/evaluate_holdout.py on SYNTHETIC frames: the script's
integrity rules (no exploratory fits, shape checks, criteria applied as
registered) must hold regardless of what the real data say, and the real
test set must never be opened by a test.
"""

import numpy as np
import pandas as pd
import pytest

from scripts import evaluate_holdout as eh
from src import calibration
from src.parameters import SCY_200


def _frame(n, seed, shape, noise=0.004):
    rng = np.random.default_rng(seed)
    T = rng.uniform(100, 125, n)
    P = np.asarray(shape) + rng.normal(0, noise, (n, 4))
    P /= P.sum(axis=1, keepdims=True)
    laps = P * (T + SCY_200.start_credit_s)[:, None]
    laps[:, 0] -= SCY_200.start_credit_s          # back to recorded lap 1
    df = pd.DataFrame({f"split{i+1}_time": laps[:, i] for i in range(4)})
    df["final_time_s"] = laps.sum(axis=1)
    for i in range(4):
        df[f"P{i+1}_corrected"] = P[:, i]
    df["swimmer_id"] = [f"S{k:03d}" for k in rng.integers(0, n // 2, n)]
    df["age_source"] = "published"
    return df


def test_exploratory_fit_reports_are_refused(tmp_path):
    fits = pd.DataFrame({"model": ["M3_position_fatigue"], "param": ["beta_x"],
                         "fitted_value": [0.2], "shape": ["0/0/0/0"],
                         "exploratory": [True]})
    path = tmp_path / "fits.csv"
    fits.to_csv(path, index=False)
    with pytest.raises(SystemExit, match="exploratory"):
        eh.fitted_shapes(str(path), ["M0", "M3"])


def test_m3_shape_comes_from_the_registered_value(tmp_path):
    fits = pd.DataFrame({"model": ["M3_position_fatigue"], "param": ["beta_x"],
                         "fitted_value": [0.2277], "shape": [""],
                         "exploratory": [False]})
    path = tmp_path / "fits.csv"
    fits.to_csv(path, index=False)
    shapes, values = eh.fitted_shapes(str(path), ["M0", "M1", "M3"])
    assert values == {"M3": 0.2277}
    assert np.allclose(shapes["M3"], calibration.m3_shape(0.2277))
    assert np.allclose(shapes["M0"], 0.25) and np.allclose(shapes["M1"], 0.25)


def test_compare_separates_models_when_the_data_do():
    shapes = {"M0": np.full(4, 0.25), "M3": calibration.m3_shape(0.25)}
    test = _frame(120, 7, shapes["M3"], noise=0.003)
    res = eh.compare(test, shapes, n_boot=400, label="synthetic")
    t = res["table"].set_index("model")
    assert t.loc["M3", "mean_RMSE_pp"] < t.loc["M0", "mean_RMSE_pp"]
    assert res["criteria"]["accuracy_winner"] == "M3"
    assert res["criteria"]["shape_winner"] == "M3"
    assert set(t.columns) >= {"RMSE_ci_lo", "RMSE_ci_hi", "diff_ci_lo",
                              "signed_err_P1_pp", "n_races_best"}


def test_compare_declines_to_pick_when_the_data_do_not():
    m3 = calibration.m3_shape(0.05)
    shapes = {"M2": m3[::-1].copy(), "M3": m3}   # mirror images around even
    test = _frame(60, 8, np.full(4, 0.25), noise=0.006)  # truth: even
    res = eh.compare(test, shapes, n_boot=400, label="synthetic")
    assert res["criteria"]["accuracy_winner"] is None
    assert "do not distinguish" in res["criteria"]["conclusion"]


def test_start_band_moves_only_the_data_side():
    shapes = {"M0": np.full(4, 0.25), "M3": calibration.m3_shape(0.2)}
    test = _frame(50, 9, shapes["M3"])
    sens = eh.start_band(test, shapes)
    assert list(sens["offset_s"]) == list(eh.BAND)
    # at the registered credit the sweep reproduces the direct evaluation
    row = sens[np.isclose(sens["offset_s"], SCY_200.start_credit_s)].iloc[0]
    P = calibration.observed_shares(test)
    direct = np.sqrt(np.mean((P - shapes["M3"]) ** 2, axis=1)).mean() * 100
    assert abs(row["M3"] - direct) < 1e-4   # table rounds to 4 decimals
    # a larger credit makes the data more front-loaded-corrected, i.e. flatter
    assert sens["M0"].iloc[-1] != sens["M0"].iloc[0]
