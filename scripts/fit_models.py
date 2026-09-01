"""
Fit the fatigue parameters on TRAINING rows only (Task 14 entry point).

The sanctioned fitting path: data comes from `calibration.training_frame`
(which withholds the registered held-out test rows), every frame passes the
structural leakage guard before any objective is evaluated, and the run writes
one auditable CSV via `calibration.write_fit_report`.

    python -m scripts.fit_models --models M3            # fast, closed form
    python -m scripts.fit_models --models M4 M2         # ODE fits, minutes each
    python -m scripts.fit_models --out results/validation/fits_train_pilot.csv

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

PROCESSED = "data/processed/200_free_scy_processed.csv"
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
    ap.add_argument("--exploratory", action="store_true", default=True,
                    help="label rows exploratory (pilot-era default; the "
                         "registered run on the expanded frozen dataset "
                         "will unset this deliberately)")
    args = ap.parse_args()

    train, meta = calibration.training_frame(args.processed)
    calibration.assert_no_test_rows(train, args.processed)
    shares = calibration.observed_shares(train)
    print(f"training rows: {meta['n_train_races']} races / "
          f"{meta['n_train_swimmers']} swimmers (seed {meta['seed']}); "
          f"test rows withheld: {meta['n_test_races_unopened']}")

    meta = dict(meta, exploratory=bool(args.exploratory),
                dataset="pilot-v0.1", loss="mean per-race RMSE of split "
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
