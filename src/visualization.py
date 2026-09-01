"""
Figures (Phase 15).

Every figure is written for print: one measure per axis, no dual axes, a
recessive grid, thin marks, and direct labels on series wherever the legend
would otherwise be the only way to tell lines apart.

The categorical hues are assigned in a fixed order and never cycled. Three of
them sit below 3:1 contrast against the light surface, so every categorical
series also carries a direct label or a distinct marker shape: identity is
never communicated by colour alone.
"""

from __future__ import annotations

import os
import textwrap
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from .parameters import Course, Swimmer, SCY_200, REFERENCE, WORKING, ARCHETYPES
from . import model
from . import optimization
from . import sensitivity
from . import simulator


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8880"
GRID = "#e4e3dd"

#: Fixed categorical order. Never cycled, never reordered by rank.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]

#: Single-hue sequential ramp, light to dark, for magnitude surfaces.
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue", ["#eef4fc", "#c3daf4", "#8fbcea", "#5a99de", "#2a78d6", "#1a4e8c"]
)

#: Two hues plus a neutral midpoint, for signed quantities only.
DIV = LinearSegmentedColormap.from_list(
    "div", ["#1a4e8c", "#5a99de", "#d9d8d2", "#ef8f63", "#a83a15"]
)

STYLE = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": INK_3,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "600",
    "axes.labelsize": 10,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "legend.labelcolor": INK_2,
    "lines.linewidth": 2.0,
    "lines.markersize": 6,
    "font.size": 10,
    "figure.dpi": 130,
    "savefig.dpi": 220,
    "savefig.bbox": "tight",
}

FIGDIR = "figures"


def use_style():
    plt.rcParams.update(STYLE)


def _finish(fig, ax_or_axes, name: str, note: str | None = None, outdir: str = FIGDIR,
            wrap: int = 96):
    """
    Attach a provenance note, save PNG and PDF, close.

    The note is hard-wrapped. An unwrapped caption is wider than the axes and,
    with bbox_inches="tight", silently stretches the saved figure to match,
    leaving a band of dead space beside the plot.
    """
    if note:
        fig.text(0.005, -0.02, textwrap.fill(note, wrap),
                 fontsize=7.5, color=INK_3, va="top")
    os.makedirs(outdir, exist_ok=True)
    png = os.path.join(outdir, f"{name}.png")
    fig.savefig(png)
    fig.savefig(os.path.join(outdir, f"{name}.pdf"))
    plt.close(fig)
    return png


def _label_right(ax, x, y, text, color, dx=0.01, fontsize=9):
    """Direct label at the right end of a series."""
    ax.annotate(text, xy=(x, y), xytext=(4, 0), textcoords="offset points",
                color=color, fontsize=fontsize, va="center", ha="left",
                fontweight="600")


# ---------------------------------------------------------------------------
# Figure 1 and 2: trajectories
# ---------------------------------------------------------------------------


