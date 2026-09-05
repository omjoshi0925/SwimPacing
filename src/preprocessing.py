"""
Data cleaning and normalized pacing metrics (Task 10).

Turns a hand-collected raw race file into the analysis file described in
`data/data_dictionary.md`. Nothing here silently repairs data: bad rows are
flagged and excluded, and the flag counts are reported, so a collection problem
shows up as a number rather than disappearing.

Command line:

    python -m src.preprocessing data/raw/200_free_scy_raw.csv
    python -m src.preprocessing data/raw/200_free_scy_raw.csv --out data/processed/x.csv
"""

from __future__ import annotations

import argparse
import os
import re
from typing import Iterable

import numpy as np
import pandas as pd

from .parameters import (MODELS, PREDICTED_SHAPES_SCY200, SCY_200,
                         START_OFFSET_S, Course)
from . import model as _model

RAW_COLUMNS = [
    "swimmer_id", "meet_id", "meet_name", "meet_date", "age", "sex_category",
    "event", "course", "round", "seed_time", "pre_race_pb", "final_time",
    "split_50", "split_100", "split_150", "split_200", "data_source",
]

CUMULATIVE = ["split_50", "split_100", "split_150", "split_200"]

#: The processed dataset, single source of truth for every consumer (scripts,
#: tests); duplicated string literals of this path drifted 4 ways before 104.
PROCESSED_CSV = "data/processed/200_free_scy_processed.csv"

#: Tolerance for split_200 against final_time, seconds. Official timing resolves
#: to 0.01 s, so 0.05 allows a little rounding without accepting a real mismatch.
TIME_MATCH_TOL = 0.05


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

# The seconds field is unbounded in digits so a bare "102.35" parses, but when a
# minutes field is present the seconds must be under 60 (see below). Restricting
# the seconds group to two digits would silently reject every plain-seconds time
# over 99 s, which is most of a 200 free.
_TIME_RE = re.compile(r"^\s*(?:(\d+):)?(\d+(?:\.\d+)?)\s*$")


def parse_time(value) -> float:
    """
    Parse a swimming time into seconds.

    Accepts "1:42.35", "102.35", "42.35", 102.35, and blank/NA forms. Returns
    NaN for anything unparseable rather than raising, because one malformed cell
    in a hand-typed file should flag that row, not kill the run.

    >>> parse_time("1:42.35")
    102.35
    >>> parse_time("58.07")
    58.07
    """
    if value is None:
        return np.nan
    if isinstance(value, (int, float)):
        return np.nan if pd.isna(value) else float(value)

    s = str(value).strip()
    if not s or s.upper() in {"NA", "N/A", "NAN", "NT", "NS", "DQ", "-", "--", ""}:
        return np.nan

    # Some sources use a comma decimal separator.
    s = s.replace(",", ".")

    m = _TIME_RE.match(s)
    if not m:
        return np.nan
    minutes, seconds = m.group(1), float(m.group(2))
    # A bare "1:02.5" is 62.5 s; a bare "62.5" is also 62.5 s. But a seconds
    # field of 60 or more inside a m:ss form is malformed.
    if minutes is not None:
        if seconds >= 60.0:
            return np.nan
        return int(minutes) * 60.0 + seconds
    return seconds


