"""
Tests for src/calibration.py: the registered loss, then the fitters.

The loss tests tie the new code to numbers already published in
results/validation/pilot_model_comparison.csv, so the calibration module is
anchored to the same comparison the pilot report printed before any fitting
exists.
"""

import numpy as np
import pandas as pd
import pytest

from src import calibration, preprocessing
from src.parameters import SCY_200

PROCESSED = "data/processed/200_free_scy_processed.csv"
COMPARISON = "results/validation/pilot_model_comparison.csv"


@pytest.fixture(scope="module")
def usable():
    df = pd.read_csv(PROCESSED, low_memory=False)
    return df[df["usable"] == True]  # noqa: E712


# ---------------------------------------------------------------------------
# The registered loss
# ---------------------------------------------------------------------------


PILOT_V01_MEET = "2025_ORINDA_SC_SENIOR_OPEN"


def test_loss_reproduces_the_published_pilot_comparison(usable):
    """
    calibration.mean_rmse_pp must reproduce the pilot report's RMSE table.
    The comparison CSV is a FROZEN pilot-v0.1 artifact (80 Orinda races), so
    the check runs on that frozen subset; the processed file itself keeps
    growing as the expansion toward v0.2 proceeds.
    """
    published = pd.read_csv(COMPARISON).set_index("model")["mean_RMSE_pp"]
    shares = calibration.observed_shares(usable[usable["meet_id"] == PILOT_V01_MEET])
    preds = preprocessing.model_predictions(SCY_200)
    for name, star in preds.items():
        short = name.split("_")[0]
        got = calibration.mean_rmse_pp(star, shares)
        assert got == pytest.approx(published[short], abs=5e-4), short


def test_loss_agrees_with_the_pipeline_deviation_columns(usable):
    """Same number two ways: the loss vs the stored per-race deviations."""
    shares = calibration.observed_shares(usable)
    preds = preprocessing.model_predictions(SCY_200)
    for name, star in preds.items():
        short = name.split("_")[0]
        stored = usable[f"model_deviation_{short}"].mean() * 100
        assert calibration.mean_rmse_pp(star, shares) == pytest.approx(stored,
                                                                       abs=1e-9)


def test_loss_is_zero_only_at_the_observed_shape(usable):
    shares = calibration.observed_shares(usable)
    m = calibration.mean_shape(shares)
    single = shares[:1]
    assert calibration.mean_rmse_pp(single[0], single) == pytest.approx(0.0)
    assert calibration.mean_rmse_pp(m, shares) > 0  # dispersion never vanishes


def test_shares_at_credit_matches_pipeline_at_default(usable):
    """Recomputing shares at the default credit must equal the stored columns."""
    S = float(usable["start_offset_used"].iloc[0])
    recomputed = calibration.shares_at_credit(usable, S)
    stored = calibration.observed_shares(usable)
    assert np.allclose(recomputed, stored, atol=1e-12)


def test_observed_shares_refuses_missing_rows():
    df = pd.DataFrame({c: [0.25, np.nan] for c in calibration.OBS_COLS})
    with pytest.raises(ValueError, match="missing"):
        calibration.observed_shares(df)


# ---------------------------------------------------------------------------
# Synthetic recovery: fitters must find parameters they generated
# ---------------------------------------------------------------------------


def test_fit_beta_x_recovers_the_generating_value_exactly():
    """Noise-free: shares generated from beta_x = 0.31 must refit to 0.31."""
    truth = 0.31
    shares = np.tile(calibration.m3_shape(truth), (25, 1))
    fit = calibration.fit_beta_x(shares)
    assert fit.value == pytest.approx(truth, abs=1e-4)
    assert fit.loss_pp == pytest.approx(0.0, abs=1e-6)


def test_fit_beta_x_recovers_under_realistic_noise():
    """
    Race-level noise at the pilot's observed dispersion (sd ~0.5 pp per share)
    must not move the fitted value materially: the fit reads the mean shape,
    and the noise averages out across races.
    """
    truth = 0.31
    rng = np.random.default_rng(20260829)
    base = calibration.m3_shape(truth)
    noise = rng.normal(0.0, 0.005, size=(60, 4))
    noise -= noise.mean(axis=1, keepdims=True)  # keep each row summing to 1
    shares = base[None, :] + noise
    fit = calibration.fit_beta_x(shares)
    assert fit.value == pytest.approx(truth, abs=0.03)
    assert fit.improved() or fit.baseline_pp == pytest.approx(fit.loss_pp, abs=1e-9)