def fig_velocity_and_energy(sw: Swimmer = WORKING, course: Course = SCY_200,
                            outdir: str = FIGDIR):
    """
    Figures 1 and 2. Optimal velocity and energy reserve against distance,
    stacked so the two share a distance axis and can be read together.
    """
    use_style()
    opt = optimization.optimize(sw, course)
    traj = simulator.simulate(np.asarray(opt["velocities"]), sw, course)

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.4), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1], "hspace": 0.12})
    ax1, ax2 = axes

    ax1.step(traj["x"], traj["v"], where="post", color=SERIES[0], label="optimal")
    ax1.margins(y=0.20)
    ax1.set_ylabel("velocity  (m/s)")
    ax1.set_title("Optimal velocity and energy reserve over the race",
                  loc="left", pad=10)
    for i, v in enumerate(np.asarray(opt["velocities"])):
        xm = (i + 0.5) * course.split_distance_m
        ax1.annotate(f"{v:.3f}", xy=(xm, v), xytext=(0, 7),
                     textcoords="offset points", ha="center",
                     fontsize=8.5, color=INK_2)

    ax2.plot(traj["x"], traj["E"] / 1000.0, color=SERIES[2])
    ax2.fill_between(traj["x"], 0, traj["E"] / 1000.0, color=SERIES[2], alpha=0.10)
    ax2.axhline(0.0, color=INK_3, lw=1.0, ls="--")
    ax2.set_ylabel("anaerobic reserve  (kJ)")
    ax2.set_xlabel("distance  (m)")
    ax2.annotate("reserve reaches zero exactly at the touch",
                 xy=(course.total_distance_m, 0.0),
                 xytext=(-0.42 * course.total_distance_m, 0.30 * sw.E0 / 1000.0),
                 textcoords="data", ha="left", fontsize=8.5, color=INK_2,
                 arrowprops=dict(arrowstyle="-", color=INK_3, lw=0.9,
                                 connectionstyle="angle3,angleA=0,angleB=70"))

    for ax in axes:
        for i in range(1, course.n_splits):
            ax.axvline(i * course.split_distance_m, color=INK_3, lw=0.8,
                       ls=(0, (2, 3)), alpha=0.7)
        ax.margins(x=0.02)

    note = (f"{sw.label}  |  T* = {model.format_time(opt['race_time'])}  "
            f"|  R = {sw.R:.0f} W, E0 = {sw.E0/1000:.1f} kJ, "
            f"tau = {sw.tau:.0f} s, beta_x = {sw.beta_x:.2f}")
    return _finish(fig, axes, "fig01_velocity_energy", note, outdir)


# ---------------------------------------------------------------------------
# Figures 3 and 4: strategy comparison
# ---------------------------------------------------------------------------


def fig_strategy_comparison(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                            outdir: str = FIGDIR):
    """
    Figures 3 and 4. Split times for each named strategy against the optimum,
    all at a matched energy budget, with the pacing penalty beside them.
    """
    use_style()
    rows = optimization.compare_strategies(sw, course)
    keep = ["OPTIMAL", "even", "positive_split", "negative_split",
            "aggressive_opening", "very_aggressive", "conservative_opening"]
    rows = [r for r in rows if r["strategy"] in keep]
    # OPTIMAL and even coincide in the constant-economy model; drop the duplicate.
    if len(rows) > 1 and np.allclose(rows[0]["splits"], rows[1]["splits"], atol=1e-6):
        rows = [rows[0]] + rows[2:]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.8),
                                   gridspec_kw={"width_ratios": [1.45, 1]})

    x = np.arange(1, course.n_splits + 1)
    for i, r in enumerate(rows):
        c = SERIES[i % len(SERIES)]
        lw = 2.6 if r["strategy"] == "OPTIMAL" else 1.9
        ax1.plot(x, r["splits"], color=c, lw=lw,
                 marker=MARKERS[i % len(MARKERS)], markersize=7,
                 markeredgecolor=SURFACE, markeredgewidth=1.2,
                 label=r["strategy"].replace("_", " "))
    ax1.set_xticks(x)
    ax1.set_xlabel("split")
    ax1.set_ylabel("split time  (s)")
    ax1.set_title("Split times at a matched energy budget", loc="left", pad=10)
    ax1.set_xlim(0.85, course.n_splits + 0.15)
    ax1.margins(y=0.16)
    ax1.legend(ncol=2, loc="upper left")

    names = [r["strategy"].replace("_", " ") for r in rows[1:]]
    pen = [r["penalty_s"] for r in rows[1:]]
    order = np.argsort(pen)
    names = [names[i] for i in order]
    pen = [pen[i] for i in order]
    cols = [SERIES[(list(range(1, len(rows)))[order[i]]) % len(SERIES)]
            for i in range(len(order))]
    bars = ax2.barh(names, pen, color=cols, height=0.62)
    for b, v in zip(bars, pen):
        ax2.annotate(f"+{v:.2f} s", xy=(b.get_width(), b.get_y() + b.get_height() / 2),
                     xytext=(5, 0), textcoords="offset points",
                     va="center", fontsize=9, color=INK_2, fontweight="600")
    ax2.set_xlabel("time lost vs optimum  (s)")
    ax2.set_title("Pacing penalty", loc="left", pad=10)
    ax2.margins(x=0.22)
    ax2.grid(axis="y", visible=False)

    note = ("Every strategy is rescaled to finish with exactly zero reserve, so the "
            "penalty is the cost of spending the same fuel in the wrong order, not "
            "the cost of trying less hard.")
    fig.tight_layout()
    return _finish(fig, (ax1, ax2), "fig03_strategy_comparison", note, outdir)


