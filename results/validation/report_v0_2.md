# Registered held-out evaluation — pilot-v0.2

Generated 2026-09-03T02:04:16Z. Dataset pilot-v0.2 (frozen 2026-09-03). Registered split seed 20260829: training 256 races / 188 swimmers, held-out 89 races / 60 swimmers. **The test set was first opened by this script at 2026-09-03T02:00:12Z**; this run re-executes the same registered evaluation (post-hoc supplements are labelled). Start credit 1.80 s (elite-anchored; validation_plan §7).

## Exclusion funnel (validation_plan §10)

| step | rows |
|---|---|
| raw rows | 1382 |
| with complete cumulative splits | 832 |
| … monotonic | 832 |
| … |split_200 − final| ≤ 0.05 s | 832 |
| … every 50 within 0.5-2.0× race mean | 832 |
| … not a duplicate | 832 |
| … SCY | 832 |
| … male 15-18 (published or club-linked age) | 345 |
| usable (shape analysis) | 345 |
| usable with pre-race PB (H1) | 110 |

## Registered calibration (training side only)

| model | parameter | fitted | registry | bounds | training loss (pp) |
|---|---|---|---|---|---|
| M3_position_fatigue | beta_x | 0.2277 | 0.28 | [0, 1.5] | 0.4645 |
| M0_constant_economy | — | — | — | — | 0.6529 |
| M4_velocity_ceiling | gamma | 0.2687 | 0.18 | [0.02, 0.45] | 0.4608 |
| M2_reserve_fatigue | beta_E | 0.0200 | 0.28 | [0.02, 1] | 0.7644 |

## Held-out comparison (§3, §4)

| model | mean RMSE (pp) | 95% CI | MAE (pp) | Δ vs best (pp) | Δ 95% CI | sign(P4−P1) | best in n races |
|---|---|---|---|---|---|---|---|
| M0 | 0.653 | [0.568, 0.759] | 0.583 | +0.200 | [+0.144, +0.262] | +0 | 20 |
| M1 | 0.653 | [0.568, 0.759] | 0.583 | +0.200 | [+0.144, +0.262] | +0 | 0 |
| M2 | 0.771 | [0.682, 0.880] | 0.693 | +0.317 | [+0.256, +0.385] | -1 | 2 |
| M3 | 0.454 | [0.398, 0.523] | 0.394 | +0.000 | — | +1 | 30 |
| M4 | 0.461 | [0.415, 0.515] | 0.402 | +0.007 | [-0.019, +0.030] | +1 | 37 |

Observed held-out mean shares (free-swimming equivalent, %): P1 = 24.15 [23.97, 24.29], P2 = 24.76 [24.70, 24.83], P3 = 25.56 [25.46, 25.67], P4 = 25.53 [25.42, 25.65].
Discriminating statistic: drop 1→2 = +0.75 s [+0.56, +0.99], drop 3→4 = -0.03 s [-0.18, +0.10] (after adding the start credit to lap 1).

### §4 criteria, applied mechanically

- Observed sign of P4 − P1: +1. Models with the matching sign: M3, M4. Shape winner: **none (more than one model class matches)**.
- Lowest held-out RMSE: M3. Accuracy winner (CI of every pairwise difference excludes zero): **none**.
- Registered conclusion: **the data do not distinguish these models on held-out accuracy (§4)**.

## Start-credit band on the held-out set (§7)

Fitted parameters held at their 1.80 s training values; only the credit applied to the held-out data moves.

| credit (s) | M0 | M1 | M2 | M3 | M4 | best | sign(P4−P1) |
|---|---|---|---|---|---|---|---|
| 1.2 | 0.835 | 0.835 | 0.960 | 0.526 | 0.454 | M4 | +1 |
| 1.4 | 0.769 | 0.769 | 0.893 | 0.491 | 0.445 | M4 | +1 |
| 1.6 | 0.708 | 0.708 | 0.830 | 0.466 | 0.447 | M4 | +1 |
| 1.8 | 0.653 | 0.653 | 0.771 | 0.454 | 0.461 | M3 | +1 |
| 2.0 | 0.606 | 0.606 | 0.717 | 0.453 | 0.483 | M3 | +1 |
| 2.2 | 0.569 | 0.569 | 0.671 | 0.463 | 0.514 | M3 | +1 |
| 2.4 | 0.543 | 0.543 | 0.634 | 0.482 | 0.550 | M3 | +1 |
| 2.6 | 0.529 | 0.529 | 0.607 | 0.509 | 0.593 | M3 | +1 |
| 2.8 | 0.526 | 0.526 | 0.590 | 0.542 | 0.640 | M0 | +1 |
| 3.0 | 0.531 | 0.531 | 0.583 | 0.582 | 0.691 | M0 | +1 |
| 3.2 | 0.544 | 0.544 | 0.585 | 0.628 | 0.745 | M0 | +1 |
| 3.4 | 0.564 | 0.564 | 0.594 | 0.678 | 0.803 | M0 | -1 |

