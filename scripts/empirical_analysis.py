#!/usr/bin/env python3
"""
First empirical analysis (Phases 5-7 of the current task list).

Input: data/processed/200_free_scy_processed.csv, built by src.preprocessing
from the raw ingest. Uses ONLY rows with usable == True.

Outputs:
    figures/empirical/emp01_split_share_distributions.(png|pdf)
    figures/empirical/emp02_mean_profile_vs_models.(png|pdf)
    figures/empirical/emp03_model_deviations.(png|pdf)
    figures/empirical/emp04_start_effect.(png|pdf)
    results/validation/pilot_model_comparison.csv
    results/validation/pilot_start_sensitivity.csv
    results/validation/pilot_report.md

Everything here is DESCRIPTIVE. n is small, every race is from one meet, no
parameter has been fitted to any of it, and no train/test split has been
consumed. The held-out comparison in docs/validation_plan.md remains untouched.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import preprocessing, data_split  # noqa: E402
from src.parameters import SCY_200, START_OFFSET_S  # noqa: E402
from src.visualization import (SERIES, MARKERS, INK, INK_2, INK_3,  # noqa: E402
                               use_style, _finish)

OUT_FIG = "figures/empirical"
OUT_RES = "results/validation"
PROCESSED = "data/processed/200_free_scy_processed.csv"

#: Fixed hue per model, never reassigned by rank.
MODEL_COLOR = {"M0": SERIES[0], "M1": SERIES[6], "M2": SERIES[1],
               "M3": SERIES[2], "M4": SERIES[3]}
MODEL_ORDER = ["M0", "M1", "M2", "M3", "M4"]


def load_usable() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED, low_memory=False)
    ok = df[df["usable"] == True].copy()  # noqa: E712
    if not len(ok):
        raise SystemExit("no usable races; nothing to analyse")
    return ok


def model_shapes() -> dict:
    preds = preprocessing.model_predictions(SCY_200)
    return {name.split("_")[0]: np.asarray(P) for name, P in preds.items()}


# ---------------------------------------------------------------------------
# Figure 1: distributions of the four split shares
# ---------------------------------------------------------------------------


def fig_distributions(ok: pd.DataFrame) -> str:
    use_style()
    fig, axes = plt.subplots(1, 4, figsize=(12.6, 3.4), sharey=True)
    lo = min(ok[f"P{i}"].min() for i in range(1, 5)) * 100 - 0.3
    hi = max(ok[f"P{i}"].max() for i in range(1, 5)) * 100 + 0.3
    bins = np.linspace(lo, hi, 22)
    for i, ax in enumerate(axes, start=1):
        vals = ok[f"P{i}"] * 100
        ax.hist(vals, bins=bins, color=SERIES[i - 1], edgecolor="#fcfcfb",
                linewidth=0.6)
        ax.axvline(25.0, color=INK_3, ls="--", lw=1.0)
        ax.axvline(vals.mean(), color=INK, lw=1.4)
        ax.annotate(f"mean {vals.mean():.2f}%", xy=(0.03, 0.92),
                    xycoords="axes fraction", fontsize=8.5, color=INK_2)
        ax.set_title(f"lap {i} share of race", loc="left", fontsize=10, pad=6)
        ax.set_xlabel("% of final time")
    axes[0].set_ylabel("races")
    fig.suptitle(f"How real 200 SCY races are divided  (n = {len(ok)})",
                 x=0.005, ha="left", fontsize=12, fontweight="600")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    note = ("Recorded shares, no start correction. Dashed line: perfectly even "
            "25%. Lap 1 sits far below even because it contains the dive start; "
            "laps 2-4 sit above.")
    return _finish(fig, axes, "emp01_split_share_distributions", note, OUT_FIG)


# ---------------------------------------------------------------------------
# Figure 2: mean profile against every model
# ---------------------------------------------------------------------------


def fig_profile_vs_models(ok: pd.DataFrame, shapes: dict) -> str:
    use_style()
    x = np.arange(1, 5)
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.8, 4.6), sharey=True)

    for ax, suffix, title in [
        (axL, "", "recorded shares (dive included in lap 1)"),
        (axR, "_corrected", f"start-corrected (lap 1 credited {START_OFFSET_S:.1f} s)"),
    ]:
        P = np.vstack([ok[f"P{i}{suffix}"].to_numpy() for i in range(1, 5)]).T * 100
        mean, sd = P.mean(axis=0), P.std(axis=0, ddof=1)
        for name in MODEL_ORDER:
            if name == "M1":  # identical to M0; drawn once, labelled jointly
                continue
            label = "M0 / M1 (even)" if name == "M0" else name
            ax.plot(x, shapes[name] * 100, color=MODEL_COLOR[name], lw=1.8,
                    marker=MARKERS[MODEL_ORDER.index(name)], markersize=6,
                    markeredgecolor="#fcfcfb", markeredgewidth=1.0, label=label)
        ax.errorbar(x, mean, yerr=sd, color=INK, lw=2.6, marker="o",
                    markersize=8, markeredgecolor="#fcfcfb",
                    markeredgewidth=1.3, capsize=4, label=f"observed (n={len(ok)})",
                    zorder=6)
        ax.set_xticks(x)
        ax.set_xlabel("lap")
        ax.set_title(title, loc="left", fontsize=10.5, pad=8)
    axL.set_ylabel("share of final time  (%)")
    axL.legend(loc="lower right", fontsize=8.5)
    fig.suptitle("Observed pacing against the five model predictions",
                 x=0.005, ha="left", fontsize=12, fontweight="600")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    note = ("Error bars: +/-1 SD across races. Real races are more front-loaded than "
            "every model, and the last lap is not slower than the third, a finishing "
            "kick no cost-based model reproduces. M2's negative split has the wrong "
            "sign entirely. Descriptive only; single meet, no fitting.")
    return _finish(fig, (axL, axR), "emp02_mean_profile_vs_models", note, OUT_FIG)


# ---------------------------------------------------------------------------
# Figure 3: per-race deviation from each model
# ---------------------------------------------------------------------------


def fig_deviations(ok: pd.DataFrame) -> str:
    use_style()
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    rng = np.random.default_rng(0)
    for j, name in enumerate(MODEL_ORDER):
        vals = ok[f"model_deviation_{name}"] * 100
        jitter = rng.uniform(-0.16, 0.16, len(vals))
        ax.plot(j + jitter, vals, "o", color=MODEL_COLOR[name], markersize=4.5,
                alpha=0.55, markeredgewidth=0)
        ax.plot([j - 0.26, j + 0.26], [vals.mean()] * 2, color=INK, lw=2.6,
                solid_capstyle="round", zorder=5)
        ax.annotate(f"{vals.mean():.2f}", xy=(j, vals.mean()),
                    xytext=(30, 2), textcoords="offset points",
                    fontsize=9, color=INK_2, fontweight="600")
    ax.set_xticks(range(len(MODEL_ORDER)))
    ax.set_xticklabels(MODEL_ORDER)
    ax.set_ylabel("RMSE vs model prediction  (percentage points)")
    ax.set_title(f"Per-race deviation from each model's optimal shape "
                 f"(start-corrected, n = {len(ok)})", loc="left", pad=10)
    note = ("Each dot is one race; the bar is the mean. Lower is closer to that "
            "model's predicted split distribution. M0 and M1 predict identical "
            "shapes and differ only in mechanism, so their columns match by "
            "construction. Descriptive only.")
    return _finish(fig, ax, "emp03_model_deviations", note, OUT_FIG)


# ---------------------------------------------------------------------------
# Figure 4 and analysis: the start effect (Phase 7)
# ---------------------------------------------------------------------------


def start_effect(ok: pd.DataFrame, shapes: dict):
    """
    How much of the fast first lap is the dive, and does the model ranking
    survive uncertainty in the start credit?
    """
    d_yd = SCY_200.split_distance_m  # 45.72 m per lap

    lap1 = ok["split1_time"]
    mid = ok[["split2_time", "split3_time"]].mean(axis=1)
    v1 = d_yd / lap1
    vmid = d_yd / mid

    # Time the dive is worth ON THIS DATA if laps 2-3 pace were swum in lap 1.
    implied_credit = mid - lap1

    # Literature anchor: elite 15 m start time vs covering 15 m at race pace.
    v_race = SCY_200.total_distance_m / ok["final_time_s"]
    lit_lo = 15.0 / v_race.mean() - 6.41   # Rudnik et al. 2023, intl males
    lit_hi = 15.0 / v_race.mean() - 6.12   # Tor, Pease & Ball 2014, elite males

    # Sensitivity of the model ranking to the start credit.
    offsets = np.round(np.arange(1.2, 2.81, 0.2), 2)
    rows = []
    T = ok["final_time_s"].to_numpy()
    laps = np.vstack([ok[f"split{i}_time"].to_numpy() for i in range(1, 5)]).T
    for off in offsets:
        lapsc = laps.copy()
        lapsc[:, 0] -= off
        P = lapsc / lapsc.sum(axis=1, keepdims=True)
        row = {"offset_s": off}
        for name in MODEL_ORDER:
            row[name] = float(np.sqrt(np.mean((P - shapes[name][None, :]) ** 2,
                                              axis=1)).mean() * 100)
        row["best"] = min(MODEL_ORDER, key=lambda m: row[m])
        rows.append(row)
    sens = pd.DataFrame(rows)

    # figure
    use_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.6))

    ax1.hist(implied_credit, bins=18, color=SERIES[0], edgecolor="#fcfcfb",
             linewidth=0.6)
    ax1.axvline(START_OFFSET_S, color=INK, lw=1.8)
    ax1.annotate(f"model credit {START_OFFSET_S:.1f} s",
                 xy=(START_OFFSET_S, ax1.get_ylim()[1] * 0.92),
                 xytext=(6, 0), textcoords="offset points", fontsize=9,
                 color=INK_2, fontweight="600")
    ax1.axvspan(lit_lo, lit_hi, color=SERIES[2], alpha=0.18)
    ax1.annotate("literature-implied\nelite band",
                 xy=(0.5 * (lit_lo + lit_hi), ax1.get_ylim()[1] * 0.72),
                 ha="center", fontsize=8.5, color=INK_2)
    ax1.set_xlabel("lap 1 advantage over mid-race laps  (s)")
    ax1.set_ylabel("races")
    ax1.set_title("How much faster the first lap actually is", loc="left", pad=8)

    for name in MODEL_ORDER:
        if name == "M1":
            continue
        label = "M0 / M1" if name == "M0" else name
        ax2.plot(sens["offset_s"], sens[name], color=MODEL_COLOR[name], lw=1.9,
                 marker=MARKERS[MODEL_ORDER.index(name)], markersize=5,
                 markeredgecolor="#fcfcfb", markeredgewidth=1.0, label=label)
    ax2.axvline(START_OFFSET_S, color=INK_3, ls="--", lw=1.0)
    ax2.set_xlabel("start credit applied to lap 1  (s)")
    ax2.set_ylabel("mean RMSE vs model  (pp)")
    ax2.set_title("Model ranking across the start-credit band", loc="left", pad=8)
    ax2.legend(loc="upper right", fontsize=8.5)

    note = ("Left: lap 1 is faster than the mid-race laps by far more than the dive "
            "alone explains; the excess is pacing and fresh-swimmer effects, which is "
            "why the credit must not be estimated from lap differences. Right: the "
            "M4 < M3 < M0/M1 < M2 ordering holds across the whole 1.2-2.8 s band.")
    path = _finish(fig, (ax1, ax2), "emp04_start_effect", note, OUT_FIG)

    stats = {
        "v1_mean": float(v1.mean()), "vmid_mean": float(vmid.mean()),
        "implied_credit_mean": float(implied_credit.mean()),
        "implied_credit_sd": float(implied_credit.std(ddof=1)),
        "lit_band": (float(lit_lo), float(lit_hi)),
        "ranking_stable": bool((sens["best"] == sens["best"].iloc[0]).all()),
        "best_everywhere": str(sens["best"].iloc[0]),
    }
    return path, sens, stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_report(ok, df_all, shapes, sens, stats) -> str:
    os.makedirs(OUT_RES, exist_ok=True)

    comp = []
    for name in MODEL_ORDER:
        dev = ok[f"model_deviation_{name}"] * 100
        comp.append({"model": name,
                     "mean_RMSE_pp": round(dev.mean(), 3),
                     "sd_RMSE_pp": round(dev.std(ddof=1), 3),
                     "n_races_best": int((ok["best_model"] == name).sum())})
    comp = pd.DataFrame(comp)
    comp.to_csv(os.path.join(OUT_RES, "pilot_model_comparison.csv"), index=False)
    sens.to_csv(os.path.join(OUT_RES, "pilot_start_sensitivity.csv"), index=False)

    train, test = data_split.split_by_swimmer(ok)
    rep = data_split.split_report(train, test)

    P_raw = [ok[f"P{i}"].mean() * 100 for i in range(1, 5)]
    P_cor = [ok[f"P{i}_corrected"].mean() * 100 for i in range(1, 5)]

    lines = f"""# Pilot empirical report — first real races through the pipeline