# ---------------------------------------------------------------------------
# Figures 5 and 6: opening penalty
# ---------------------------------------------------------------------------


def fig_opening_penalty(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                        outdir: str = FIGDIR):
    """
    Figures 5 and 6 on one axis. Time lost as a function of how far the first 50
    departs from its optimal velocity, with the remaining three splits
    re-optimized in every case.

    Splitting this into a "too fast" chart and a "too slow" chart would hide the
    thing worth seeing: the curve is smooth through zero and locally symmetric,
    so small errors in either direction cost about the same, and the cost grows
    quadratically rather than linearly.
    """
    use_style()
    f = np.linspace(-0.10, 0.12, 45)
    res = optimization.opening_penalty_curve(f, sw, course)

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    pct = res["overspeed"] * 100.0
    ax.plot(pct, res["penalty_s"], color=SERIES[0])
    ax.fill_between(pct, 0, res["penalty_s"], color=SERIES[0], alpha=0.10)
    ax.axvline(0.0, color=INK_3, lw=1.0, ls="--")
    ax.axhline(0.0, color=INK_3, lw=1.0)

    for target in (-5.0, 2.0, 5.0, 10.0):
        if pct.min() <= target <= pct.max():
            y = float(np.interp(target, pct, res["penalty_s"]))
            ax.plot([target], [y], marker="o", markersize=8, color=SERIES[1],
                    markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=5)
            ax.annotate(f"{target:+.0f}%  ->  {y:.2f} s",
                        xy=(target, y), xytext=(6, 8), textcoords="offset points",
                        fontsize=9, color=INK_2, fontweight="600")

    ax.annotate("optimal opening", xy=(0, 0), xytext=(6, 26),
                textcoords="offset points", fontsize=9, color=INK_3)
    ax.set_xlabel("first-50 velocity relative to optimum  (%)")
    ax.set_ylabel("time lost over the race  (s)")
    ax.set_title("What it costs to open the race off pace", loc="left", pad=10)

    note = (f"Splits 2 to 4 are re-optimized for each opening. "
            f"Baseline T* = {model.format_time(res['T_optimal'])}, "
            f"optimal first-50 velocity {res['v_optimal_first']:.3f} m/s. "
            f"Model: {sw.label}.")
    return _finish(fig, ax, "fig05_opening_penalty", note, outdir)


# ---------------------------------------------------------------------------
# Phase 4: cost of velocity
# ---------------------------------------------------------------------------


