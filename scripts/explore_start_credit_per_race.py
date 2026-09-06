"""
EXPLORATORY per-race start credit S(v) = 15/v - t15 (roadmap band K, row 111).

Replaces the constant dive credit with a per-race, pace-aware one and asks a
narrow question: across the plausible t15 band, is beta_x's fitted range
narrower than the constant-credit sweep's 0.3335 -> 0.0103, and does the
held-out ranking stabilize? Declared in docs/validation_plan.md (2026-09-05).

Hard constraints, enforced here:
- Exploratory. The test set was opened 2026-09-03; every row this script
  writes carries exploratory=True. The registered conclusion cannot change.
- Writes ONLY results/validation/exploratory_start_credit_per_race.csv and
  figure emp09. It never imports scripts.evaluate_holdout (whose writers own
  the frozen registered artifacts) and refuses to write to any other path
  under results/.
- t15 is a literature quantity (docs/parameters.md, Category A); it is swept
  or fixed, never fitted.
- Fits run on TRAINING rows only via calibration.training_frame, with the
  CalibrationLeakageError guard applied to every fitted frame.

Regimes (one cell each unless noted):
  (iii) reference: constant S = 1.80 s for every race. Runs FIRST and ALONE.
        Gate: the per-race path must equal shares_at_credit(df, 1.80) and the
        stored P{i}_corrected to <= 1e-9; the held-out RMSEs at the REGISTERED
        fitted values must match model_comparison.csv exactly at its four
        decimals for the closed-form models (M0, M1, M3) and to within 2e-4 pp
        for the ODE models (M2, M4), whose shapes come from a re-solve that
        does not reproduce the registered run bit-for-bit (see the note on
        ODE_TOL_PP). If the gate fails nothing is written and the exit code
        is 2.
  (i)   constant t15 swept 6.1-7.5 s in 0.2 s steps (8 cells).
  (ii)  proportional t15 = k * 15/v with k = 6.4 / (15 / (182.88/93)), so an
        elite ~1:33 SCY swim gets 6.4 s (1 cell).
Per cell: refit beta_x (closed form), gamma and beta_E (ODE) on the training
rows; score M0-M4 held-out; record fitted values, losses, RMSEs, the ranking
and sign(P4-P1). Each finished cell is appended to the CSV immediately, and a
rerun resumes from whatever the CSV already holds.

Usage:
    python -m scripts.explore_start_credit_per_race --gate-only   # (iii) + gate
    python -m scripts.explore_start_credit_per_race               # all cells
    python -m scripts.explore_start_credit_per_race --figure      # emp09 only
    --skip-ode fits beta_x only (smoke tests); rows are marked skip_ode=True.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import calibration, data_split, model, preprocessing, stats  # noqa: E402
from src.parameters import SCY_200  # noqa: E402
from src.preprocessing import PROCESSED_CSV as PROCESSED  # noqa: E402

OUT = "results/validation/exploratory_start_credit_per_race.csv"
FIG = "figures/empirical/emp09_start_credit_per_race"
#: read-only registered references; this script never writes them
FITS_REGISTERED = "results/model_calibration/fits_train_v0_2.csv"
COMPARISON_REGISTERED = "results/validation/model_comparison.csv"
M3_REFIT_CONSTANT = "results/validation/holdout_start_sensitivity_m3_refit.csv"

KEY = {"M0": "M0_constant_economy", "M1": "M1_oxygen_kinetics",
       "M2": "M2_reserve_fatigue", "M3": "M3_position_fatigue",
       "M4": "M4_velocity_ceiling"}
PARAM = {"M2": "beta_E", "M3": "beta_x", "M4": "gamma"}
MODELS = ["M0", "M1", "M2", "M3", "M4"]

T15_GRID = np.round(np.arange(6.1, 7.51, 0.2), 2)          # 8 values
ELITE_T_S = 93.0                                          # ~1:33 SCY
K_PROP = 6.4 / (15.0 / (SCY_200.total_distance_m / ELITE_T_S))   # 0.839
REFERENCE_S = SCY_200.start_credit_s                      # 1.80
GATE_TOL = 1e-9
#: Held-out RMSE reproduction, per model class (owner's decision, 2026-09-05).
#: Closed-form models must match the registered CSV exactly at its 4 decimals.
#: The ODE models' shapes come from a re-solve whose result drifted between
#: the registered run and today (M2: 0.7709 recorded, 0.771022 re-solved by
#: evaluate_holdout's own code; M4 reproduces), so they get a stated
#: solver-reproducibility band; both numbers are printed and recorded.
CLOSED_FORM = ("M0", "M1", "M3")
ODE_TOL_PP = 2e-4


# ---------------------------------------------------------------------------
# cells and credits
# ---------------------------------------------------------------------------


def cells() -> list:
    out = [{"cell": "iii_constant_S_1.80", "regime": "iii", "t15_s": np.nan,
            "k": np.nan, "S_constant_s": REFERENCE_S}]
    for t in T15_GRID:
        out.append({"cell": f"i_t15_{t:.1f}", "regime": "i", "t15_s": float(t),
                    "k": np.nan, "S_constant_s": np.nan})
    out.append({"cell": f"ii_k_{K_PROP:.3f}", "regime": "ii", "t15_s": np.nan,
                "k": float(K_PROP), "S_constant_s": np.nan})
    return out


def whole_race_velocity(df: pd.DataFrame) -> np.ndarray:
    """v = 182.88 / T per race: the amendment (b) definition (circular in
    lap 1, stated in model.start_credit_per_race)."""
    return SCY_200.total_distance_m / df["final_time_s"].to_numpy(dtype=float)


def credit_for(cell: dict, df: pd.DataFrame) -> np.ndarray:
    n = len(df)
    if cell["regime"] == "iii":
        return np.full(n, cell["S_constant_s"])
    v = whole_race_velocity(df)
    if cell["regime"] == "i":
        return model.start_credit_per_race(v, cell["t15_s"])
    t15 = cell["k"] * 15.0 / v            # regime (ii): t15 proportional to 15/v
    return model.start_credit_per_race(v, t15)


# ---------------------------------------------------------------------------
# shapes and scoring (the evaluate_holdout logic, re-stated locally so the
# registered writers are never imported)
# ---------------------------------------------------------------------------


def shapes_from_values(values: dict, cache: dict) -> dict:
    base = preprocessing.model_predictions(SCY_200)
    shapes = {}
    for m in MODELS:
        if m in ("M0", "M1"):
            shapes[m] = np.asarray(base[KEY[m]], dtype=float)
        elif m == "M3":
            shapes[m] = calibration.m3_shape(values["M3"])
        else:
            shapes[m] = calibration._ode_shape(KEY[m], PARAM[m], values[m], SCY_200, cache)
    return shapes


def score(P: np.ndarray, shapes: dict) -> dict:
    rmse = {m: float(stats.race_rmse_pp(P, shapes[m]).mean()) for m in MODELS}
    ranking = sorted(MODELS, key=lambda m: rmse[m])
    Pm = P.mean(axis=0)
    return {"rmse": rmse, "best": ranking[0], "ranking": ">".join(ranking),
            "sign_P4_minus_P1": int(np.sign(Pm[3] - Pm[0])),
            "P_mean": Pm}


def registered_values() -> dict:
    fits = pd.read_csv(FITS_REGISTERED)
    if bool(fits["exploratory"].astype(bool).any()):
        raise SystemExit(f"{FITS_REGISTERED} carries exploratory rows; refusing")
    vals = {}
    for m, key in KEY.items():
        row = fits[fits["model"] == key]
        if m in PARAM and not row.empty:
            vals[m] = float(row["fitted_value"].iloc[0])
    return vals


# ---------------------------------------------------------------------------
# the gate: the per-race path at S == 1.80 must be the registered path
# ---------------------------------------------------------------------------


def gate(train: pd.DataFrame, test: pd.DataFrame, cache: dict) -> bool:
    ok = True
    for name, df in (("train", train), ("test", test)):
        per = calibration.shares_at_credit(df, np.full(len(df), REFERENCE_S))
        scalar = calibration.shares_at_credit(df, REFERENCE_S)
        stored = calibration.observed_shares(df)
        d1, d2 = np.abs(per - scalar).max(), np.abs(per - stored).max()
        print(f"gate/{name}: |per-race - scalar| max {d1:.2e}, "
              f"|per-race - stored| max {d2:.2e} (tol {GATE_TOL:.0e})")
        ok &= (d1 <= GATE_TOL) and (d2 <= GATE_TOL)
    # the per-race credit path for regimes (i)/(ii), which the reference cell
    # (credit == 1.80 everywhere) would otherwise never exercise
    T = test["final_time_s"].to_numpy(dtype=float)
    ci = credit_for({"regime": "i", "t15_s": 6.12}, test)
    expect = 15.0 * T / SCY_200.total_distance_m - 6.12
    d_i = np.abs(ci - expect).max()
    order = np.argsort(T, kind="stable")
    dT, dS = np.diff(T[order]), np.diff(ci[order])
    # slower race -> more credit; races with an identical final time get an
    # identical credit (ties exist in the held-out rows), so strictness is
    # required only where T strictly increases
    mono = bool((dS[dT > 0] > 0).all() and (np.abs(dS[dT == 0]) <= 1e-12).all())
    cii = credit_for({"regime": "ii", "k": K_PROP}, test)
    print(f"gate/credit: regime (i) |S - (15T/L - t15)| max {d_i:.2e}; increasing in T: {mono}; "
          f"regime (ii) S in [{cii.min():.2f}, {cii.max():.2f}] s, all positive: {bool((cii > 0).all())}")
    ok &= (d_i <= 1e-12) and mono and bool((cii > 0).all())
    vals = registered_values()
    shapes = shapes_from_values(vals, cache)
    # the ODE band below is only meaningful if the re-solved shapes sit within
    # the drift evaluate_holdout.fitted_shapes itself tolerates (2e-4 per lap)
    fits = pd.read_csv(FITS_REGISTERED)
    for m in ("M2", "M4"):
        rec = np.array([float(x) for x in fits[fits["model"] == KEY[m]]["shape"].iloc[0].split("/")])
        dsh = np.abs(shapes[m] - rec).max()
        print(f"gate/shape {m}: re-solved vs fit-report shape max|dP| {dsh:.2e} (tol 2e-4)")
        ok &= dsh <= 2e-4
    P = calibration.shares_at_credit(test, np.full(len(test), REFERENCE_S))
    got = score(P, shapes)["rmse"]
    ref = pd.read_csv(COMPARISON_REGISTERED)
    ref = ref[ref["stratum"] == "all held-out"].set_index("model")["mean_RMSE_pp"]
    for m in MODELS:
        want, have = float(ref[m]), got[m]
        if m in CLOSED_FORM:
            passed = round(have, 4) == round(want, 4)
            rule = "exact at 4 dp (closed form)"
        else:
            passed = abs(have - want) <= ODE_TOL_PP
            rule = f"|delta| <= {ODE_TOL_PP:.0e} pp (ODE re-solve band)"
        print(f"gate/held-out {m}: per-race path {have:.6f} vs registered {want:.4f} "
              f"delta {have - want:+.6f}  {'ok' if passed else 'MISMATCH'}  [{rule}]")
        ok &= bool(passed)
    print("GATE PASSED" if ok else "GATE FAILED: stopping, nothing written")
    return bool(ok)


# ---------------------------------------------------------------------------
# one cell
# ---------------------------------------------------------------------------


def run_cell(cell: dict, train: pd.DataFrame, test: pd.DataFrame,
             cache: dict, skip_ode: bool, meta: dict) -> dict:
    c_tr, c_te = credit_for(cell, train), credit_for(cell, test)
    P_tr = calibration.shares_at_credit(train, c_tr)
    P_te = calibration.shares_at_credit(test, c_te)
    row = dict(cell)
    row.update({"S_train_mean_s": float(c_tr.mean()), "S_train_min_s": float(c_tr.min()),
                "S_train_max_s": float(c_tr.max()), "S_test_mean_s": float(c_te.mean()),
                "S_test_min_s": float(c_te.min()), "S_test_max_s": float(c_te.max())})
    values = {}
    fx = calibration.fit_beta_x(P_tr)
    values["M3"] = fx.value
    row.update({"beta_x": fx.value, "beta_x_loss_pp": fx.loss_pp, "beta_x_evals": fx.n_evals})
    if skip_ode:
        reg = registered_values()
        values["M4"], values["M2"] = reg["M4"], reg["M2"]
        row.update({"gamma": np.nan, "beta_E": np.nan, "skip_ode": True})
    else:
        fg = calibration.fit_gamma(P_tr)
        fe = calibration.fit_beta_E(P_tr)
        values["M4"], values["M2"] = fg.value, fe.value
        row.update({"gamma": fg.value, "gamma_loss_pp": fg.loss_pp, "gamma_evals": fg.n_evals,
                    "beta_E": fe.value, "beta_E_loss_pp": fe.loss_pp, "beta_E_evals": fe.n_evals,
                    "skip_ode": False})
    shapes = shapes_from_values(values, cache)
    sc = score(P_te, shapes)
    for m in MODELS:
        row[f"rmse_{m}_pp"] = round(sc["rmse"][m], 4)
    row.update({"best": sc["best"], "ranking": sc["ranking"],
                "sign_P4_minus_P1": sc["sign_P4_minus_P1"],
                "heldout_P_mean": "/".join(f"{x:.4f}" for x in sc["P_mean"])})
    row.update(meta)
    row["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return row


def append_row(path: str, row: dict) -> None:
    """Append one finished cell; a full row supersedes a smoke (skip_ode) row
    for the same cell, so a smoke run can never mask a real one."""
    df = pd.DataFrame([row])
    if os.path.exists(path):
        old = pd.read_csv(path)
        if "skip_ode" in old.columns and not row.get("skip_ode", False):
            old = old[~((old["cell"] == row["cell"]) & old["skip_ode"].astype(bool))]
        df = pd.concat([old, df], ignore_index=True)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False)


def refuse_frozen(path: str) -> None:
    """The one place this script writes results; anything else is refused."""
    if os.path.islink(path):
        raise SystemExit(f"refusing a symlink as output: {path}")
    ap = os.path.realpath(path)
    for frozen in (FITS_REGISTERED, COMPARISON_REGISTERED, M3_REFIT_CONSTANT,
                   "results/validation/report_v0_2.md",
                   "results/validation/holdout_start_sensitivity.csv",
                   "results/validation/h1_regression.csv",
                   "results/validation/pilot_model_comparison.csv",
                   "results/validation/pilot_start_sensitivity.csv",
                   "results/validation/fits_train_pilot.csv",
                   "results/validation/fits_beta_x_credit_sweep.csv",
                   "results/validation/pilot_report.md"):
        if ap == os.path.realpath(frozen):
            raise SystemExit(f"refusing to write a registered artifact: {path}")
    if "exploratory" not in os.path.basename(ap):
        raise SystemExit(f"output must carry 'exploratory' in its name: {path}")
    if os.path.exists(ap):
        head = pd.read_csv(ap, nrows=0)
        if "cell" not in head.columns or "exploratory" not in head.columns:
            raise SystemExit(f"{path} exists and is not this script's output; refusing")


# ---------------------------------------------------------------------------
# figure emp09
# ---------------------------------------------------------------------------


def figure(csv_path: str, fig_base: str, train: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    try:
        from src.visualization import use_style, SERIES, INK, INK_3
        use_style()
    except Exception:                                  # pragma: no cover
        SERIES, INK, INK_3 = ["C0", "C1", "C2", "C3"], "black", "gray"
    d = pd.read_csv(csv_path)
    v_mean = whole_race_velocity(train).mean()
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    i_rows = d[d["regime"] == "i"].sort_values("t15_s")
    if len(i_rows):
        ax.plot(i_rows["t15_s"], i_rows["beta_x"], "o-", color=SERIES[2],
                label="regime (i): constant t15, per-race S = 15/v − t15")
    ii_rows = d[d["regime"] == "ii"]
    if len(ii_rows):
        t_eff = float(ii_rows["k"].iloc[0]) * 15.0 / v_mean
        ax.plot([t_eff], ii_rows["beta_x"], "s", color=SERIES[3], ms=8,
                label=f"regime (ii): t15 = {float(ii_rows['k'].iloc[0]):.3f}·15/v "
                      f"(field-mean t15 {t_eff:.2f} s)")
    iii = d[d["regime"] == "iii"]
    if len(iii):
        t_ref = 15.0 / v_mean - REFERENCE_S
        ax.plot([t_ref], iii["beta_x"], "D", color=INK, ms=8,
                label=f"reference: constant S = 1.80 s (≡ t15 {t_ref:.2f} s at field-mean v)")
    if os.path.exists(M3_REFIT_CONSTANT):
        c = pd.read_csv(M3_REFIT_CONSTANT)
        t_axis = 15.0 / v_mean - c["offset_s"]     # constant S ↔ t15 at the field-mean v
        ax.plot(t_axis, c["beta_x"], "--", color=INK_3, lw=1.2,
                label="registered constant-S sweep (§7), mapped to t15 at field-mean v")
    ax.set_xlabel("t15 (s): measured time to 15 m")
    ax.set_ylabel("fitted beta_x (training rows)")
    ax.set_title("EXPLORATORY — per-race start credit: beta_x across the t15 band")
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    os.makedirs(os.path.dirname(fig_base), exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{fig_base}.{ext}", dpi=200)
    plt.close(fig)
    print(f"wrote {fig_base}.png/.pdf")


# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processed", default=PROCESSED)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--gate-only", action="store_true",
                    help="run the gate and the reference cell only")
    ap.add_argument("--skip-ode", action="store_true",
                    help="fit beta_x only; rows marked skip_ode=True (smoke tests)")
    ap.add_argument("--cells", nargs="*", default=None,
                    help="subset of cell ids to run (default: all not yet in the CSV)")
    ap.add_argument("--figure", action="store_true", help="render emp09 from the CSV and exit")
    args = ap.parse_args()
    refuse_frozen(args.out)
    if args.skip_ode and os.path.realpath(args.out) == os.path.realpath(OUT):
        raise SystemExit("--skip-ode is for smoke tests; point --out at a scratch path, "
                         "not the deliverable")
    if args.cells is not None:
        valid = {c["cell"] for c in cells()}
        unknown = set(args.cells) - valid
        if unknown or not args.cells:
            raise SystemExit(f"unknown cell ids {sorted(unknown)}; valid: {sorted(valid)}")

    df = pd.read_csv(args.processed, low_memory=False)
    ok = df[df["usable"] == True].copy()  # noqa: E712
    _, test = data_split.split_by_swimmer(ok, seed=data_split.DEFAULT_SEED)
    train, tmeta = calibration.training_frame(args.processed)
    calibration.assert_no_test_rows(train, args.processed)

    if args.figure:
        figure(args.out, FIG, train)
        return

    cache: dict = {}
    print(f"training rows {len(train)} / held-out rows {len(test)} (seed "
          f"{tmeta['seed']}); EXPLORATORY, test set already open")
    if not gate(train, test, cache):
        raise SystemExit(2)

    meta = {"exploratory": True, "dataset": "pilot-v0.2", "seed": tmeta["seed"],
            "n_train_races": len(train), "n_test_races": len(test),
            "loss": "mean per-race RMSE of split proportions (pp), validation_plan §3"}
    done = set()
    if os.path.exists(args.out):
        prev = pd.read_csv(args.out)
        smoke = prev["skip_ode"].astype(bool) if "skip_ode" in prev.columns else pd.Series(False, index=prev.index)
        # a smoke row only counts as done for another smoke run
        done = set(prev.loc[~smoke | bool(args.skip_ode), "cell"])
    todo = [c for c in cells() if c["cell"] not in done]
    if args.cells is not None:
        todo = [c for c in todo if c["cell"] in set(args.cells)]
    if args.gate_only:
        todo = [c for c in todo if c["regime"] == "iii"]
    print(f"{len(done)} cells already in {args.out}; {len(todo)} to run")
    for cell in todo:
        print(f"--- {cell['cell']} ---", flush=True)
        row = run_cell(cell, train, test, cache, args.skip_ode, meta)
        append_row(args.out, row)
        print(f"  beta_x {row['beta_x']:.4f}  gamma {row.get('gamma', float('nan')):.4f}  "
              f"beta_E {row.get('beta_E', float('nan')):.4f}  best {row['best']}  "
              f"ranking {row['ranking']}  sign {row['sign_P4_minus_P1']}", flush=True)


if __name__ == "__main__":
    main()