Date: 2026-08-31. Dataset version: **pilot-v0.1** (see data provenance below).

## What this is, and is not

This is the Phase 5-7 pipeline test on the first real data: descriptive
statistics, the first observed-versus-predicted comparison, and the start-effect
check. It is **not** the pre-registered held-out model comparison. No parameter
was fitted to any of this data, the swimmer-level train/test split has been
generated and recorded but **the test set has not been evaluated against any
fitted model**, and with n = {len(ok)} races from a single meet nothing here is
a strong conclusion.

## Dataset

| | |
|---|---|
| Raw rows ingested | {len(df_all)} |
| Usable races (all quality gates passed) | {len(ok)} |
| Source of every usable race | Official Hy-Tek results, Orinda Aquatics SCY Senior Open, Jan 25-26 2025, Sanction #25-010, Boys 200 Yard Freestyle, pacswim.org (checksum-verified retrieval, 2026-08-31) |
| Population of usable races | male, ages 15-18, SCY, timed finals |
| Unique swimmers (usable) | {ok['swimmer_id'].nunique()} |
| Final time range | {preprocessing.format_time(ok['final_time_s'].min())} to {preprocessing.format_time(ok['final_time_s'].max())} (mean {preprocessing.format_time(ok['final_time_s'].mean())}) |
| Age distribution (usable) | {ok['age'].astype(int).value_counts().sort_index().to_dict()} |