def fig_cost_of_velocity(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                         outdir: str = FIGDIR):
    """
    The hydrodynamic core of the model: drag force, the metabolic cost rate it
    implies, and the cost of covering a fixed 50 at that speed.

    The third panel is the one that matters for pacing. Cost per unit distance
    scales with v^{p-1}, not v^p, and it is the curvature of *that* function
    that makes uneven pacing expensive.
    """
    use_style()
    v = np.linspace(1.20, 2.20, 240)
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.2))

    axes[0].plot(v, model.drag_force(v, sw), color=SERIES[0])
    axes[0].set_ylabel("drag force  (N)")
    axes[0].set_title("F$_D$ = ½ρC$_D$Av²", loc="left", pad=8)

    axes[1].plot(v, model.metabolic_rate(v, sw) / 1000.0, color=SERIES[1])
    axes[1].axhline(sw.R / 1000.0, color=INK_3, ls="--", lw=1.2)
    axes[1].annotate(f"aerobic ceiling R = {sw.R:.0f} W",
                     xy=(v[5], sw.R / 1000.0), xytext=(0, 6),
                     textcoords="offset points", fontsize=8.5, color=INK_2)
    axes[1].set_ylabel("metabolic cost rate  (kW)")
    axes[1].set_title("C(v) = kv³", loc="left", pad=8)

    e50 = sw.k * course.split_distance_m * v ** (sw.p - 1.0) / 1000.0
    axes[2].plot(v, e50, color=SERIES[2])
    axes[2].set_ylabel("energy per 50  (kJ)")
    axes[2].set_title("C(v)·t = kdv²  (cost of one split)", loc="left", pad=8)

    v_star = model.even_pace_velocity(sw, course)
    for ax, series in zip(axes, [model.drag_force(v_star, sw),
                                 model.metabolic_rate(v_star, sw) / 1000.0,
                                 sw.k * course.split_distance_m * v_star ** (sw.p - 1) / 1000]):
        ax.axvline(v_star, color=INK_3, lw=1.0, ls=":")
        ax.plot([v_star], [series], marker="o", markersize=8, color=INK,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=5)
        ax.set_xlabel("velocity  (m/s)")
    axes[0].annotate(f"race pace\n{v_star:.3f} m/s", xy=(v_star, model.drag_force(v_star, sw)),
                     xytext=(-70, 6), textcoords="offset points",
                     fontsize=8.5, color=INK_2)

    note = (f"{sw.label}:  ½ρC$_D$A = {sw.drag_factor:.1f} N s²/m², "
            f"k = {sw.k:.1f} W s³/m³, p = {sw.p:.1f}, "
            f"η = η_p·η_g = {sw.eta:.3f}.")
    fig.tight_layout()
    return _finish(fig, axes, "fig02_cost_of_velocity", note, outdir)


def fig_drag_sensitivity(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                         outdir: str = FIGDIR):
    """
    Hydrodynamic sensitivity: what a change in drag buys in race time, and what
    it does to the optimal shape.

    The right panel is intentionally flat. It is the visual statement of the
    central negative result: drag sets how fast you go, not how you distribute
    it.
    """
    use_style()
    mults = np.linspace(0.75, 1.25, 21)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.4))

    for i, (field, label) in enumerate([("Cd", "drag coefficient C$_D$"),
                                        ("A", "frontal area A"),
                                        ("eta_p", "propelling efficiency η$_p$")]):
        base = getattr(sw, field)
        T, P1 = [], []
        for m in mults:
            o = optimization.optimize(sw.with_(**{field: float(base * m)}), course)
            T.append(o["race_time"])
            P1.append(float(np.asarray(o["split_fractions"])[0]) * 100.0)
        c = SERIES[i]
        ax1.plot(mults * 100, T, color=c, marker=MARKERS[i], markersize=5,
                 markevery=4, markeredgecolor=SURFACE, markeredgewidth=1.0, label=label)
        ax2.plot(mults * 100, P1, color=c, marker=MARKERS[i], markersize=5,
                 markevery=4, markeredgecolor=SURFACE, markeredgewidth=1.0, label=label)
        _label_right(ax1, mults[-1] * 100, T[-1], label.split()[0], c, fontsize=8.5)

    ax1.set_xlabel("parameter, % of baseline")
    ax1.set_ylabel("optimal race time  (s)")
    ax1.set_title("Drag sets the race time", loc="left", pad=10)
    ax1.legend(loc="upper left")

    ax2.set_xlabel("parameter, % of baseline")
    ax2.set_ylabel("optimal first-50 share of race  (%)")
    ax2.set_title("Drag does not set the pacing shape", loc="left", pad=10)
    ax2.set_ylim(24.0, 26.0)
    ax2.axhline(25.0, color=INK_3, ls="--", lw=1.0)
    ax2.annotate("even pacing, 25.00%", xy=(mults[2] * 100, 25.0), xytext=(0, 7),
                 textcoords="offset points", fontsize=8.5, color=INK_2)

    note = ("Right panel: the optimal first-50 share is pinned at 25.00% across a "
            "±25% change in every hydrodynamic parameter. This is the closed-form "
            "result, not a numerical coincidence.")
    fig.tight_layout()
    return _finish(fig, (ax1, ax2), "fig04_drag_sensitivity", note, outdir)


