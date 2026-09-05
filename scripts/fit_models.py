"""
Fit the fatigue parameters on TRAINING rows only (Task 14 entry point).

The sanctioned fitting path: data comes from `calibration.training_frame`
(which withholds the registered held-out test rows), every frame passes the
structural leakage guard before any objective is evaluated, and the run writes
one auditable CSV via `calibration.write_fit_report`.

    python -m scripts.fit_models --models M3            # fast, closed form
    python -m scripts.fit_models --models M4 M2         # ODE fits, minutes each
    python -m scripts.fit_models --out results/validation/fits_train_pilot.csv

The REGISTERED calibration (validation_plan §6, run once on the training side
of the frozen pilot-v0.2 dataset) is an explicit mode, never the default:

    python -m scripts.fit_models --registered --dataset pilot-v0.2 \
        --out results/model_calibration/fits_train_v0_2.csv

Rows merge into an existing report CSV by model, so per-model runs can land
separately without clobbering each other.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import calibration  # noqa: E402
from src.parameters import MODELS  # noqa: E402
from src.preprocessing import PROCESSED_CSV as PROCESSED  # noqa: E402
DEFAULT_OUT = "results/validation/fits_train_pilot.csv"

FITTERS = {
    "M3": lambda shares: calibration.fit_beta_x(shares),
    "M4": lambda shares: calibration.fit_gamma(shares),
    "M2": lambda shares: calibration.fit_beta_E(shares),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="+", default=["M3", "M4", "M2"],
                    choices=sorted(FITTERS), help="which models to fit")
    ap.add_argument("--processed", default=PROCESSED)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--registered", action="store_true",
                    help="label rows as the registered calibration (not "
                         "exploratory); requires --dataset naming a FROZEN "
                         "version in data/DATASET_VERSIONS.md")
    ap.add_argument("--dataset", default="pilot-v0.1",
                    help="dataset version label recorded in the report")
    args = ap.parse_args()
    if args.registered and args.dataset == "pilot-v0.1":
        ap.error("pilot-v0.1 fits are exploratory by declaration "
                 "(validation_plan, 2026-09-01); name the frozen dataset")

    train, meta = calibration.training_frame(args.processed)
    calibration.assert_no_test_rows(train, args.processed)
    shares = calibration.observed_shares(train)
    print(f"training rows: {meta['n_train_races']} races / "
          f"{meta['n_train_swimmers']} swimmers (seed {meta['seed']}); "
          f"test rows withheld: {meta['n_test_races_unopened']}")

    meta = dict(meta, exploratory=not args.registered,
                dataset=args.dataset, loss="mean per-race RMSE of split "
                "proportions (pp), validation_plan §3")

    fits = []
    for key in args.models:
        print(f"fitting {key} ...", flush=True)
        fit = FITTERS[key](shares)
        fits.append(fit)
        print(f"  {fit.model}: {fit.param} = {fit.value:.4f} "
              f"(registry {getattr(MODELS[fit.model], fit.param):.2f}), "
              f"loss {fit.loss_pp:.4f} pp vs registry {fit.baseline_pp:.4f} pp, "
              f"{fit.n_evals} evals")

    baselines = {"M0_constant_economy":
                 calibration.mean_rmse_pp(np.full(4, 0.25), shares)}

    if os.path.exists(args.out):
        old = pd.read_csv(args.out)
        new = calibration.fit_report_frame(fits, meta, baselines)
        merged = pd.concat([old[~old["model"].isin(new["model"])], new],
                           ignore_index=True)
        merged.to_csv(args.out, index=False)
        print(f"merged {len(new)} rows into {args.out}")
    else:
        calibration.write_fit_report(args.out, fits, meta, baselines)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