def test_fit_beta_x_is_deterministic():
    shares = np.tile(calibration.m3_shape(0.22), (10, 1))
    a = calibration.fit_beta_x(shares)
    b = calibration.fit_beta_x(shares)
    assert a.value == b.value and a.loss_pp == b.loss_pp and a.n_evals == b.n_evals


@pytest.mark.slow
def test_fit_gamma_recovers_the_generating_value():
    """
    Shares generated from the registry M4 shape (gamma = 0.18, pinned by the
    cache-freshness test) must refit to gamma near 0.18. Small eval budget:
    every objective evaluation is a full ODE optimization.
    """
    from src.parameters import PREDICTED_SHAPES_SCY200
    target = np.tile(np.array(PREDICTED_SHAPES_SCY200["M4_velocity_ceiling"]),
                     (10, 1))
    fit = calibration.fit_gamma(target, bounds=(0.10, 0.30), coarse=4,
                                refine_iters=4)
    assert fit.value == pytest.approx(0.18, abs=0.03)
    assert fit.loss_pp < 0.05


def test_training_frame_withholds_test_rows():
    train, meta = calibration.training_frame(PROCESSED)
    assert meta["n_train_races"] == len(train)
    assert meta["n_test_races_unopened"] > 0
    # the guard passes on the frame it produced
    calibration.assert_no_test_rows(train, PROCESSED)


def test_leakage_guard_raises_on_test_rows():
    """Feeding held-out rows to the guard is a hard error, not a warning."""
    from src import data_split
    df = pd.read_csv(PROCESSED, low_memory=False)
    ok = df[df["usable"] == True]  # noqa: E712
    _, test = data_split.split_by_swimmer(ok)
    with pytest.raises(calibration.CalibrationLeakageError, match="held-out"):
        calibration.assert_no_test_rows(test, PROCESSED)
    # and a single smuggled test row also trips it
    train, _ = calibration.training_frame(PROCESSED)
    smuggled = pd.concat([train, test.iloc[:1]])
    with pytest.raises(calibration.CalibrationLeakageError):
        calibration.assert_no_test_rows(smuggled, PROCESSED)


def test_fit_beta_x_on_train_rows_matches_the_committed_report(usable):
    """
    Determinism against the committed artifact: the exploratory fit report is
    a FROZEN pilot-v0.1 artifact, so refitting on the reconstructed v0.1
    training rows (Orinda races, registered seed) must reproduce the recorded
    value exactly, however much the live dataset has grown since.
    """
    from src import data_split

    rep = pd.read_csv("results/validation/fits_train_pilot.csv")
    row = rep[rep["param"] == "beta_x"].iloc[0]
    v01 = usable[usable["meet_id"] == PILOT_V01_MEET]
    train, _ = data_split.split_by_swimmer(v01)
    fit = calibration.fit_beta_x(calibration.observed_shares(train))
    assert fit.value == pytest.approx(row["fitted_value"], abs=1e-3)
    assert bool(row["exploratory"]) is True
    assert int(row["seed"]) == 20260829
    assert int(row["n_train_races"]) == len(train)
    # every fitted row in the pilot report is exploratory and train-sized
    fitted_rows = rep[rep["param"].astype(str).str.len() > 0]
    assert fitted_rows["exploratory"].astype(bool).all()
    assert (fitted_rows["n_train_races"] == len(train)).all()


@pytest.mark.slow
def test_fit_beta_E_recovers_the_generating_value():
    """Same recovery contract for M2's reserve coupling (registry 0.28)."""
    from src.parameters import PREDICTED_SHAPES_SCY200
    target = np.tile(np.array(PREDICTED_SHAPES_SCY200["M2_reserve_fatigue"]),
                     (10, 1))
    fit = calibration.fit_beta_E(target, bounds=(0.15, 0.45), coarse=4,
                                 refine_iters=4)
    assert fit.value == pytest.approx(0.28, abs=0.04)
    assert fit.loss_pp < 0.05
