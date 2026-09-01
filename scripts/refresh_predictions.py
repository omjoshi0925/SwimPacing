#!/usr/bin/env python3
"""
Recompute PREDICTED_SHAPES_SCY200 in src/parameters.py.

Run this after changing anything in MODELS. The path-dependent models take about
a minute each, which is why the values are cached rather than solved per use.

    python -m scripts.refresh_predictions
"""
import os, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

import numpy as np
from src import model, optimization
from src.parameters import MODELS, SCY_200

for name, sw in MODELS.items():
    if model._closed_form_ok(sw):
        P = np.asarray(model.optimal_solution_closed_form(sw, SCY_200)["split_fractions"])
        how = "closed form"
    else:
        P = np.asarray(optimization.optimize_full(sw, SCY_200, n_starts=4)["split_fractions"])
        how = "ODE solver"
    vals = ", ".join(f"{x:.6f}" for x in P)
    print(f'    "{name}":{" " * (22 - len(name))}({vals}),   # {how}')