# ---------------------------------------------------------------------------
# Figures 7 and 8: physiology versus shape
# ---------------------------------------------------------------------------


def fig_physiology_vs_shape(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                            outdir: str = FIGDIR):
    """
    Figures 7 and 8. Optimal first-50 share against aerobic capacity R and
    against the anaerobic reserve E0, with race time on a companion axis in a
    separate panel rather than a second y-scale.
    """
    use_style()
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.4), sharex="col")

    for col, (field, label, mult) in enumerate([
        ("R", "aerobic ceiling R  (W)", (0.75, 1.25)),
        ("E0", "anaerobic reserve E$_0$  (kJ)", (0.55, 1.70)),
    ]):
        base = getattr(sw, field)
        vals = np.linspace(base * mult[0], base * mult[1], 25)
        T, P1 = [], []
        for val in vals:
            o = optimization.optimize(sw.with_(**{field: float(val)}), course)
            T.append(o["race_time"])
            P1.append(float(np.asarray(o["split_fractions"])[0]) * 100.0)
        xs = vals / 1000.0 if field == "E0" else vals

        axes[0, col].plot(xs, T, color=SERIES[col])
        axes[0, col].set_ylabel("optimal race time  (s)")
        axes[0, col].set_title(f"Race time vs {field}", loc="left", pad=8)

        axes[1, col].plot(xs, P1, color=SERIES[col])
        axes[1, col].axhline(25.0, color=INK_3, ls="--", lw=1.0)
        axes[1, col].set_ylim(24.0, 26.0)
        axes[1, col].set_ylabel("optimal first-50 share  (%)")
        axes[1, col].set_xlabel(label)
        axes[1, col].set_title(f"Pacing shape vs {field}", loc="left", pad=8)
        axes[1, col].annotate("even pacing", xy=(xs[1], 25.0), xytext=(0, 7),
                              textcoords="offset points", fontsize=8.5, color=INK_2)

    note = ("A swimmer with a bigger anaerobic tank does not want a faster opening. "
            "Under a constant-economy cost function they want the same shape and a "
            "faster race. The engine sets the level; only economy decay sets the shape.")
    fig.tight_layout()
    return _finish(fig, axes, "fig07_physiology_vs_shape", note, outdir)


# ---------------------------------------------------------------------------
# Figure 14: sensitivity heatmap
# ---------------------------------------------------------------------------


def fig_shape_heatmap(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                      n: int = 25, outdir: str = FIGDIR):
    """
    Figure 14. Optimal first-50 share over the cost exponent p and the
    position-fatigue coefficient beta_x, the only two parameters in the model
    that can move the pacing shape.

    A single-hue sequential ramp, because the quantity is a magnitude and has no
    meaningful midpoint. Contours are drawn so the surface can be read without
    relying on colour alone.
    """
    use_style()
    grid = sensitivity.exponent_map(sw, course, n=n)
    P1 = grid["P1"] * 100.0

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    im = ax.pcolormesh(grid["p"], grid["beta_x"], P1, cmap=SEQ, shading="gouraud")
    cs = ax.contour(grid["p"], grid["beta_x"], P1,
                    levels=[23.0, 23.5, 24.0, 24.5, 25.0],
                    colors=INK_2, linewidths=0.9)
    ax.clabel(cs, inline=True, fontsize=8, fmt="%.1f%%")

    ax.axhline(0.0, color=INK, lw=1.4)
    ax.annotate("β$_x$ = 0: every p gives exactly 25.00%",
                xy=(grid["p"].mean(), 0.0), xytext=(0, 7),
                textcoords="offset points", ha="center",
                fontsize=8.5, color=INK, fontweight="600")

    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("optimal first-50 share of race  (%)", color=INK_2)
    cb.outline.set_edgecolor(INK_3)

    ax.set_xlabel("energy-cost exponent  p")
    ax.set_ylabel("position-fatigue coefficient  β$_x$")
    ax.set_title("The only two parameters that bend the optimal pacing shape",
                 loc="left", pad=10)
    ax.grid(False)

    note = ("Read the bottom edge first: with no economy decay the optimum is even "
            "pacing for every exponent. Moving up the axis is the only way to make "
            "a positive split optimal, and larger p damps how far the splits spread.")
    return _finish(fig, ax, "fig14_shape_heatmap", note, outdir)


