"""
Tests for the data pipeline (Tasks 10 and 13).

The fixture at tests/fixtures/synthetic_races.csv is SYNTHETIC. It exists to
exercise the pipeline, and every row says so in its data_source column. No
assertion here should ever be read as a fact about real swimming.
"""

import os

import numpy as np
import pandas as pd
import pytest

from src import data_split, preprocessing
from src.parameters import MODELS, PREDICTED_SHAPES_SCY200, SCY_200

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic_races.csv")


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,expected", [
    ("1:42.35", 102.35),
    ("1:02.50", 62.50),
    ("58.07", 58.07),
    ("102.35", 102.35),
    ("  1:42.35  ", 102.35),
    ("1:42,35", 102.35),        # comma decimal
    ("9.9", 9.9),
])
def test_parse_time_valid(text, expected):
    assert preprocessing.parse_time(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", "NT", "DQ", "NS", "N/A", "-", "abc",
                                  "1:75.00", "1:2:3", None])
def test_parse_time_invalid_returns_nan(text):
    """
    Unparseable input must return NaN, not raise. One malformed cell in a
    hand-typed file should flag that row, not abort the whole run.
    """
    assert np.isnan(preprocessing.parse_time(text))


def test_parse_time_rejects_impossible_seconds_field():
    """'1:75.00' is not 135 s, it is a typo. Must not be silently accepted."""
    assert np.isnan(preprocessing.parse_time("1:75.00"))


def test_parse_time_roundtrips_through_format():
    for seconds in (23.41, 58.07, 102.35, 135.0):
        assert preprocessing.parse_time(
            preprocessing.format_time(seconds)) == pytest.approx(seconds, abs=0.005)


# ---------------------------------------------------------------------------
# Split derivation
# ---------------------------------------------------------------------------


def test_splits_derived_from_cumulative_not_copied():
    """
    The classic error is treating a cumulative column as an individual split.
    Split 2 must be split_100 minus split_50, not split_100.
    """
    df = preprocessing.derive_splits(preprocessing.load_raw(FIXTURE))
    row = df.iloc[0]
    assert row["split1_time"] == pytest.approx(row["split_50_s"])
    assert row["split2_time"] == pytest.approx(row["split_100_s"] - row["split_50_s"])
    assert row["split3_time"] == pytest.approx(row["split_150_s"] - row["split_100_s"])
    assert row["split4_time"] == pytest.approx(row["split_200_s"] - row["split_150_s"])


def test_split_times_sum_to_final_time():
    df = preprocessing.derive_splits(preprocessing.load_raw(FIXTURE))
    df = preprocessing.add_flags(df)
    ok = df[df["usable"]]
    total = ok[[f"split{i}_time" for i in range(1, 5)]].sum(axis=1)
    assert np.allclose(total, ok["final_time_s"], atol=0.06)


# ---------------------------------------------------------------------------
# The pre-race personal best rule
# ---------------------------------------------------------------------------


def test_pre_race_pb_uses_only_earlier_races():
    """
    A personal best set AFTER a race must never inform a prediction about it.
    Using a later PB leaks the outcome into the predictor and would manufacture
    a relationship in the H1 analysis.
    """
    df = preprocessing.derive_splits(preprocessing.load_raw(FIXTURE))
    pb = preprocessing.derive_pre_race_pb(df)
    df["derived_pb"] = pb

    for sid, grp in df.groupby("swimmer_id"):
        grp = grp.sort_values("meet_date")
        for _, row in grp.iterrows():
            if pd.isna(row["derived_pb"]):
                continue
            earlier = grp[grp["meet_date"] < row["meet_date"]]["final_time_s"].dropna()
            assert len(earlier) > 0
            assert row["derived_pb"] == pytest.approx(earlier.min())
            # and it must not equal a time only achievable later
            later = grp[grp["meet_date"] > row["meet_date"]]["final_time_s"].dropna()
            if len(later) and later.min() < earlier.min():
                assert row["derived_pb"] != pytest.approx(later.min())


def test_first_race_of_a_swimmer_has_no_pb():
    """Blank is honest; substituting a seed time is not."""
    df = preprocessing.derive_splits(preprocessing.load_raw(FIXTURE))
    pb = preprocessing.derive_pre_race_pb(df)
    df["derived_pb"] = pb
    for sid, grp in df.groupby("swimmer_id"):
        first = grp.sort_values("meet_date").iloc[0]
        assert pd.isna(first["derived_pb"])


# ---------------------------------------------------------------------------
# Quality flags
# ---------------------------------------------------------------------------