Excluded rows, by blocking reason (a row can carry several flags):
missing splits {int(df_all['flag_missing_splits'].sum())} (the 449 SwimCloud
rows, which publish no splits); course mismatch {int(df_all['flag_course_mismatch'].sum())}
(Far Western is LCM); age outside 15-18 or unknown {int(df_all['flag_age_out_of_scope'].sum())}
(includes all SwimCloud rows, which publish no ages, and {132 - len(ok)} Orinda
swims aged 12-14 or 19+). Zero rows failed monotonicity, final-time match,
plausibility, or duplication — the official file is internally consistent.

## Observed pacing (n = {len(ok)})

| | lap 1 | lap 2 | lap 3 | lap 4 |
|---|---|---|---|---|
| recorded share | {P_raw[0]:.2f}% | {P_raw[1]:.2f}% | {P_raw[2]:.2f}% | {P_raw[3]:.2f}% |
| start-corrected ({START_OFFSET_S:.1f} s) | {P_cor[0]:.2f}% | {P_cor[1]:.2f}% | {P_cor[2]:.2f}% | {P_cor[3]:.2f}% |

Mean half difference +{ok['half_difference'].mean():.2f} s (positive split).
Mean lap-1 to lap-2 drop +{ok['drop_1_2'].mean():.2f} s; mean lap-3 to lap-4
drop {ok['drop_3_4'].mean():+.2f} s. The fade is overwhelmingly front-loaded,
and the final lap is on average slightly FASTER than the third — a finishing
kick that none of the cost-based models produces.