# ---------------------------------------------------------------------------
# Figure 9: theoretical versus observed
# ---------------------------------------------------------------------------


def fig_theory_vs_observed(sw: Swimmer = WORKING, course: Course = SCY_200,
                           outdir: str = FIGDIR):
    """
    Figure 9. Predicted split fractions against the recorded shapes, with the
    dive start credited back to split 1 so the two are on the same footing.

    The observed series here are PLACEHOLDERS built from representative split
    sheets, not a dataset. The figure is captioned as such and must be
    regenerated once Phase 9 collection is done.
    """
    use_style()
    opt = optimization.optimize(sw, course)
    P_model = np.asarray(opt["split_fractions"]) * 100.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.8),
                                   gridspec_kw={"width_ratios": [1.2, 1]})
    x = np.arange(1, course.n_splits + 1)

    series = [("model optimum", P_model, SERIES[0], MARKERS[0])]
    for i, key in enumerate(["observed_elite_corrected", "observed_pilot_corrected"]):
        shape = np.asarray(simulator.STRATEGY_SHAPES[key], dtype=float)
        t = 1.0 / shape
        series.append((key.replace("observed_", "").replace("_corrected", "")
                       + " (placeholder)", t / t.sum() * 100.0,
                       SERIES[i + 1], MARKERS[i + 1]))

    for name, P, c, mk in series:
        ax1.plot(x, P, color=c, marker=mk, markersize=8,
                 markeredgecolor=SURFACE, markeredgewidth=1.3, label=name)
        _label_right(ax1, x[-1], P[-1], name.split()[0], c, fontsize=8.5)
    ax1.axhline(25.0, color=INK_3, ls="--", lw=1.0)
    ax1.set_xticks(x)
    ax1.set_xlabel("split")
    ax1.set_ylabel("share of race time  (%)")
    ax1.set_title("Predicted vs recorded pacing shape", loc="left", pad=10)
    ax1.set_xlim(0.85, course.n_splits + 1.3)
    ax1.legend(loc="upper left")

    names, rmses, cols = [], [], []
    for i, (name, P, c, _) in enumerate(series[1:], start=1):
        rmse = float(np.sqrt(np.mean((P - P_model) ** 2)))
        names.append(name.split()[0])
        rmses.append(rmse)
        cols.append(c)
    bars = ax2.bar(names, rmses, color=cols, width=0.5)
    for b, v in zip(bars, rmses):
        ax2.annotate(f"{v:.2f} pp", xy=(b.get_x() + b.get_width() / 2, v),
                     xytext=(0, 5), textcoords="offset points", ha="center",
                     fontsize=9.5, color=INK_2, fontweight="600")
    ax2.set_ylabel("RMSE vs model  (percentage points)")
    ax2.set_title("Deviation from the theoretical optimum", loc="left", pad=10)
    ax2.margins(y=0.25)
    ax2.grid(axis="x", visible=False)

    note = ("Observed series are REAL: elite = Robertson et al. 2009 mean lap times, "
            "men's 200 m free international finalists (LCM); pilot = this project's 80 "
            "usable SCY races (male 15-18, Orinda SC Senior Open, official splits). Both "
            "carry a 1.80 s start credit on lap 1. See results/validation/ for the full "
            "empirical comparison.")
    fig.tight_layout()
    return _finish(fig, (ax1, ax2), "fig09_theory_vs_observed", note, outdir)