def test_flags_catch_the_deliberately_broken_rows():
    df, summary = preprocessing.process(FIXTURE)
    by_id = df.set_index("swimmer_id")
    assert bool(by_id.loc["S099", "flag_non_monotonic"])
    assert bool(by_id.loc["S098", "flag_course_mismatch"])
    assert bool(by_id.loc["S097", "flag_age_out_of_scope"])
    assert bool(by_id.loc["S097", "flag_time_mismatch"])
    for sid in ("S099", "S098", "S097"):
        assert not bool(by_id.loc[sid, "usable"])


def test_clean_rows_are_usable():
    df, _ = preprocessing.process(FIXTURE)
    clean = df[~df["swimmer_id"].isin(["S099", "S098", "S097"])]
    assert clean["usable"].all()


def test_missing_pb_is_not_blocking():
    """
    Rows without a prior personal best still inform the shape analysis. Only the
    performance regression needs a PB, so flag_no_pb must not zero out usability.
    """
    df, _ = preprocessing.process(FIXTURE)
    no_pb = df[df["flag_no_pb"] & ~df["swimmer_id"].isin(["S099", "S098", "S097"])]
    assert len(no_pb) > 0
    assert no_pb["usable"].all()


def test_duplicate_detection():
    df = preprocessing.load_raw(FIXTURE)
    doubled = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    flagged = preprocessing.add_flags(preprocessing.derive_splits(doubled))
    assert flagged["flag_duplicate"].sum() == 1


# ---------------------------------------------------------------------------
# Normalized pacing metrics
# ---------------------------------------------------------------------------


def test_split_proportions_sum_to_one():
    df, _ = preprocessing.process(FIXTURE)
    ok = df[df["usable"]]
    for suffix in ("", "_corrected"):
        P = ok[[f"P{i}{suffix}" for i in range(1, 5)]].to_numpy(dtype=float)
        assert np.allclose(P.sum(axis=1), 1.0, atol=1e-9)


def test_start_correction_lowers_the_first_split_share():
    """Crediting the dive to split 1 must make split 1 a smaller share, not larger."""
    df, _ = preprocessing.process(FIXTURE)
    ok = df[df["usable"]]
    assert (ok["P1_corrected"] < ok["P1"]).all()


def test_half_difference_sign_matches_split_direction():
    df, _ = preprocessing.process(FIXTURE)
    ok = df[df["usable"]]
    positive = ok["half_difference"] > 0
    assert (ok.loc[positive, "second_half"] > ok.loc[positive, "first_half"]).all()


def test_pace_deviation_even_is_zero_for_perfectly_even_splits():
    df = pd.DataFrame({f"split{i}_time": [25.0] for i in range(1, 5)})
    df["final_time_s"] = 100.0
    df["pre_race_pb_s"] = 101.0
    out = preprocessing.add_pacing_metrics(df, start_offset=0.0)
    assert out["pace_deviation_even"].iloc[0] == pytest.approx(0.0, abs=1e-12)


def test_performance_improvement_sign():
    """Positive means faster than the previous best."""
    df = pd.DataFrame({f"split{i}_time": [25.0] for i in range(1, 5)})
    df["final_time_s"] = 100.0
    df["pre_race_pb_s"] = 102.0
    out = preprocessing.add_pacing_metrics(df, start_offset=0.0)
    assert out["performance_improvement"].iloc[0] > 0


# ---------------------------------------------------------------------------
# Model predictions and the cache
# ---------------------------------------------------------------------------


def test_cached_predictions_match_a_live_solve():
    """
    M2 and M4 are cached because each takes about a minute to solve. If MODELS
    changes and the cache is not refreshed, every model deviation silently
    becomes wrong. This is the guard against that.
    """
    live = preprocessing.model_predictions(SCY_200, use_cache=False)
    for name, cached in PREDICTED_SHAPES_SCY200.items():
        assert np.allclose(live[name], np.asarray(cached), atol=2e-3), (
            f"{name} cache is stale; run python -m scripts.refresh_predictions"
        )


def test_every_model_prediction_is_a_valid_distribution():
    preds = preprocessing.model_predictions(SCY_200)
    assert set(preds) == set(MODELS)
    for name, P in preds.items():
        assert np.isclose(P.sum(), 1.0, atol=1e-6), name
        assert (P > 0).all(), name


def test_models_make_the_predicted_qualitative_shapes():
    """The three-way split that makes this a real model comparison."""
    P = preprocessing.model_predictions(SCY_200)
    assert np.allclose(P["M0_constant_economy"], 0.25, atol=1e-6)
    assert np.allclose(P["M1_oxygen_kinetics"], 0.25, atol=1e-6)
    assert P["M2_reserve_fatigue"][0] > P["M2_reserve_fatigue"][3]     # negative
    assert P["M3_position_fatigue"][0] < P["M3_position_fatigue"][3]   # positive
    assert P["M4_velocity_ceiling"][0] < P["M4_velocity_ceiling"][3]   # positive


