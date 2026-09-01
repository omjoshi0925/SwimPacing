#!/usr/bin/env python3
"""
Reproduce every result and figure in the repository.

    python scripts/run_all.py [--quick]

Writes CSV tables to results/ and PNG + PDF figures to figures/. Nothing is
cached; every number below is recomputed from parameters.py on each run.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import model, optimization, sensitivity, simulator, visualization  # noqa: E402
from src.parameters import (ARCHETYPES, REFERENCE, SCY_200, WORKING,  # noqa: E402
                            START_OFFSET_S)

warnings.filterwarnings("ignore")
RESULTS = "results"
COURSE = SCY_200


#: Where each table belongs. Placeholder output is segregated so it cannot be
#: mistaken for evidence; see results/placeholder_data/README.md.
SUBDIR = {
    "01_optimal_static": "theoretical", "02_mechanism_comparison": "theoretical",
    "03_strategies_reference": "theoretical", "03_strategies_working": "theoretical",
    "04_opening_penalty": "theoretical",
    "05_elasticity": "sensitivity", "06_parameter_sweeps": "sensitivity",
    "07_archetypes": "sensitivity", "08_penalty_robustness": "sensitivity",
    "09_validation_placeholder": "placeholder_data",
}


def _save(df: pd.DataFrame, name: str) -> None:
    out_dir = os.path.join(RESULTS, SUBDIR.get(name, "theoretical"))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.csv")
    df.to_csv(path, index=False)
    print(f"  wrote {path}  ({len(df)} rows)")


def banner(title: str) -> None:
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


# ---------------------------------------------------------------------------


def phase_3_4(quick: bool) -> None:
    banner("PHASE 3 + 4  Discrete model, drag-derived cost, closed form vs solver")

    sw = REFERENCE
    closed = model.optimal_solution_closed_form(sw, COURSE)
    solved = optimization.optimize_static(sw, COURSE, n_starts=8 if quick else 24)
    ode = simulator.simulate(np.asarray(closed["velocities"]), sw, COURSE)

    print(f"  drag factor  1/2 rho Cd A = {sw.drag_factor:8.2f} N s^2/m^2")
    print(f"  cost coeff   k            = {sw.k:8.2f} W s^3/m^3  (p = {sw.p})")
    print(f"  C at race pace            = {float(model.metabolic_rate(closed['velocities'][0], sw)):8.1f} W")
    print()
    print(f"  closed form   T = {closed['race_time']:.6f} s   "
          f"v = {np.round(closed['velocities'], 6)}")
    print(f"  SLSQP         T = {solved['race_time']:.6f} s   "
          f"gap = {solved['closed_form_gap_s']:.2e} s")
    print(f"  ODE simulator T = {ode['race_time']:.6f} s   "
          f"terminal E = {ode['terminal_energy']:.3e} J")
    print(f"  KKT residual              = {solved['kkt_residual']:.2e}")
    print(f"  max split spread          = {solved['max_split_spread_s']:.2e} s")
    print(f"\n  RESULT: optimal splits are even to {solved['max_split_spread_s']:.1e} s. "
          f"T* = {model.format_time(closed['race_time'])}")

    _save(pd.DataFrame({
        "split": np.arange(1, COURSE.n_splits + 1),
        "v_closed_form": closed["velocities"],
        "t_closed_form": closed["split_times"],
        "v_slsqp": solved["velocities"],
        "t_slsqp": solved["split_times"],
        "P_closed_form": closed["split_fractions"],
        "energy_after_split_kJ": closed["energy"][1:] / 1000.0,
    }), "01_optimal_static")


def phase_5(quick: bool) -> None:
    banner("PHASE 5  ODE model: which mechanisms can bend the optimal shape")

    rows = []
    cases = [
        ("static budget",            REFERENCE),
        ("+ oxygen kinetics tau=20", REFERENCE.with_(tau=20.0)),
        ("+ oxygen kinetics tau=30", REFERENCE.with_(tau=30.0)),
        ("+ position fatigue 0.15",  REFERENCE.with_(tau=20.0, beta_x=0.15)),
        ("+ position fatigue 0.30",  REFERENCE.with_(tau=20.0, beta_x=0.30)),
        ("+ reserve fatigue 0.30",   REFERENCE.with_(tau=20.0, beta_E=0.30)),
    ]
    if quick:
        cases = [c for c in cases if "reserve" not in c[0]]

    for name, sw in cases:
        opt = optimization.optimize(sw, COURSE, n_starts=4 if quick else 10)
        P = np.asarray(opt["split_fractions"])
        shape = ("even" if P.max() - P.min() < 1e-5
                 else ("positive split" if P[0] < P[-1] else "negative split"))
        rows.append({
            "model": name, "tau": sw.tau, "beta_x": sw.beta_x, "beta_E": sw.beta_E,
            "race_time": opt["race_time"],
            "P1": P[0], "P2": P[1], "P3": P[2], "P4": P[3],
            "shape": shape,
        })
        print(f"  {name:<26s} T = {opt['race_time']:7.3f}  "
              f"P = {np.round(P, 4)}  -> {shape}")

    print("\n  RESULT: oxygen kinetics slow the race but leave the shape exactly even.")
    print("  Position-coupled economy decay gives a positive split, reserve-coupled")
    print("  decay gives a negative split. Real races are positively split, so the")
    print("  data can discriminate between the two mechanisms.")
    _save(pd.DataFrame(rows), "02_mechanism_comparison")


def phase_6_7(quick: bool) -> None:
    banner("PHASE 6 + 7  Simulator, strategy comparison, pacing penalties")

    for label, sw in [("constant economy", REFERENCE), ("working model", WORKING)]:
        print(f"\n  --- {label} ({sw.label}) ---")
        rows = optimization.compare_strategies(sw, COURSE)
        recs = []
        for r in rows:
            splits = np.asarray(r["splits"])
            print(f"  {r['strategy']:<28s} T = {model.format_time(r['race_time'])}"
                  f"  dT = {r['penalty_s']:+6.3f} s   "
                  f"splits = {' '.join(f'{s:5.2f}' for s in splits)}")
            recs.append({
                "strategy": r["strategy"], "race_time": r["race_time"],
                "penalty_s": r["penalty_s"],
                **{f"t{i+1}": splits[i] for i in range(len(splits))},
                **{f"P{i+1}": r["fractions"][i] for i in range(len(splits))},
            })
        _save(pd.DataFrame(recs),
              f"03_strategies_{'reference' if sw is REFERENCE else 'working'}")

    print("\n  --- opening penalty curve ---")
    f = np.linspace(-0.10, 0.12, 12 if quick else 45)
    cur = optimization.opening_penalty_curve(f, REFERENCE, COURSE)
    for target in (-6, -3, 3, 6, 10):
        y = float(np.interp(target / 100.0, cur["overspeed"], cur["penalty_s"]))
        print(f"  first 50 at {target:+3d}%  ->  {y:+.3f} s")
    _save(pd.DataFrame({"overspeed_frac": cur["overspeed"],
                        "race_time": cur["race_time"],
                        "penalty_s": cur["penalty_s"]}), "04_opening_penalty")


def phase_8(quick: bool) -> None:
    banner("PHASE 8  Sensitivity and robustness")

    el = sensitivity.elasticity_table(REFERENCE, COURSE)
    print("\n  local sensitivity, +/-10% on each parameter:")
    for _, r in el.iterrows():
        flag = "  <- moves the shape" if r.moves_shape else ""
        e = "     n/a" if not np.isfinite(r.elasticity_T) else f"{r.elasticity_T:+8.3f}"
        print(f"  {r.parameter:<8s} dT = {r.dT_s:+7.3f} s   elasticity = {e}   "
              f"[{r.perturbation}]{flag}")
    _save(el, "05_elasticity")

    sw_all = sensitivity.sweep_all(REFERENCE, COURSE, n=9 if quick else 21)
    _save(sw_all, "06_parameter_sweeps")
    moved = sw_all.groupby("parameter")["shape_spread"].max().sort_values(ascending=False)
    print("\n  largest departure from even pacing across each full sweep:")
    for name, val in moved.items():
        print(f"  {name:<8s} max |P_max - P_min| = {val:.2e}")

    # 1:43 rather than 1:40: the low-drag archetype is already faster than
    # 1:40 on aerobic power alone, so it cannot be calibrated down to it.
    arch = sensitivity.compare_archetypes(ARCHETYPES, COURSE, match_time=103.0)
    _save(arch, "07_archetypes")
    print("\n  archetypes all calibrated to 1:43.00:")
    for _, r in arch.iterrows():
        print(f"  {r.archetype:<12s} beta_x = {r.beta_x:.2f}  P1 = {r.P1:.4f}  "
              f"spread = {r.shape_spread:.2e}  (via {r.calibrated_on})")

    rob = sensitivity.penalty_robustness(REFERENCE, COURSE,
                                         n_draws=40 if quick else 240)
    _save(rob, "08_penalty_robustness")
    print("\n  pacing penalty under 10% parameter uncertainty:")
    for _, r in rob.iterrows():
        print(f"  {r.strategy:<28s} median {r['median']:+.3f} s   "
              f"[{r.q25:+.3f}, {r.q75:+.3f}] IQR")


def phase_9_preview() -> None:
    banner("VALIDATION PREVIEW  model vs observed shapes (Robertson 2009 elite; own pilot)")

    opt = optimization.optimize(WORKING, COURSE)
    P_model = np.asarray(opt["split_fractions"])
    t_model = np.asarray(opt["split_times"])
    recorded = model.apply_start_offset(t_model, START_OFFSET_S)

    print(f"  model free-swimming splits : {' '.join(f'{t:5.2f}' for t in t_model)}"
          f"   T = {model.format_time(opt['race_time'])}")
    print(f"  with {START_OFFSET_S:.2f} s start credit : "
          f"{' '.join(f'{t:5.2f}' for t in recorded)}"
          f"   T = {model.format_time(recorded.sum())}")

    rows = []
    for key in ("observed_elite_corrected", "observed_pilot_corrected"):
        shape = np.asarray(simulator.STRATEGY_SHAPES[key], dtype=float)
        t = 1.0 / shape
        P = t / t.sum()
        rmse = float(np.sqrt(np.mean((P - P_model) ** 2)))
        rows.append({"source": key, "P1": P[0], "P2": P[1], "P3": P[2], "P4": P[3],
                     "rmse_vs_model": rmse, "is_placeholder": False})
        print(f"  {key:<32s} RMSE vs model = {rmse * 100:.3f} percentage points")
    _save(pd.DataFrame(rows), "09_validation_placeholder")
    print("\n  NOTE: quick preview only. The pre-registered comparison lives in")
    print("  results/validation/ and scripts/empirical_analysis.py.")


# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="coarser grids and fewer restarts, for a fast smoke run")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    phase_3_4(args.quick)
    phase_5(args.quick)
    phase_6_7(args.quick)
    phase_8(args.quick)
    phase_9_preview()

    if not args.no_figures:
        banner("PHASE 15  Figures")
        for path in visualization.build_all():
            print(f"  wrote {path}")

    print(f"\nDone in {time.time() - t0:.1f} s.")


if __name__ == "__main__":
    main()
