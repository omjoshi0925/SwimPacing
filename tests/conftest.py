"""
Shared synthetic fixtures.

Every test that needs a dataset reads one derived from
`tests/fixtures/synthetic_raw.csv`: invented swimmers, teams, meets and times
carried in the real raw schema. No test may read `data/`. Those files are
gitignored, so a test that reaches for them passes locally and fails on a clean
checkout, which is exactly how the CI suite broke on 2026-09-01 and stayed
broken for 51 commits.

Tests that genuinely assert a property of the REAL dataset (published benchmark
values, frozen artifact counts) cannot be served by a fixture without
fabricating the very numbers under test. Those are marked `requires_data` and
deselected in CI instead.
"""

import pandas as pd
import pytest

from src import preprocessing

SYNTHETIC_RAW = "tests/fixtures/synthetic_raw.csv"


@pytest.fixture(scope="session")
def synthetic_raw_csv() -> str:
    """The committed synthetic raw file, in the real raw schema."""
    return SYNTHETIC_RAW


@pytest.fixture(scope="session")
def synthetic_processed_csv(tmp_path_factory) -> str:
    """
    The synthetic raw file put through the real pipeline.

    Derived at test time rather than committed, deliberately: the
    `model_deviation_*` columns come out of `src.preprocessing`, so a test
    comparing them against `src.calibration` compares two independent modules
    rather than comparing hand-written numbers with themselves.
    """
    out = tmp_path_factory.mktemp("synthetic") / "processed.csv"
    df, _ = preprocessing.process(SYNTHETIC_RAW, str(out))
    assert bool(df["usable"].all()), "synthetic fixture must be entirely usable"
    return str(out)


@pytest.fixture(scope="session")
def synthetic_usable(synthetic_processed_csv) -> pd.DataFrame:
    """Usable rows of the derived synthetic dataset."""
    df = pd.read_csv(synthetic_processed_csv, low_memory=False)
    return df[df["usable"] == True]  # noqa: E712