def test_M3_and_M4_are_distinguishable_by_shape_not_just_magnitude():
    """
    M3 predicts a near-even fade; M4 predicts most of the loss in the first
    transition. If this stopped being true the model comparison would lose its
    most informative statistic.
    """
    P = preprocessing.model_predictions(SCY_200)
    m3, m4 = P["M3_position_fatigue"], P["M4_velocity_ceiling"]
    r3 = (m3[1] - m3[0]) / (m3[3] - m3[2])
    r4 = (m4[1] - m4[0]) / (m4[3] - m4[2])
    assert r4 > 2.0 * r3


def test_model_deviation_is_zero_when_a_race_matches_a_model_exactly():
    P = preprocessing.model_predictions(SCY_200)
    star = P["M3_position_fatigue"]
    T = 100.0
    df = pd.DataFrame({f"split{i}_time": [star[i - 1] * T] for i in range(1, 5)})
    df["final_time_s"] = T
    df["pre_race_pb_s"] = T
    out = preprocessing.add_pacing_metrics(df, start_offset=0.0)
    out = preprocessing.add_model_deviations(out, predictions=P)
    assert out["model_deviation_M3"].iloc[0] == pytest.approx(0.0, abs=1e-9)
    assert out["best_model"].iloc[0] == "M3"


# ---------------------------------------------------------------------------
# Train / test splitting
# ---------------------------------------------------------------------------


def test_no_swimmer_appears_in_both_splits():
    """The single most important guarantee in the whole analysis pipeline."""
    df, _ = preprocessing.process(FIXTURE)
    train, test = data_split.split_by_swimmer(df[df["usable"]])
    assert data_split.check_no_leakage(train, test)
    assert len(set(train["swimmer_id"]) & set(test["swimmer_id"])) == 0


def test_split_is_deterministic_under_a_fixed_seed():
    df, _ = preprocessing.process(FIXTURE)
    ok = df[df["usable"]]
    a1, b1 = data_split.split_by_swimmer(ok, seed=42)
    a2, b2 = data_split.split_by_swimmer(ok, seed=42)
    assert list(a1["swimmer_id"]) == list(a2["swimmer_id"])
    assert list(b1["swimmer_id"]) == list(b2["swimmer_id"])


def test_split_covers_every_race_exactly_once():
    df, _ = preprocessing.process(FIXTURE)
    ok = df[df["usable"]]
    train, test = data_split.split_by_swimmer(ok)
    assert len(train) + len(test) == len(ok)


def test_split_puts_roughly_the_requested_fraction_in_test():
    df, _ = preprocessing.process(FIXTURE)
    ok = df[df["usable"]]
    train, test = data_split.split_by_swimmer(ok, test_fraction=0.25)
    rep = data_split.split_report(train, test)
    # Whole swimmers are assigned, so the realized fraction overshoots slightly.
    assert 0.20 <= rep["test_race_fraction"] <= 0.45
    assert rep["swimmer_overlap"] == 0


def test_naive_race_split_does_leak_and_is_only_there_to_show_it():
    """
    Demonstrates why grouping matters. With several races per swimmer, a random
    race split puts the same swimmer on both sides almost every time.
    """
    df, _ = preprocessing.process(FIXTURE)
    ok = df[df["usable"]]
    train, test = data_split.naive_race_split(ok)
    assert not data_split.check_no_leakage(train, test)


def test_split_rejects_a_frame_without_swimmer_ids():
    with pytest.raises(ValueError):
        data_split.split_by_swimmer(pd.DataFrame({"x": [1, 2, 3]}))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


def test_full_pipeline_produces_every_documented_column():
    df, summary = preprocessing.process(FIXTURE)
    expected = (
        [f"split{i}_time" for i in range(1, 5)]
        + [f"P{i}" for i in range(1, 5)]
        + [f"P{i}_corrected" for i in range(1, 5)]
        + ["first_half", "second_half", "half_difference", "closing_fade",
           "split_variability", "max_split_difference", "pace_deviation_even",
           "drop_1_2", "drop_3_4", "drop_ratio", "performance_improvement",
           "usable"]
        + [f"model_deviation_{m}" for m in ("M0", "M1", "M2", "M3", "M4")]
    )
    missing = [c for c in expected if c not in df.columns]
    assert not missing, f"pipeline did not produce: {missing}"
    assert len(summary) > 0


def test_fixture_is_labelled_synthetic_in_every_row():
    """
    Guards the rule in results/placeholder_data/README.md: synthetic data must
    never be mistakable for evidence. If this fixture ever loses its labelling,
    that is a real problem, not a test nit.
    """
    df = pd.read_csv(FIXTURE, dtype=str, keep_default_na=False)
    assert df["data_source"].str.upper().str.contains("SYNTHETIC").all()