Ranking changes inside the band: **M4 → M3 → M0**. Per §7 item 3, the data cannot distinguish the surviving models given start uncertainty.

### Supplementary: M3 refitted at each credit (training side), scored held-out

| credit (s) | beta_x (train) | held-out RMSE M3 (pp) | held-out RMSE M0 (pp) |
|---|---|---|---|
| 1.2 | 0.3335 | 0.491 | 0.835 |
| 1.4 | 0.2965 | 0.474 | 0.770 |
| 1.6 | 0.2612 | 0.461 | 0.708 |
| 1.8 | 0.2277 | 0.454 | 0.653 |
| 2.0 | 0.1967 | 0.452 | 0.606 |
| 2.2 | 0.1672 | 0.455 | 0.569 |
| 2.4 | 0.1391 | 0.463 | 0.543 |
| 2.6 | 0.1118 | 0.476 | 0.530 |
| 2.8 | 0.0852 | 0.492 | 0.526 |
| 3.0 | 0.0595 | 0.513 | 0.531 |
| 3.2 | 0.0345 | 0.536 | 0.544 |
| 3.4 | 0.0103 | 0.562 | 0.564 |

## Published-age stratum (club-linked rows removed)

Held-out races 73 / swimmers 60. M0 0.706 [0.618, 0.807]; M1 0.706 [0.618, 0.807]; M2 0.827 [0.735, 0.930]; M3 0.469 [0.403, 0.544]; M4 0.463 [0.407, 0.526]. Conclusion: the data do not distinguish these models on held-out accuracy (§4).

## H1: deviation vs performance (§8)

Races with a pre-race PB: 110 (71 swimmers; all usable races, not only held-out ones — H1 is not a model-selection step, and the deviation D uses the training-fitted shapes). I = (PB − T)/PB in percent; D in pp, centered.

| stratum | D vs | n races / swimmers | method | b1 (% per pp) | 95% CI | b2 (% per pp²) | 95% CI | RE var | resid var |
|---|---|---|---|---|---|---|---|---|---|
| registered: every race with a pre-race PB | M0 | 110 / 71 | mixed | -1.463 | [-4.616, +1.690] | +0.776 | [-5.208, +6.760] | 16.835 | 7.776 |
| post-hoc supplement: PB within 365 days | M0 | 85 / 65 | mixed | -0.044 | [-2.661, +2.572] | +0.254 | [-4.735, +5.244] | 8.814 | 4.325 |
| registered: every race with a pre-race PB | M2 | 110 / 71 | mixed | -2.418 | [-5.256, +0.419] | +1.334 | [-4.021, +6.689] | 17.291 | 7.329 |
| post-hoc supplement: PB within 365 days | M2 | 85 / 65 | mixed | -0.776 | [-3.178, +1.626] | +1.582 | [-3.043, +6.207] | 8.949 | 4.188 |
| registered: every race with a pre-race PB | M3 | 110 / 71 | mixed | +0.383 | [-4.089, +4.856] | +14.719 | [+6.269, +23.169] | 9.351 | 8.973 |
| post-hoc supplement: PB within 365 days | M3 | 85 / 65 | mixed | +2.623 | [-1.333, +6.578] | +0.370 | [-8.820, +9.561] | 9.060 | 3.906 |
| registered: every race with a pre-race PB | M4 | 110 / 71 | mixed | +1.040 | [-3.715, +5.796] | +19.875 | [+9.478, +30.271] | 8.221 | 9.223 |
| post-hoc supplement: PB within 365 days | M4 | 85 / 65 | mixed | +1.815 | [-2.552, +6.181] | +3.153 | [-8.908, +15.213] | 9.109 | 3.975 |

The post-hoc supplement (added after the first run; exploratory, not registered) keeps only races whose pre-race PB was set within 365 days: in the registered set the three largest improvements (29%, 14%, 13%) were measured against PBs swum four years earlier, at ages 13-14, which are not expectations.

H1 is supported only if b1 < 0 with a CI excluding zero (closer to the optimum → better relative to expectation) and the curvature is consistent with a penalty; otherwise the registered null is reported as a null (§9).

## Files

`results/validation/model_comparison.csv`, `results/validation/holdout_start_sensitivity.csv`, `results/validation/h1_regression.csv`, figures `figures/empirical/emp06-08`.