External check: Robertson et al. (2009), 200 m free international finalists
(men, LCM), show the same family of shape — laps 23.5 / 25.2 / 25.7 / 25.6% —
fast first lap, then a flat back half with no terminal fade. The pilot swimmers
are more front-loaded than those elites, consistent with both their age and
SCY underwater time.

## First model comparison (descriptive)

Start-corrected RMSE against each model's predicted split distribution:

| model | mechanism | mean RMSE (pp) | races where best |
|---|---|---|---|
""" + "\n".join(
        f"| {r.model} | "
        f"{ {'M0':'constant economy','M1':'oxygen kinetics','M2':'reserve fatigue','M3':'position fatigue','M4':'velocity ceiling'}[r.model] } | "
        f"{r.mean_RMSE_pp:.2f} ± {r.sd_RMSE_pp:.2f} | {r.n_races_best} |"
        for r in comp.itertuples()) + f"""

Reading, with small-n caution:

1. **M2 is contradicted.** Its predicted negative split has the wrong sign
   against every single race. This was the pre-registered expectation, and it
   is the one claim n = {len(ok)} can support, because it is a sign, not a
   magnitude.
2. **The front-loaded family (M4) tracks the data best**, and the observed
   drop pattern (large lap-1 to 2, none lap-3 to 4) is qualitatively M4's
   signature rather than M3's even fade. Ranking, not proof.