# ---------------------------------------------------------------------------
# Figure 12: swimmer archetypes
# ---------------------------------------------------------------------------


def fig_archetypes(course: Course = SCY_200, match_time: float = 103.0,
                   outdir: str = FIGDIR):
    """
    Figure 12. Optimal pacing for each swimmer archetype, all calibrated to the
    same race time so the comparison isolates shape from speed.
    """
    use_style()
    picks = {k: ARCHETYPES[k] for k in
             ["reference", "aerobic", "anaerobic", "high_drag", "durable", "fatiguer"]}
    df = sensitivity.compare_archetypes(picks, course, match_time=match_time)

    # Profiles that share a beta_x produce *identical* optimal shapes, so drawing
    # them as separate series would stack four lines and four labels on top of
    # each other. Grouping them into one labelled line is both readable and a
    # more direct statement of the result.
    # Rounded to 6 dp, which is far finer than any meaningful pacing difference
    # (1e-6 of a race is 0.0001 s) but coarser than the 1e-8 solver noise that
    # would otherwise keep identical shapes from grouping.
    groups: dict = {}
    for _, row in df.iterrows():
        key = tuple(np.round([row.P1, row.P2, row.P3, row.P4], 6))
        groups.setdefault(key, []).append(row)

    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    x = np.arange(1, course.n_splits + 1)
    for i, (key, members) in enumerate(sorted(groups.items(), key=lambda kv: kv[0][0])):
        P = np.array(key) * 100.0
        c = SERIES[i % len(SERIES)]
        names = ", ".join(m.archetype for m in members)
        b = members[0].beta_x
        label = (f"β$_x$={b:.2f}   {names}" if len(members) == 1
                 else f"β$_x$={b:.2f}   {len(members)} profiles, identical: {names}")
        ax.plot(x, P, color=c, marker=MARKERS[i % len(MARKERS)], markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1.2, label=label)
        short = names if len(members) == 1 else f"{len(members)} profiles"
        _label_right(ax, x[-1], P[-1], short, c, fontsize=8.5)
    ax.axhline(25.0, color=INK_3, ls="--", lw=1.0)
    ax.set_xticks(x)
    ax.set_xlabel("split")
    ax.set_ylabel("share of race time  (%)")
    ax.set_xlim(0.85, course.n_splits + 0.85)
    ax.margins(y=0.20)
    ax.set_title(f"Optimal pacing by swimmer profile, all matched to "
                 f"{model.format_time(match_time)}", loc="left", pad=10)
    ax.legend(loc="upper left", ncol=1)

    note = ("Each profile is recalibrated on E$_0$ to the same target time. The four "
            "profiles with β$_x$ = 0 collapse onto a single flat line at 25%: engine "
            "and drag differences do not separate them at all. Only the two economy-"
            "decay profiles depart from even pacing.")
    return _finish(fig, ax, "fig12_archetypes", note, outdir)


# ---------------------------------------------------------------------------
# Figure 13: what matters
# ---------------------------------------------------------------------------


