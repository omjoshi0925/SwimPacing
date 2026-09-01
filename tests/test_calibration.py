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


def test_loss_reproduces_the_published_pilot_comparison(usable):
    """calibration.mean_rmse_pp must reproduce the pilot report's RMSE table."""
    published = pd.read_csv(COMPARISON).set_index("model")["mean_RMSE_pp"]
    shares = calibration.observed_shares(usable)
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