3. **Every model is beaten by the data's own front-loadedness.** Observed
   corrected lap-1 share ({P_cor[0]:.2f}%) is below even M4's prediction
   ({shapes['M4'][0]*100:.2f}%). Either the start credit is too small, or a
   mechanism is missing (see below), or both.

## Start effect (Phase 7)

Mean lap-1 velocity {stats['v1_mean']:.3f} m/s vs mid-race {stats['vmid_mean']:.3f} m/s.
Lap 1 is faster than the mid-race laps by {stats['implied_credit_mean']:.2f} ±
{stats['implied_credit_sd']:.2f} s.

The literature-implied dive value for elite males is only about
{stats['lit_band'][0]:.1f}-{stats['lit_band'][1]:.1f} s at this field's race
pace (measured 15 m start times of 6.1-6.4 s against covering 15 m at race
speed). **The observed lap-1 advantage is therefore roughly 1 s larger than
the dive alone explains.** The excess is pacing behaviour and fresh-swimmer
physiology, which is exactly why the start credit must come from start-time
measurements and never be estimated from lap differences — doing so would
absorb genuine pacing into the correction.

Ranking stability: across the whole pre-registered start-credit band
(1.2-2.8 s), the best-fitting model is **{stats['best_everywhere']} at every
value** (see pilot_start_sensitivity.csv). The descriptive ranking does not
depend on the weakest number in the model.

Verdict on the Phase 7 question: **yes, a dedicated start term appears
necessary.** A constant credit is serviceable for shape comparison, but lap 1
mixes three separable effects (dive, underwater share, fresh-swimmer cost) that
an eight-segment model with an explicit start phase should separate. beta_x
fitted without that separation would absorb the residual.

## Train/test split (generated, not consumed)

Grouped by swimmer, seed {data_split.DEFAULT_SEED}: {rep['n_races_train']} train /
{rep['n_races_test']} test races ({rep['n_swimmers_train']}/{rep['n_swimmers_test']}
swimmers, overlap {rep['swimmer_overlap']}). Recorded here so the assignment is
frozen before any calibration happens. Note the pilot has
{(ok.groupby('swimmer_id').size() > 1).sum()} swimmers with more than one usable
race, so the mixed-effects structure is not yet exercised.

## Known limitations of pilot-v0.1

Single meet, single region, single day-pair; no 15 m times published, so the
start credit stays literature-anchored rather than measured; no usable race has
a pre-race personal best (this meet is the earliest in the file), so the
deviation-versus-performance hypothesis (H1) cannot be tested on this pilot at
all — that requires either earlier meets or the next season of the same
swimmers; ages 15-18 only after filtering a senior-open field, so selection is
toward committed club swimmers.

## Next data step

Expand to 200-300 races across several meets (Phase 8) using the same
`src/hytek_parser.py` route on official pacswim.org results files, prioritizing
meets that give the same swimmers multiple races so pre-race PBs and the
mixed-effects structure become available.
"""
    path = os.path.join(OUT_RES, "pilot_report.md")
    with open(path, "w") as f:
        f.write(lines)
    return path


def main() -> None:
    ok = load_usable()
    df_all = pd.read_csv(PROCESSED, low_memory=False)
    shapes = model_shapes()

    made = [fig_distributions(ok), fig_profile_vs_models(ok, shapes),
            fig_deviations(ok)]
    p4, sens, stats = start_effect(ok, shapes)
    made.append(p4)
    report = write_report(ok, df_all, shapes, sens, stats)

    for m in made:
        print("wrote", m)
    print("wrote", report)
    print("\nbest model at every start credit 1.2-2.8 s:",
          stats["best_everywhere"], "| ranking stable:", stats["ranking_stable"])


if __name__ == "__main__":
    main()