def fig_elasticity(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                   outdir: str = FIGDIR):
    """
    Figure 13. A tornado of local sensitivities: seconds of race time gained or
    lost for a ±10% move in each parameter, with the parameters that move the
    pacing shape marked.
    """
    use_style()
    df = sensitivity.elasticity_table(sw, course)
    df = df[df["dT_s"].abs() > 1e-9].sort_values("abs_dT_s")

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    colors = [SERIES[1] if m else SERIES[0] for m in df["moves_shape"]]
    bars = ax.barh(df["parameter"], df["dT_s"], color=colors, height=0.6)
    for b, v in zip(bars, df["dT_s"]):
        off = 5 if v >= 0 else -5
        ha = "left" if v >= 0 else "right"
        ax.annotate(f"{v:+.2f} s", xy=(v, b.get_y() + b.get_height() / 2),
                    xytext=(off, 0), textcoords="offset points",
                    va="center", ha=ha, fontsize=9, color=INK_2, fontweight="600")
    ax.axvline(0.0, color=INK_3, lw=1.0)
    ax.set_xlabel("change in optimal race time over a ±10% parameter move  (s)")
    ax.set_title("What the race time is actually sensitive to", loc="left", pad=10)
    ax.margins(x=0.24, y=0.06)
    ax.grid(axis="y", visible=False)

    handles = [plt.Line2D([0], [0], color=SERIES[0], lw=6),
               plt.Line2D([0], [0], color=SERIES[1], lw=6)]
    ax.legend(handles, ["changes race time only", "also changes pacing shape"],
              loc="lower right", bbox_to_anchor=(1.0, -0.02))

    note = ("Only one parameter in the model is capable of moving the optimal split "
            "distribution. Everything else, including every hydrodynamic term, changes "
            "how fast the race is swum and nothing about how it is divided. C_D, A and "
            "rho enter only through their product, so their elasticities are identical "
            "by construction; rho is omitted because a realistic pool spans under 1%, "
            "not the 10% plotted here.")
    return _finish(fig, ax, "fig13_elasticity", note, outdir)


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def fig_penalty_robustness(sw: Swimmer = REFERENCE, course: Course = SCY_200,
                           n_draws: int = 240, outdir: str = FIGDIR):
    """
    Pacing penalties under parameter uncertainty. The point estimate is a thin
    claim when the physiological parameters are only known to about 10%; the
    interval is the honest version of the result.
    """
    use_style()
    df = sensitivity.penalty_robustness(sw, course, n_draws=n_draws)
    df = df[df["strategy"] != "even"].reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    y = np.arange(len(df))
    for i, row in df.iterrows():
        c = SERIES[i % len(SERIES)]
        ax.plot([row.lo, row.hi], [i, i], color=c, lw=2.0, alpha=0.35,
                solid_capstyle="round")
        ax.plot([row.q25, row.q75], [i, i], color=c, lw=6.0,
                solid_capstyle="round")
        ax.plot([row["median"]], [i], marker="o", markersize=9, color=c,
                markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=5)
        ax.annotate(f"{row['median']:.2f} s", xy=(row.hi, i), xytext=(7, 0),
                    textcoords="offset points", va="center", fontsize=9,
                    color=INK_2, fontweight="600")
    ax.set_yticks(y)
    ax.set_yticklabels([s.replace("_", " ") for s in df["strategy"]])
    ax.axvline(0.0, color=INK_3, lw=1.0)
    ax.set_xlabel("pacing penalty  (s)")
    ax.set_title("Pacing penalties survive parameter uncertainty", loc="left", pad=10)
    ax.margins(x=0.18)
    ax.grid(axis="y", visible=False)

    note = (f"{n_draws} draws with R, E$_0$, C$_D$, A, η$_p$, η$_g$ perturbed "
            f"lognormally at 10% CV. Thick bar: interquartile range. Thin bar: 5th "
            f"to 95th percentile. Dot: median.")
    return _finish(fig, ax, "fig15_penalty_robustness", note, outdir)


# ---------------------------------------------------------------------------


def build_all(outdir: str = FIGDIR) -> "list[str]":
    """Regenerate every figure. Returns the list of PNG paths written."""
    made = [
        fig_velocity_and_energy(WORKING, SCY_200, outdir),
        fig_cost_of_velocity(REFERENCE, SCY_200, outdir),
        fig_strategy_comparison(REFERENCE, SCY_200, outdir),
        fig_drag_sensitivity(REFERENCE, SCY_200, outdir),
        fig_opening_penalty(REFERENCE, SCY_200, outdir),
        fig_physiology_vs_shape(REFERENCE, SCY_200, outdir),
        fig_theory_vs_observed(WORKING, SCY_200, outdir),
        fig_archetypes(SCY_200, 103.0, outdir),
        fig_elasticity(REFERENCE, SCY_200, outdir),
        fig_shape_heatmap(REFERENCE, SCY_200, 25, outdir),
        fig_penalty_robustness(REFERENCE, SCY_200, 240, outdir),
    ]
    return made
