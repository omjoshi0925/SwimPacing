"""
docs/parameters.md against src/parameters.py.

The classification tables in docs/parameters.md (Category A, B and C) state
a value for every parameter the model carries. Those values are copied by
hand, so this module reads the tables and checks each row against the code.
Every row must be accounted for in exactly one of four ways: mapped to a
dataclass default, mapped to a model-registry value, derived from the
registry by a stated computation, or listed as skipped with a reason. A row
this file cannot place fails, so a new parameter in the doc has to be wired
here deliberately rather than guessed at by attribute name.

Tolerance: relative 1e-9 for values written with a decimal point, exact for
values written as integers. A derived row states a range printed to a fixed
number of decimals, and is compared at that precision.
"""

import math
import re
from dataclasses import fields

import pytest

from src.parameters import MODELS, Course, Swimmer

DOC = "docs/parameters.md"

# Table symbol -> (Swimmer field, factor from the table's unit to the field's).
SWIMMER_FIELDS = {
    "rho": ("rho", 1.0),
    "C_D": ("Cd", 1.0),
    "A": ("A", 1.0),
    "eta_p": ("eta_p", 1.0),
    "eta_g": ("eta_g", 1.0),
    "p": ("p", 1.0),
    "R": ("R", 1.0),
    "E0": ("E0", 1000.0),       # the table says kJ, the field holds J
    "v_max": ("v_max", 1.0),
    "v_min": ("v_min", 1.0),
}

# Table symbol -> Course field (the default on the dataclass, which SCY_200 uses).
COURSE_FIELDS = {
    "Course.start_credit_s": "start_credit_s",
}

# Table symbol -> (registry models carrying the value, field). These define
# M1-M4 and are 0.0 on the Swimmer default by design, so the table's value is
# the registry's, not the dataclass's.
MODEL_FIELDS = {
    "tau": (("M1_oxygen_kinetics", "M2_reserve_fatigue",
             "M3_position_fatigue", "M4_velocity_ceiling"), "tau"),
    "beta_E": (("M2_reserve_fatigue",), "beta_E"),
    "beta_x": (("M3_position_fatigue",), "beta_x"),
    "gamma": (("M4_velocity_ceiling",), "gamma"),
}

# Derived rows: the table states a range summarising several registry values.
DERIVED = {
    "phi": lambda: (min(m.phi for m in MODELS.values()),
                    max(m.phi for m in MODELS.values())),
}

# Rows with no code default, each with the reason.
SKIP = {
    "t15": "a literature band (Category A) that band K sweeps as an input; "
           "src/parameters.py holds no default for it",
}

_NUM = r"[0-9]+(?:\.[0-9]+)?"


def _classification_tables(text: str) -> "list[tuple[str, str]]":
    """(symbol, value cell) for every row of the tables under '## Classification'."""
    section = text[text.index("## Classification"):text.index("## Full records")]
    rows, header = [], None
    for line in section.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):      # the |---|---| separator
            continue
        row = dict(zip(header, cells))
        rows.append((row["Symbol"].strip("`"), row["Value"]))
    return rows


def _number(value: str) -> "tuple[float, bool]":
    """Leading number of a value cell, and whether it was written as an integer."""
    m = re.match(rf"\s*({_NUM})", value)
    assert m, f"no leading number in {value!r}"
    return float(m.group(1)), "." not in m.group(1)


def _range(value: str) -> "tuple[float, float, int]":
    """Leading 'lo-hi' of a value cell and the number of decimals it is printed to."""
    m = re.match(rf"\s*({_NUM})-({_NUM})", value)
    assert m, f"no leading range in {value!r}"
    decimals = max(len(x.split(".")[1]) if "." in x else 0 for x in m.groups())
    return float(m.group(1)), float(m.group(2)), decimals


def _close(code: float, doc: float, exact: bool) -> bool:
    return code == doc if exact else math.isclose(code, doc, rel_tol=1e-9, abs_tol=0.0)


@pytest.fixture(scope="module")
def table_rows():
    with open(DOC, encoding="utf-8") as f:
        return _classification_tables(f.read())


def _value_of(table_rows, symbol: str) -> str:
    vals = [v for s, v in table_rows if s == symbol]
    assert len(vals) == 1, f"{symbol}: {len(vals)} rows in {DOC}, expected 1"
    return vals[0]


def test_every_table_row_is_accounted_for(table_rows):
    symbols = [s for s, _ in table_rows]
    known = (set(SWIMMER_FIELDS) | set(COURSE_FIELDS) | set(MODEL_FIELDS)
             | set(DERIVED) | set(SKIP))
    assert len(symbols) == len(set(symbols)), f"duplicate symbol in {DOC}"
    unplaced = [s for s in symbols if s not in known]
    assert not unplaced, (
        f"{DOC} rows with no mapping, derivation or skip reason here: {unplaced}")
    stale = sorted(known - set(symbols))
    assert not stale, f"wired in this test but no longer in {DOC}: {stale}"
    assert all(SKIP.values()), "every skipped row needs a reason"


@pytest.mark.parametrize("symbol", sorted(SWIMMER_FIELDS))
def test_swimmer_default_matches_the_table(table_rows, symbol):
    field_name, factor = SWIMMER_FIELDS[symbol]
    doc, is_int = _number(_value_of(table_rows, symbol))
    code = {f.name: f.default for f in fields(Swimmer)}[field_name]
    assert _close(code, doc * factor, is_int and factor == 1.0), (
        f"{symbol}: {DOC} says {doc} (x{factor}), Swimmer.{field_name} defaults to {code}")


@pytest.mark.parametrize("symbol", sorted(COURSE_FIELDS))
def test_course_default_matches_the_table(table_rows, symbol):
    field_name = COURSE_FIELDS[symbol]
    doc, is_int = _number(_value_of(table_rows, symbol))
    code = {f.name: f.default for f in fields(Course)}[field_name]
    assert _close(code, doc, is_int), (
        f"{symbol}: {DOC} says {doc}, Course.{field_name} defaults to {code}")


@pytest.mark.parametrize("symbol", sorted(MODEL_FIELDS))
def test_registry_value_matches_the_table(table_rows, symbol):
    models, field_name = MODEL_FIELDS[symbol]
    doc, is_int = _number(_value_of(table_rows, symbol))
    for name in models:
        code = getattr(MODELS[name], field_name)
        assert _close(code, doc, is_int), (
            f"{symbol}: {DOC} says {doc}, MODELS[{name!r}].{field_name} = {code}")


def test_phi_range_matches_the_registry(table_rows):
    lo_doc, hi_doc, decimals = _range(_value_of(table_rows, "phi"))
    lo, hi = DERIVED["phi"]()
    assert (round(lo, decimals), round(hi, decimals)) == (lo_doc, hi_doc), (
        f"phi: {DOC} says {lo_doc}-{hi_doc}, registry spans {lo}-{hi}")