def format_time(seconds: float) -> str:
    """Seconds back to m:ss.hh, the way a split sheet reads."""
    if pd.isna(seconds):
        return ""
    m = int(seconds // 60)
    s = seconds - 60 * m
    return f"{m}:{s:05.2f}" if m else f"{s:.2f}"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_raw(path: str) -> pd.DataFrame:
    """Read the raw CSV and parse every time column into seconds."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"raw file is missing required columns: {missing}. "
            f"See data/data_dictionary.md for the expected header."
        )

    for col in CUMULATIVE + ["final_time", "pre_race_pb", "seed_time",
                             "prelim_time", "finals_time", "split_15m"]:
        if col in df.columns:
            df[col + "_s"] = df[col].map(parse_time)

    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["meet_date"] = pd.to_datetime(df["meet_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------


def derive_splits(df: pd.DataFrame) -> pd.DataFrame:
    """
    Individual 50 splits from cumulative splits.

    Cumulative is how split sheets report and how the raw file stores them;
    individual is what the model compares against. Doing the subtraction in one
    documented place avoids the classic error of treating a cumulative column as
    an individual split.
    """
    df = df.copy()
    c = [df[f"{col}_s"] for col in CUMULATIVE]
    df["split1_time"] = c[0]
    df["split2_time"] = c[1] - c[0]
    df["split3_time"] = c[2] - c[1]
    df["split4_time"] = c[3] - c[2]
    return df


def derive_pre_race_pb(df: pd.DataFrame) -> pd.Series:
    """
    Best time strictly BEFORE each race, computed from the file itself.

    More reliable than typing it by hand, and it enforces the rule that matters:
    a personal best set later must never inform a prediction about an earlier
    race. Races on the same date as the target race are excluded too, since
    prelim/final ordering within a day is not always recoverable.

    Returns NaN where the swimmer has no earlier race in the file. That is
    correct and honest; those rows drop out of the H1 analysis only.
    """
    out = pd.Series(np.nan, index=df.index, dtype=float)
    for sid, grp in df.groupby("swimmer_id", sort=False):
        grp = grp.sort_values("meet_date")
        for idx, row in grp.iterrows():
            earlier = grp[grp["meet_date"] < row["meet_date"]]["final_time_s"]
            earlier = earlier.dropna()
            if len(earlier):
                out.loc[idx] = float(earlier.min())
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def derive_linked_ages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Club-linked age ranges for rows whose source publishes no age (Task:
    dataset expansion; registered amendment 2026-09-02, validation_plan).

    Some official sources (high school results) list grades, not ages. When
    the SAME swimmer has age-published rows at other meets, the age at the
    age-blank meet is bounded by counting possible birthdays across the date
    gap: with known age a0 at date d0 and target date d, elapsed = (d-d0) in
    years, the age lies in [a0 + floor(elapsed), a0 + ceil(elapsed)] (works
    for both directions in time). Multiple age-published rows intersect their
    ranges; an empty intersection marks a link conflict (possible identity
    false-merge) and derives nothing.

    Adds: `age_lo`, `age_hi` (equal to `age` where published), `age_source`
    in {published, club_linked, link_conflict, none}. No published age is
    ever overwritten, and no single point value is invented for linked rows.
    """
    import math

    df = df.copy()
    dates = pd.to_datetime(df["meet_date"], errors="coerce")
    df["age_lo"] = df["age"].astype(float)
    df["age_hi"] = df["age"].astype(float)
    df["age_source"] = np.where(df["age"].notna(), "published", "none")

    for sid, grp in df.groupby("swimmer_id", sort=False):
        known = grp[grp["age"].notna()]
        blank = grp[grp["age"].isna()]
        if known.empty or blank.empty:
            continue
        for idx in blank.index:
            bounds = []
            for kidx in known.index:
                delta = (dates[idx] - dates[kidx]).days / 365.25
                a0 = float(df.at[kidx, "age"])
                bounds.append((a0 + math.floor(delta), a0 + math.ceil(delta)))
            lo = max(b[0] for b in bounds)
            hi = min(b[1] for b in bounds)
            if lo <= hi:
                df.at[idx, "age_lo"] = lo
                df.at[idx, "age_hi"] = hi
                df.at[idx, "age_source"] = "club_linked"
            else:
                df.at[idx, "age_source"] = "link_conflict"
    return df


def add_flags(df: pd.DataFrame, course: Course = SCY_200,
              age_range=(15, 18), expected_course="SCY") -> pd.DataFrame:
    """
    Attach every quality flag from the data dictionary, plus a `usable` column.

    Flags are additive and non-destructive. Nothing is dropped here, so the
    caller can always report how many rows failed and why.
    """
    df = df.copy()
    splits = df[["split1_time", "split2_time", "split3_time", "split4_time"]]
    cum = df[[f"{c}_s" for c in CUMULATIVE]]

    df["flag_missing_splits"] = cum.isna().any(axis=1) | df["final_time_s"].isna()

    # Strictly increasing cumulative splits.
    diffs = cum.diff(axis=1).iloc[:, 1:]
    df["flag_non_monotonic"] = (diffs <= 0).any(axis=1) | (cum.iloc[:, 0] <= 0)

    df["flag_time_mismatch"] = (
        (df["split_200_s"] - df["final_time_s"]).abs() > TIME_MATCH_TOL
    )

    mean_split = splits.mean(axis=1)
    lo, hi = 0.5 * mean_split, 2.0 * mean_split
    df["flag_implausible_split"] = (
        splits.lt(lo, axis=0) | splits.gt(hi, axis=0)
    ).any(axis=1)

    df["flag_duplicate"] = df.duplicated(
        subset=["swimmer_id", "meet_id", "round", "final_time"], keep="first"
    )

    df["flag_course_mismatch"] = df["course"].str.upper().str.strip() != expected_course
    # A row is in scope when its ENTIRE possible age range lies inside the
    # registered band: published ages have lo == hi == age; club-linked rows
    # (see derive_linked_ages, registered amendment 2026-09-02) carry a
    # derived [lo, hi]; rows with neither have NaN bounds and fail.
    if "age_lo" not in df.columns:
        df = derive_linked_ages(df)
    in_scope = (df["age_lo"] >= age_range[0]) & (df["age_hi"] <= age_range[1])
    df["flag_age_out_of_scope"] = ~in_scope.fillna(False)
    df["flag_no_pb"] = df["pre_race_pb_s"].isna()

    # flag_no_pb is NOT blocking: those rows still inform the shape analysis.
    blocking = [
        "flag_missing_splits", "flag_non_monotonic", "flag_time_mismatch",
        "flag_implausible_split", "flag_duplicate", "flag_course_mismatch",
        "flag_age_out_of_scope",
    ]
    df["usable"] = ~df[blocking].any(axis=1)
    return df


def flag_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Counts per flag, for the collection-quality report."""
    cols = [c for c in df.columns if c.startswith("flag_")]
    rows = [{"flag": c, "n": int(df[c].sum()),
             "pct": 100.0 * float(df[c].mean())} for c in cols]
    rows.append({"flag": "usable", "n": int(df["usable"].sum()),
                 "pct": 100.0 * float(df["usable"].mean())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Normalized pacing metrics
# ---------------------------------------------------------------------------


def add_pacing_metrics(df: pd.DataFrame,
                       start_offset: float = START_OFFSET_S) -> pd.DataFrame:
    """
    Normalized pacing variables (Task 10).

    Both raw and start-corrected split proportions are produced. The corrected
    set is what gets compared with the model, because the model describes free
    swimming and a recorded split 1 contains a dive start. The raw set is kept
    so the size of that correction stays visible.
    """
    df = df.copy()
    s = [df[f"split{i}_time"] for i in range(1, 5)]
    T = df["final_time_s"]

    for i in range(1, 5):
        df[f"P{i}"] = s[i - 1] / T

    # Recorded lap 1 contains the dive, which makes it FASTER than swimming
    # that lap at race pace, so the free-swimming-equivalent ("corrected")
    # race ADDS the credit back to lap 1 (the model.recorded_to_raced
    # direction), and the corrected shares are then comparable with model
    # raced split fractions. A previous version SUBTRACTED the credit here,
    # applying the model-side transform to the data as well and thereby
    # double-counting the credit by 2*offset on lap 1. Fixed 2026-09-01; see
    # the amendment log in docs/validation_plan.md.
    corrected = [s[0] + start_offset, s[1], s[2], s[3]]
    T_corr = sum(corrected)
    for i in range(1, 5):
        df[f"P{i}_corrected"] = corrected[i - 1] / T_corr
    df["start_offset_used"] = start_offset

    df["first_half"] = s[0] + s[1]
    df["second_half"] = s[2] + s[3]
    df["half_difference"] = df["second_half"] - df["first_half"]
    df["closing_fade"] = s[3] - s[1]

    arr = np.vstack([x.to_numpy(dtype=float) for x in s]).T
    df["split_variability"] = np.nanstd(arr, axis=1, ddof=1)
    df["max_split_difference"] = np.nanmax(arr, axis=1) - np.nanmin(arr, axis=1)

    P = np.vstack([df[f"P{i}"].to_numpy(dtype=float) for i in range(1, 5)]).T
    df["pace_deviation_even"] = np.sqrt(np.nanmean((P - 0.25) ** 2, axis=1))

    # The M3-versus-M4 discriminator: M3 predicts an even fade, M4 predicts most
    # of the loss between the first and second 50.
    df["drop_1_2"] = s[1] - s[0]
    df["drop_3_4"] = s[3] - s[2]
    with np.errstate(divide="ignore", invalid="ignore"):
        df["drop_ratio"] = df["drop_1_2"] / df["drop_3_4"]

    # The raw lap-1-to-2 drop embeds the dive (lap 1 is dive-fast), so the
    # fair discriminator credits it back: this is the drop the swimmer's
    # PACING produced, and the one to compare against M3/M4 predictions.
    df["drop_1_2_corrected"] = df["drop_1_2"] - start_offset
    with np.errstate(divide="ignore", invalid="ignore"):
        df["drop_ratio_corrected"] = df["drop_1_2_corrected"] / df["drop_3_4"]

    df["performance_improvement"] = (
        (df["pre_race_pb_s"] - df["final_time_s"]) / df["pre_race_pb_s"]
    )
    return df


# ---------------------------------------------------------------------------
# Model deviations
# ---------------------------------------------------------------------------


def model_predictions(course: Course = SCY_200, use_cache: bool = True) -> dict:
    """
    Predicted split proportions for each of M0-M4.

    The closed-form models are solved on demand. The path-dependent ones (M2,
    M4) take about a minute each through the ODE optimizer, so on SCY_200 they
    come from the cached values in parameters.py by default. Pass
    `use_cache=False` to force a live solve, which is what the test suite does
    to confirm the cache has not gone stale.
    """
    from . import optimization

    cached = PREDICTED_SHAPES_SCY200 if (use_cache and course is SCY_200) else {}

    preds = {}
    for name, sw in MODELS.items():
        if _model._closed_form_ok(sw):
            preds[name] = np.asarray(
                _model.optimal_solution_closed_form(sw, course)["split_fractions"])
        elif name in cached:
            preds[name] = np.asarray(cached[name], dtype=float)
        else:
            preds[name] = np.asarray(
                optimization.optimize_full(sw, course, n_starts=3)["split_fractions"])
    return preds


def add_model_deviations(df: pd.DataFrame, predictions: dict | None = None,
                         course: Course = SCY_200) -> pd.DataFrame:
    """
    RMSE of each race's start-corrected proportions against each model.

    This is the primary metric from `docs/validation_plan.md` §3.
    """
    df = df.copy()
    preds = predictions if predictions is not None else model_predictions(course)
    P = np.vstack([df[f"P{i}_corrected"].to_numpy(dtype=float) for i in range(1, 5)]).T

    for name, star in preds.items():
        short = name.split("_")[0]
        df[f"model_deviation_{short}"] = np.sqrt(np.mean((P - star[None, :]) ** 2, axis=1))

    dev_cols = [c for c in df.columns if c.startswith("model_deviation_")]
    if dev_cols:
        # idxmin raises on rows where every deviation is NaN, which is exactly
        # the situation for rows without splits, so restrict to rows that have
        # at least one finite deviation. Found by the first real ingest, in
        # which 449 of 581 rows had no split data.
        has_any = df[dev_cols].notna().any(axis=1)
        df["best_model"] = pd.NA
        if has_any.any():
            best = df.loc[has_any, dev_cols].idxmin(axis=1)
            df.loc[has_any, "best_model"] = best.str.replace(
                "model_deviation_", "", regex=False)
    return df


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def process(path: str, out_path: str | None = None,
            start_offset: float = START_OFFSET_S,
            recompute_pb: bool = True,
            course: Course = SCY_200) -> "tuple[pd.DataFrame, pd.DataFrame]":
    """
    Full pipeline: load, derive splits, flag, normalize, score against models.

    Returns (processed frame, flag summary). Writes the processed CSV if
    `out_path` is given.
    """
    df = load_raw(path)
    df = derive_splits(df)

    if recompute_pb:
        derived = derive_pre_race_pb(df)
        # Prefer a value typed by hand, fall back to the derived one. A hand
        # value may come from outside this file; the derived one never can.
        df["pre_race_pb_s"] = df["pre_race_pb_s"].fillna(derived)
        df["pre_race_pb_derived"] = derived.notna() & df["pre_race_pb"].eq("")

    df = add_flags(df, course=course)
    df = add_pacing_metrics(df, start_offset=start_offset)
    if df["usable"].any():
        df = add_model_deviations(df, course=course)

    summary = flag_summary(df)

    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        df.to_csv(out_path, index=False)
    return df, summary


def main(argv: Iterable[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw", help="path to the raw race CSV")
    ap.add_argument("--out", default=PROCESSED_CSV)
    ap.add_argument("--start-offset", type=float, default=START_OFFSET_S,
                    help="dive start credit applied to split 1, seconds")
    args = ap.parse_args(list(argv) if argv is not None else None)

    df, summary = process(args.raw, args.out, start_offset=args.start_offset)

    print(f"read {len(df)} races from {args.raw}")
    print(f"wrote {args.out}\n")
    print("quality flags:")
    for _, r in summary.iterrows():
        print(f"  {r['flag']:<28s} {r['n']:4d}  ({r['pct']:5.1f}%)")

    ok = df[df["usable"]]
    if not len(ok):
        print("\nno usable races; fix the flagged rows at the source.")
        return

    print(f"\nmean pacing over {len(ok)} usable races:")
    print("  recorded    P = " +
          "  ".join(f"{ok[f'P{i}'].mean():.4f}" for i in range(1, 5)))
    print(f"  start-corrected (offset {args.start_offset:.2f} s):")
    print("              P = " +
          "  ".join(f"{ok[f'P{i}_corrected'].mean():.4f}" for i in range(1, 5)))
    print(f"  half difference  {ok['half_difference'].mean():+.3f} s "
          f"(positive = positive split)")
    print(f"  drop 1->2 {ok['drop_1_2'].mean():+.3f} s   "
          f"drop 3->4 {ok['drop_3_4'].mean():+.3f} s   "
          f"(M3 predicts these similar, M4 predicts the first much larger)")

    dev = [c for c in ok.columns if c.startswith("model_deviation_")]
    if dev:
        print("\n  mean deviation from each model (percentage points):")
        for c in sorted(dev):
            print(f"    {c.replace('model_deviation_',''):<4s} "
                  f"{100 * ok[c].mean():.3f}")
        print("\n  NOTE: this is a descriptive summary on all usable races, not")
        print("  a held-out model comparison. See docs/validation_plan.md.")


if __name__ == "__main__":
    main()
