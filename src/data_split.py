"""
Train and test splitting, grouped by swimmer (Task 13).

The whole point of this module is one rule:

    NO SWIMMER APPEARS IN BOTH THE TRAINING AND TEST SETS.

Multiple races by one swimmer share that swimmer's technique, physiology, start
quality and habitual pacing. A random split over *races* would put race 1 in
training and race 2 in testing, and the model would then be scored partly on how
well it memorized that individual. The measured test error would be optimistic
and the paper would be wrong in a way that is very hard to see afterwards.

Splitting by swimmer costs some effective sample size and buys an honest number.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Fixed in docs/validation_plan.md before any data existed. Changing it after
#: seeing results turns a confirmatory analysis into an exploratory one.
DEFAULT_SEED = 20260829


def split_by_swimmer(df: pd.DataFrame, test_fraction: float = 0.25,
                     seed: int = DEFAULT_SEED,
                     group_col: str = "swimmer_id") -> "tuple[pd.DataFrame, pd.DataFrame]":
    """
    Split races into train and test with no swimmer on both sides.

    Swimmers are shuffled and assigned whole to one side until the test side
    holds at least `test_fraction` of the *races*. Assigning by swimmer while
    targeting a race fraction means the realized fraction will not land exactly
    on the target, which is expected and reported rather than forced.

    Returns (train, test) as copies with a `split` column added.
    """
    if group_col not in df.columns:
        raise ValueError(f"{group_col!r} not in the frame; cannot split safely")
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be strictly between 0 and 1")

    counts = df.groupby(group_col).size()
    swimmers = counts.index.to_numpy()

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(swimmers))

    target = test_fraction * len(df)
    test_swimmers, running = [], 0
    for i in order:
        if running >= target:
            break
        s = swimmers[i]
        test_swimmers.append(s)
        running += int(counts.loc[s])

    test_set = set(test_swimmers)
    is_test = df[group_col].isin(test_set)

    train = df.loc[~is_test].copy()
    test = df.loc[is_test].copy()
    train["split"] = "train"
    test["split"] = "test"

    overlap = set(train[group_col]) & set(test[group_col])
    if overlap:  # pragma: no cover - guarded by construction, checked anyway
        raise AssertionError(f"swimmer leaked across the split: {sorted(overlap)[:5]}")

    return train, test


def split_report(train: pd.DataFrame, test: pd.DataFrame,
                 group_col: str = "swimmer_id") -> dict:
    """Summary of a split, for the record and for the paper's methods section."""
    n = len(train) + len(test)
    return {
        "n_races_total": n,
        "n_races_train": len(train),
        "n_races_test": len(test),
        "test_race_fraction": len(test) / n if n else float("nan"),
        "n_swimmers_train": train[group_col].nunique(),
        "n_swimmers_test": test[group_col].nunique(),
        "races_per_swimmer_train": (len(train) / train[group_col].nunique()
                                    if len(train) else float("nan")),
        "races_per_swimmer_test": (len(test) / test[group_col].nunique()
                                   if len(test) else float("nan")),
        "swimmer_overlap": len(set(train[group_col]) & set(test[group_col])),
    }


def check_no_leakage(train: pd.DataFrame, test: pd.DataFrame,
                     group_col: str = "swimmer_id") -> bool:
    """Explicit assertion helper, so the guarantee can be tested and re-tested."""
    return len(set(train[group_col]) & set(test[group_col])) == 0


def naive_race_split(df: pd.DataFrame, test_fraction: float = 0.25,
                     seed: int = DEFAULT_SEED) -> "tuple[pd.DataFrame, pd.DataFrame]":
    """
    A deliberately WRONG split, provided only so the leakage it causes can be
    demonstrated and quantified rather than asserted.

    Do not use this for any reported result. It shuffles races, so a swimmer can
    and will appear on both sides.
    """
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(df))
    cut = int(round(test_fraction * len(df)))
    test = df.iloc[idx[:cut]].copy()
    train = df.iloc[idx[cut:]].copy()
    train["split"] = "train"
    test["split"] = "test"
    return train, test
