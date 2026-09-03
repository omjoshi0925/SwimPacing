#!/usr/bin/env python3
"""
The registered held-out model comparison and H1 analysis on the frozen
pilot-v0.2 dataset (validation_plan §3-§8).

This script is the ONE place the test set is opened. It reads the fitted
fatigue parameters from the registered training-side calibration
(results/model_calibration/fits_train_v0_2.csv), evaluates every model on
the held-out swimmers under the registered split (seed 20260829), applies
the §4 win criteria mechanically, sweeps the §7 start-credit band with the
fitted parameters held fixed, runs the §8 deviation-vs-performance
regression, and writes:

    results/validation/model_comparison.csv          (§11)
    results/validation/holdout_start_sensitivity.csv (§7)
    results/validation/h1_regression.csv             (§8)
    results/validation/report_v0_2.md
    figures/empirical/emp06_holdout_comparison.(png|pdf)
    figures/empirical/emp07_start_band_holdout.(png|pdf)
    figures/empirical/emp08_deviation_vs_performance.(png|pdf)

    python -m scripts.evaluate_holdout

Nothing in here is tuned to the test set: the fitted values come from the
training-side report, the credit band is the registered one, and the
criteria are quoted from the plan. Re-running the script after changing
anything downstream of the test set turns the result exploratory (§5).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import calibration, data_split, preprocessing, stats  # noqa: E402
from src.parameters import SCY_200, MODELS  # noqa: E402
from src.visualization import (SERIES, MARKERS, INK, INK_2, INK_3,  # noqa: E402
                               use_style, _finish)

PROCESSED = "data/processed/200_free_scy_processed.csv"
FITS = "results/model_calibration/fits_train_v0_2.csv"
OUT_RES = "results/validation"
OUT_FIG = "figures/empirical"
MODEL_COLOR = {"M0": SERIES[0], "M1": SERIES[6], "M2": SERIES[1],
               "M3": SERIES[2], "M4": SERIES[3]}
KEY = {"M0": "M0_constant_economy", "M1": "M1_oxygen_kinetics",
       "M2": "M2_reserve_fatigue", "M3": "M3_position_fatigue",
       "M4": "M4_velocity_ceiling"}
PARAM = {"M2": "beta_E", "M3": "beta_x", "M4": "gamma"}
BAND = np.round(np.arange(1.2, 3.41, 0.2), 2)
#: UTC time the registered test set was first opened by this script. Later
#: runs re-execute the same registered evaluation (plus any post-hoc
#: supplements, which are labelled as such); they do not re-open anything.
FIRST_OPENED = "2026-09-03T02:00:12Z"
#: Post-hoc H1 supplement (added after the first run, exploratory): restrict
#: the pre-race PB to one set within this many days, because the three
#: largest "improvements" in the registered run were against PBs swum four
#: years earlier at age 13-14, which are not expectations.
PB_MAX_AGE_DAYS = 365


# ---------------------------------------------------------------------------
# fitted shapes
# ---------------------------------------------------------------------------


def fitted_shapes(fits_csv: str, models: list) -> "tuple[dict, dict]":
    """
    Raced-space shape per model at the REGISTERED fitted value. M0/M1 have
    no free parameter (their shape is the theorem's even split). M3 is
    closed form; M2/M4 are re-solved once at the fitted value and checked
    against the shape recorded in the fit report.
    """
    fits = pd.read_csv(fits_csv) if os.path.exists(fits_csv) else pd.DataFrame()
    if len(fits) and bool(fits["exploratory"].astype(bool).any()):
        raise SystemExit(f"{fits_csv} contains exploratory rows; the held-out "
                         "evaluation only accepts the registered calibration")
    base = preprocessing.model_predictions(SCY_200)
    shapes, values = {}, {}
    cache: dict = {}
    for m in models:
        if m in ("M0", "M1"):
            shapes[m] = np.asarray(base[KEY[m]], dtype=float)
            continue
        row = fits[fits["model"] == KEY[m]]
        if row.empty:
            raise SystemExit(f"no registered fit for {m} in {fits_csv}; run "
                             "scripts.fit_models --registered first")
        v = float(row["fitted_value"].iloc[0])
        values[m] = v
        if m == "M3":
            shapes[m] = calibration.m3_shape(v)
        else:
            shapes[m] = calibration._ode_shape(KEY[m], PARAM[m], v, SCY_200, cache)
            rec = np.array([float(x) for x in row["shape"].iloc[0].split("/")])
            if np.abs(shapes[m] - rec).max() > 2e-4:
                raise SystemExit(f"{m}: re-solved shape {shapes[m]} disagrees "
                                 f"with the fit report {rec}")
    return shapes, values


# ---------------------------------------------------------------------------
# held-out comparison
# ---------------------------------------------------------------------------


def compare(test: pd.DataFrame, shapes: dict, n_boot: int, label: str) -> dict:
    P = calibration.observed_shares(test)
    clusters = test["swimmer_id"].to_numpy()
    models = list(shapes)
    R = np.column_stack([stats.race_rmse_pp(P, shapes[m]) for m in models])
    A = np.column_stack([stats.race_mae_pp(P, shapes[m]) for m in models])
    boot = stats.cluster_bootstrap(R, clusters, n_boot=n_boot)
    mean_rmse = {m: float(boot["estimate"][i]) for i, m in enumerate(models)}
    best = min(mean_rmse, key=mean_rmse.get)
    ib = models.index(best)
    diff_ci = {}
    for i, m in enumerate(models):
        if m == best:
            continue
        d = boot["draws"][:, i] - boot["draws"][:, ib]
        diff_ci[m] = (float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975)))
    P_mean = P.mean(axis=0)
    crit = stats.apply_win_criteria(mean_rmse, diff_ci, P_mean, shapes)
    # secondary metrics
    lap = test[[f"split{i}_time" for i in range(1, 5)]].to_numpy(dtype=float)
    lap1c = lap[:, 0] + SCY_200.start_credit_s
    drop12 = lap[:, 1] - lap1c
    drop34 = lap[:, 3] - lap[:, 2]
    dboot = stats.cluster_bootstrap(np.column_stack([drop12, drop34]), clusters,
                                    n_boot=n_boot)
    rows = []
    for i, m in enumerate(models):
        s = shapes[m]
        rows.append({
            "model": m, "registry_key": KEY[m],
            "mean_RMSE_pp": round(mean_rmse[m], 4),
            "RMSE_ci_lo": round(float(boot["lo"][i]), 4),
            "RMSE_ci_hi": round(float(boot["hi"][i]), 4),
            "mean_MAE_pp": round(float(A[:, i].mean()), 4),
            "diff_vs_best_pp": (0.0 if m == best
                                else round(mean_rmse[m] - mean_rmse[best], 4)),
            "diff_ci_lo": (np.nan if m == best else round(diff_ci[m][0], 4)),
            "diff_ci_hi": (np.nan if m == best else round(diff_ci[m][1], 4)),
            "signed_err_P1_pp": round(float((P_mean[0] - s[0]) * 100), 3),
            "signed_err_P2_pp": round(float((P_mean[1] - s[1]) * 100), 3),
            "signed_err_P3_pp": round(float((P_mean[2] - s[2]) * 100), 3),
            "signed_err_P4_pp": round(float((P_mean[3] - s[3]) * 100), 3),
            "shape": "/".join(f"{x:.4f}" for x in s),
            "pred_sign_P4_minus_P1": int(np.sign(np.round(s[3] - s[0], 6))),
            "n_races_best": int((R.argmin(axis=1) == i).sum()),
            "stratum": label,
        })
    table = pd.DataFrame(rows)
    return {"table": table, "criteria": crit, "P_mean": P_mean, "R": R,
            "n_races": int(len(test)), "n_swimmers": int(test["swimmer_id"].nunique()),
            "drop12": dboot, "drop34_index": 1,
            "obs_ci": stats.cluster_bootstrap(P * 100, clusters, n_boot=n_boot)}


def start_band(test: pd.DataFrame, shapes: dict) -> pd.DataFrame:
    """§7: held-out ranking across the credit band, fitted parameters fixed."""
    rows = []
    for off in BAND:
        P = calibration.shares_at_credit(test, float(off))
        row = {"offset_s": float(off)}
        for m in shapes:
            row[m] = round(float(stats.race_rmse_pp(P, shapes[m]).mean()), 4)
        row["best"] = min(shapes, key=lambda m: row[m])
        row["sign_P4_minus_P1"] = int(np.sign(np.round(P.mean(axis=0)[3]
                                                       - P.mean(axis=0)[0], 6)))
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# H1
# ---------------------------------------------------------------------------


def h1(ok: pd.DataFrame, shapes: dict, models: list,
       all_rows: pd.DataFrame) -> pd.DataFrame:
    """
    §8 on every usable race with a pre-race PB, D_j measured against each
    model's fitted optimum (the best-supported model is the registered
    predictor; the others are reported for completeness).
    """
    d = ok[~ok["flag_no_pb"]].copy()
    P = calibration.observed_shares(d)
    d["I"] = (d["pre_race_pb_s"] - d["final_time_s"]) / d["pre_race_pb_s"] * 100
    d["pb_age_days"] = pb_age_days(d, all_rows)
    out = []
    for m in models:
        d[f"D_{m}"] = stats.race_rmse_pp(P, shapes[m])
        res = stats.h1_regression(d, f"D_{m}", "I")
        res["model"] = m
        res["stratum"] = "registered: every race with a pre-race PB"
        out.append(res)
        recent = d[d["pb_age_days"] <= PB_MAX_AGE_DAYS]
        res = stats.h1_regression(recent, f"D_{m}", "I")
        res["model"] = m
        res["stratum"] = f"post-hoc supplement: PB within {PB_MAX_AGE_DAYS} days"
        out.append(res)
    frame = pd.DataFrame(out)
    frame["I_definition"] = "(pre_race_pb - final) / pre_race_pb, percent"
    return frame, d


def pb_age_days(d: pd.DataFrame, all_rows: pd.DataFrame) -> pd.Series:
    """Days between each race and the earlier row that set its pre-race PB."""
    rows = all_rows.copy()
    rows["_d"] = pd.to_datetime(rows["meet_date"])
    out = pd.Series(np.nan, index=d.index)
    for idx, r in d.iterrows():
        day = pd.Timestamp(r["meet_date"])
        prev = rows[(rows["swimmer_id"] == r["swimmer_id"]) & (rows["_d"] < day)]
        src = prev[np.isclose(prev["final_time_s"], r["pre_race_pb_s"])]
        if len(src):
            out.loc[idx] = (day - src["_d"].max()).days
    return out


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------


def fig_comparison(res: dict, shapes: dict) -> str:
    use_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.6))
    t = res["table"]
    x = np.arange(len(t))
    ax1.bar(x, t["mean_RMSE_pp"], color=[MODEL_COLOR[m] for m in t["model"]],
            width=0.62, edgecolor="#fcfcfb")
    ax1.errorbar(x, t["mean_RMSE_pp"],
                 yerr=[t["mean_RMSE_pp"] - t["RMSE_ci_lo"],
                       t["RMSE_ci_hi"] - t["mean_RMSE_pp"]],
                 fmt="none", ecolor=INK, elinewidth=1.2, capsize=3)
    ax1.set_xticks(x, t["model"])
    ax1.set_ylabel("held-out mean RMSE  (pp)")
    ax1.set_title(f"Held-out accuracy, n = {res['n_races']} races / "
                  f"{res['n_swimmers']} swimmers", loc="left", pad=8)
    laps = np.arange(1, 5)
    P_mean = res["P_mean"] * 100
    ci = res["obs_ci"]
    ax2.errorbar(laps, P_mean, yerr=[P_mean - ci["lo"], ci["hi"] - P_mean],
                 fmt="o", color=INK, capsize=3, label="observed mean (95% CI)",
                 zorder=5)
    for m, s in shapes.items():
        if m == "M1":
            continue
        ax2.plot(laps, np.asarray(s) * 100, color=MODEL_COLOR[m], lw=1.7,
                 marker=MARKERS[list(shapes).index(m)], markersize=4.5,
                 markeredgecolor="#fcfcfb", label="M0 / M1" if m == "M0" else m)
    ax2.set_xticks(laps, [f"lap {i}" for i in laps])
    ax2.set_ylabel("share of race time  (%)")
    ax2.set_title("Mean held-out profile vs fitted shapes", loc="left", pad=8)
    ax2.legend(fontsize=8.5)
    note = ("Left: mean per-race RMSE of free-swimming-equivalent split shares "
            "against each model at its training-fitted parameter, with swimmer-"
            "cluster bootstrap 95% CIs. Right: the held-out mean profile with "
            "CIs against the same fitted shapes. Start credit 1.80 s.")
    return _finish(fig, (ax1, ax2), "emp06_holdout_comparison", note, OUT_FIG)


def fig_band(sens: pd.DataFrame, shapes: dict) -> str:
    use_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for m in shapes:
        if m == "M1":
            continue
        ax.plot(sens["offset_s"], sens[m], color=MODEL_COLOR[m], lw=1.9,
                marker=MARKERS[list(shapes).index(m)], markersize=5,
                markeredgecolor="#fcfcfb", label="M0 / M1" if m == "M0" else m)
    ax.axvline(SCY_200.start_credit_s, color=INK_3, ls="--", lw=1.0)
    ax.set_xlabel("start credit applied to lap 1  (s)")
    ax.set_ylabel("held-out mean RMSE  (pp)")
    ax.set_title("Held-out ranking across the registered start-credit band",
                 loc="left", pad=8)
    ax.legend(fontsize=8.5)
    note = ("Fitted parameters held fixed at their 1.80 s training values while "
            "the credit applied to the held-out data sweeps the registered 1.2-"
            "3.4 s band (validation_plan §7). A crossing inside the band means "
            "the ranking depends on the start credit.")
    return _finish(fig, ax, "emp07_start_band_holdout", note, OUT_FIG)


def fig_h1(d: pd.DataFrame, m: str, reg: pd.Series) -> str:
    use_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(d[f"D_{m}"], d["I"], s=22, color=SERIES[0], alpha=0.75,
               edgecolor="#fcfcfb", linewidth=0.5)
    ax.axhline(0, color=INK_3, lw=0.8)
    xs = np.linspace(d[f"D_{m}"].min(), d[f"D_{m}"].max(), 100)
    xc = xs - reg["D_center_pp"]
    ax.plot(xs, reg["Intercept_est"] + reg["D_est"] * xc + reg["D2_est"] * xc ** 2,
            color=INK, lw=1.8)
    ax.set_xlabel(f"deviation from the {m} optimum  (RMSE, pp)")
    ax.set_ylabel("improvement on pre-race PB  (%)")
    ax.set_title(f"Deviation vs performance, n = {int(reg['n_races'])} races / "
                 f"{int(reg['n_swimmers'])} swimmers", loc="left", pad=8)
    note = (f"validation_plan §8: I = (PB - T)/PB against D = RMSE from the fitted "
            f"{m} shape, quadratic fit ({reg['method']}). b1 = {reg['D_est']:.3f} "
            f"[{reg['D_lo']:.3f}, {reg['D_hi']:.3f}], b2 = {reg['D2_est']:.3f} "
            f"[{reg['D2_lo']:.3f}, {reg['D2_hi']:.3f}] (% per pp, % per pp^2).")
    return _finish(fig, ax, "emp08_deviation_vs_performance", note, OUT_FIG)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def write_report(path, meta, values, shapes, res, res_pub, sens, sens_m3,
                 h1_frame, funnel):
    t = res["table"]
    c = res["criteria"]
    L = []
    L.append("# Registered held-out evaluation — pilot-v0.2\n")
    L.append(f"Generated {meta['generated_utc']}. Dataset pilot-v0.2 (frozen "
             f"2026-09-03). Registered split seed {meta['seed']}: training "
             f"{meta['n_train_races']} races / {meta['n_train_swimmers']} "
             f"swimmers, held-out {meta['n_test_races']} races / "
             f"{meta['n_test_swimmers']} swimmers. **The test set was first "
             f"opened by this script at {FIRST_OPENED}**; this run re-executes "
             f"the same registered evaluation (post-hoc supplements are "
             f"labelled). Start credit "
             f"{SCY_200.start_credit_s:.2f} s (elite-anchored; validation_plan §7).\n")
    L.append("## Exclusion funnel (validation_plan §10)\n")
    L.append("| step | rows |\n|---|---|")
    for k, v in funnel.items():
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## Registered calibration (training side only)\n")
    L.append("| model | parameter | fitted | registry | bounds | training loss (pp) |\n|---|---|---|---|---|---|")
    fits = pd.read_csv(FITS)
    for _, r in fits.iterrows():
        if isinstance(r["param"], str) and r["param"]:
            L.append(f"| {r['model']} | {r['param']} | {r['fitted_value']:.4f} | "
                     f"{r['registry_value']:.2f} | {r['bounds']} | {r['train_loss_pp']:.4f} |")
        else:
            L.append(f"| {r['model']} | — | — | — | — | {r['train_loss_pp']:.4f} |")
    L.append("")
    L.append("## Held-out comparison (§3, §4)\n")
    L.append("| model | mean RMSE (pp) | 95% CI | MAE (pp) | Δ vs best (pp) | Δ 95% CI | sign(P4−P1) | best in n races |\n|---|---|---|---|---|---|---|---|")
    for _, r in t.iterrows():
        dci = ("—" if np.isnan(r["diff_ci_lo"])
               else f"[{r['diff_ci_lo']:+.3f}, {r['diff_ci_hi']:+.3f}]")
        L.append(f"| {r['model']} | {r['mean_RMSE_pp']:.3f} | "
                 f"[{r['RMSE_ci_lo']:.3f}, {r['RMSE_ci_hi']:.3f}] | "
                 f"{r['mean_MAE_pp']:.3f} | {r['diff_vs_best_pp']:+.3f} | {dci} | "
                 f"{r['pred_sign_P4_minus_P1']:+d} | {r['n_races_best']} |")
    L.append("")
    P = res["P_mean"] * 100
    ci = res["obs_ci"]
    L.append("Observed held-out mean shares (free-swimming equivalent, %): "
             + ", ".join(f"P{i+1} = {P[i]:.2f} [{ci['lo'][i]:.2f}, {ci['hi'][i]:.2f}]"
                         for i in range(4)) + ".")
    d12, d34 = res["drop12"]["estimate"]
    lo, hi = res["drop12"]["lo"], res["drop12"]["hi"]
    L.append(f"Discriminating statistic: drop 1→2 = {d12:+.2f} s [{lo[0]:+.2f}, "
             f"{hi[0]:+.2f}], drop 3→4 = {d34:+.2f} s [{lo[1]:+.2f}, {hi[1]:+.2f}] "
             f"(after adding the start credit to lap 1).\n")
    L.append("### §4 criteria, applied mechanically\n")
    L.append(f"- Observed sign of P4 − P1: {c['observed_sign_P4_minus_P1']:+d}. "
             f"Models with the matching sign: {', '.join(c['shape_matching_models'])}. "
             f"Shape winner: **{c['shape_winner'] or 'none (more than one model class matches)'}**.")
    L.append(f"- Lowest held-out RMSE: {c['lowest_rmse_model']}. Accuracy winner "
             f"(CI of every pairwise difference excludes zero): "
             f"**{c['accuracy_winner'] or 'none'}**.")
    L.append(f"- Registered conclusion: **{c['conclusion']}**.\n")
    L.append("## Start-credit band on the held-out set (§7)\n")
    L.append("Fitted parameters held at their 1.80 s training values; only the "
             "credit applied to the held-out data moves.\n")
    L.append("| credit (s) | " + " | ".join(shapes) + " | best | sign(P4−P1) |")
    L.append("|---|" + "---|" * (len(shapes) + 2))
    for _, r in sens.iterrows():
        L.append(f"| {r['offset_s']:.1f} | " + " | ".join(f"{r[m]:.3f}" for m in shapes)
                 + f" | {r['best']} | {r['sign_P4_minus_P1']:+d} |")
    bests = sens["best"].tolist()
    stable = len(set(bests)) == 1
    L.append("")
    L.append(("Ranking stable across the band: **yes**" if stable else
              "Ranking changes inside the band: **" + " → ".join(dict.fromkeys(bests))
              + "**. Per §7 item 3, the data cannot distinguish the surviving "
              "models given start uncertainty") + ".\n")
    L.append("### Supplementary: M3 refitted at each credit (training side), scored held-out\n")
    L.append("| credit (s) | beta_x (train) | held-out RMSE M3 (pp) | held-out RMSE M0 (pp) |\n|---|---|---|---|")
    for _, r in sens_m3.iterrows():
        L.append(f"| {r['offset_s']:.1f} | {r['beta_x']:.4f} | {r['M3_refit']:.3f} | {r['M0']:.3f} |")
    L.append("")
    L.append("## Published-age stratum (club-linked rows removed)\n")
    tp = res_pub["table"]
    L.append(f"Held-out races {res_pub['n_races']} / swimmers {res_pub['n_swimmers']}. "
             + "; ".join(f"{r['model']} {r['mean_RMSE_pp']:.3f} "
                         f"[{r['RMSE_ci_lo']:.3f}, {r['RMSE_ci_hi']:.3f}]"
                         for _, r in tp.iterrows())
             + f". Conclusion: {res_pub['criteria']['conclusion']}.\n")
    L.append("## H1: deviation vs performance (§8)\n")
    L.append(f"Races with a pre-race PB: {int(h1_frame['n_races'].iloc[0])} "
             f"({int(h1_frame['n_swimmers'].iloc[0])} swimmers; all usable races, "
             "not only held-out ones — H1 is not a model-selection step, and the "
             "deviation D uses the training-fitted shapes). I = (PB − T)/PB in "
             "percent; D in pp, centered.\n")
    L.append("| stratum | D vs | n races / swimmers | method | b1 (% per pp) | 95% CI | b2 (% per pp²) | 95% CI | RE var | resid var |\n|---|---|---|---|---|---|---|---|---|---|")
    for _, r in h1_frame.iterrows():
        L.append(f"| {r['stratum']} | {r['model']} | {int(r['n_races'])} / {int(r['n_swimmers'])} | "
                 f"{'mixed' if r['used_mixed_effects'] else 'OLS-cluster'} | "
                 f"{r['D_est']:+.3f} | [{r['D_lo']:+.3f}, {r['D_hi']:+.3f}] | "
                 f"{r['D2_est']:+.3f} | [{r['D2_lo']:+.3f}, {r['D2_hi']:+.3f}] | "
                 f"{r['random_intercept_var']:.3f} | {r['residual_var']:.3f} |")
    L.append("")
    L.append(f"The post-hoc supplement (added after the first run; exploratory, "
             f"not registered) keeps only races whose pre-race PB was set within "
             f"{PB_MAX_AGE_DAYS} days: in the registered set the three largest "
             f"improvements (29%, 14%, 13%) were measured against PBs swum four "
             f"years earlier, at ages 13-14, which are not expectations.\n")
    L.append("H1 is supported only if b1 < 0 with a CI excluding zero (closer to "
             "the optimum → better relative to expectation) and the curvature is "
             "consistent with a penalty; otherwise the registered null is reported "
             "as a null (§9).\n")
    L.append("## Files\n")
    L.append("`results/validation/model_comparison.csv`, "
             "`results/validation/holdout_start_sensitivity.csv`, "
             "`results/validation/h1_regression.csv`, figures "
             "`figures/empirical/emp06-08`.\n")
    with open(path, "w") as f:
        f.write("\n".join(L))
    return path


# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="+", default=["M0", "M1", "M2", "M3", "M4"])
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--processed", default=PROCESSED)
    ap.add_argument("--dry-run", action="store_true",
                    help="exercise the code path WITHOUT opening the test set: "
                         "the registered training rows are re-split by swimmer "
                         "with another seed and outputs go to /tmp/holdout_dry")
    args = ap.parse_args()

    df = pd.read_csv(args.processed, low_memory=False)
    ok = df[df["usable"] == True].copy()  # noqa: E712
    train, test = data_split.split_by_swimmer(ok, seed=data_split.DEFAULT_SEED)
    if args.dry_run:
        global OUT_RES, OUT_FIG
        OUT_RES = OUT_FIG = "/tmp/holdout_dry"
        ok = train.drop(columns=["split"])
        train, test = data_split.split_by_swimmer(ok, seed=1)
        print("DRY RUN on a re-split of the training rows; test set NOT opened")
    shapes, values = fitted_shapes(FITS, args.models)
    print("fitted values:", values)
    print("shapes:", {m: np.round(s, 4).tolist() for m, s in shapes.items()})

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not args.dry_run:
        calibration.assert_no_test_rows(train, args.processed)
    meta = {"generated_utc": stamp + (" (DRY RUN)" if args.dry_run else ""), "seed": data_split.DEFAULT_SEED,
            "n_train_races": len(train), "n_train_swimmers": train["swimmer_id"].nunique(),
            "n_test_races": len(test), "n_test_swimmers": test["swimmer_id"].nunique()}
    print(f"{'dry-run pseudo-test' if args.dry_run else 'TEST SET OPENED'} "
          f"{stamp}: {len(test)} races / {test['swimmer_id'].nunique()} swimmers")

    res = compare(test, shapes, args.n_boot, "all held-out")
    print(res["table"][["model", "mean_RMSE_pp", "RMSE_ci_lo", "RMSE_ci_hi",
                        "diff_vs_best_pp", "diff_ci_lo", "diff_ci_hi"]].to_string(index=False))
    print(res["criteria"]["conclusion"])
    res_pub = compare(test[test["age_source"] == "published"], shapes,
                      args.n_boot, "published-age held-out")

    sens = start_band(test, shapes)
    # supplementary M3 refit per credit on the training side (closed form)
    rows = []
    for off in BAND:
        fit = calibration.fit_beta_x(calibration.shares_at_credit(train, float(off)))
        Pt = calibration.shares_at_credit(test, float(off))
        rows.append({"offset_s": float(off), "beta_x": fit.value,
                     "M3_refit": float(stats.race_rmse_pp(Pt, fit.shape).mean()),
                     "M0": float(stats.race_rmse_pp(Pt, shapes["M0"]).mean())})
    sens_m3 = pd.DataFrame(rows)

    h1_frame, h1_data = h1(ok, shapes, [m for m in args.models if m != "M1"], df)
    best = res["criteria"]["lowest_rmse_model"]
    best_h1 = best if best != "M1" else "M0"

    keep = pd.Series(True, index=df.index)
    funnel = {"raw rows": int(keep.sum())}
    for label, flag in [("with complete cumulative splits", "flag_missing_splits"),
                        ("… monotonic", "flag_non_monotonic"),
                        ("… |split_200 − final| ≤ 0.05 s", "flag_time_mismatch"),
                        ("… every 50 within 0.5-2.0× race mean", "flag_implausible_split"),
                        ("… not a duplicate", "flag_duplicate"),
                        ("… SCY", "flag_course_mismatch"),
                        ("… male 15-18 (published or club-linked age)", "flag_age_out_of_scope")]:
        keep &= ~df[flag].astype(bool)
        funnel[label] = int(keep.sum())
    funnel["usable (shape analysis)"] = int((df["usable"] == True).sum())  # noqa: E712
    funnel["usable with pre-race PB (H1)"] = int(((df["usable"] == True) & ~df["flag_no_pb"]).sum())  # noqa: E712

    os.makedirs(OUT_RES, exist_ok=True)
    table = pd.concat([res["table"], res_pub["table"]], ignore_index=True)
    for k, v in meta.items():
        table[k] = v
    table["fitted_values"] = json.dumps(values)
    table.to_csv(os.path.join(OUT_RES, "model_comparison.csv"), index=False)
    sens.to_csv(os.path.join(OUT_RES, "holdout_start_sensitivity.csv"), index=False)
    sens_m3.to_csv(os.path.join(OUT_RES, "holdout_start_sensitivity_m3_refit.csv"), index=False)
    h1_frame.to_csv(os.path.join(OUT_RES, "h1_regression.csv"), index=False)

    made = [fig_comparison(res, shapes), fig_band(sens, shapes),
            fig_h1(h1_data, best_h1, h1_frame[(h1_frame["model"] == best_h1)
                                             & h1_frame["stratum"].str.startswith("registered")].iloc[0])]
    report = write_report(os.path.join(OUT_RES, "report_v0_2.md"), meta, values,
                          shapes, res, res_pub, sens, sens_m3, h1_frame, funnel)
    for m in made + [report]:
        print("wrote", m)


if __name__ == "__main__":
    main()
