# Pilot empirical report — first real races through the pipeline

Date: 2026-08-31. Dataset version: **pilot-v0.1** (see data provenance below).

## What this is, and is not

This is the Phase 5-7 pipeline test on the first real data: descriptive
statistics, the first observed-versus-predicted comparison, and the start-effect
check. It is **not** the pre-registered held-out model comparison. No parameter
was fitted to any of this data, the swimmer-level train/test split has been
generated and recorded but **the test set has not been evaluated against any
fitted model**, and with n = 80 races from a single meet nothing here is
a strong conclusion.

## Correction (2026-09-01)

An earlier version of this report compared model raced-space shapes against
observed shares that had the start credit SUBTRACTED from lap 1 — the
model-side transform applied to the data as well, double-counting the credit
by twice its value on lap 1. All corrected quantities now ADD the credit back
to lap 1 (the free-swimming-equivalent race; `model.recorded_to_raced`).
Every number below reflects the fix. Superseded findings: "every model is
beaten by the data's own front-loadedness" and "the observed lap-1 advantage
is ~1 s beyond the dive value" were artifacts of the double-count; the model
RMSEs reported earlier (M4 1.40 pp etc.) were inflated by it. The amendment
is logged in `docs/validation_plan.md`.

## Dataset

| | |
|---|---|
| Raw rows ingested | 581 |
| Usable races (all quality gates passed) | 80 |
| Source of every usable race | Official Hy-Tek results, Orinda Aquatics SCY Senior Open, Jan 25-26 2025, Sanction #25-010, Boys 200 Yard Freestyle, pacswim.org (checksum-verified retrieval, 2026-08-31) |
| Population of usable races | male, ages 15-18, SCY, timed finals |
| Unique swimmers (usable) | 80 |
| Final time range | 1:37.01 to 2:25.17 (mean 1:55.84) |
| Age distribution (usable) | {15: 26, 16: 25, 17: 22, 18: 7} |

Excluded rows, by blocking reason (a row can carry several flags):
missing splits 449 (the 449 SwimCloud
rows, which publish no splits); course mismatch 166
(Far Western is LCM); age outside 15-18 or unknown 501
(includes all SwimCloud rows, which publish no ages, and 52 Orinda
swims aged 12-14 or 19+). Zero rows failed monotonicity, final-time match,
plausibility, or duplication — the official file is internally consistent.

## Observed pacing (n = 80)

| | lap 1 | lap 2 | lap 3 | lap 4 |
|---|---|---|---|---|
| recorded share | 22.88% | 25.19% | 26.06% | 25.87% |
| free-swimming equivalent (+1.8 s to lap 1) | 24.06% | 24.80% | 25.66% | 25.47% |

Mean half difference +4.54 s (positive split).
Mean lap-1 to lap-2 drop +2.72 s recorded, of which the
dive accounts for 1.8 s, leaving
+0.92 s of genuine pacing fade; mean lap-3 to
lap-4 drop -0.23 s. The pacing fade is front-loaded,
and the final lap is on average slightly FASTER than the third — a finishing
kick that no cost-based model produces.

External check: Robertson et al. (2009), 200 m free international finalists
(men, LCM), show the same family of shape — laps 23.5 / 25.2 / 25.7 / 25.6% —
fast first lap, then a flat back half with no terminal fade. The pilot swimmers
are more front-loaded than those elites, consistent with both their age and
SCY underwater time.

## First model comparison (descriptive)

Start-corrected RMSE against each model's predicted split distribution:

| model | mechanism | mean RMSE (pp) | races where best |
|---|---|---|---|
| M0 | constant economy | 0.73 ± 0.37 | 21 |
| M1 | oxygen kinetics | 0.73 ± 0.37 | 0 |
| M2 | reserve fatigue | 2.59 ± 0.43 | 0 |
| M3 | position fatigue | 0.51 ± 0.28 | 20 |
| M4 | velocity ceiling | 0.49 ± 0.25 | 39 |

Reading, with small-n caution:

1. **M2 is contradicted.** It predicts a negative split; 73 of
   80 races are positively split in the free-swimming-equivalent space.
   This was the pre-registered expectation, and it is the one claim
   n = 80 can support, because it is a sign, not a magnitude.
2. **The positive-split family fits closely, and M4 vs M3 is not settled by
   RMSE.** Against the mean observed shape the residuals are
   M4 0.19 pp and M3 0.26 pp — a gap far inside
   race-to-race noise. The sharper discriminator is the drop pattern: the
   pacing fade is concentrated between laps 1 and 2
   (+0.92 s) with none at the end
   (-0.23 s), which is M4's signature (predicted
   0.99 s / 0.24 s) rather than M3's even fade (0.53 s / 0.49 s).
3. **The observed mean shape sits ON the front-loaded model family.** At the
   elite-anchored credit the corrected lap-1 share (24.06%) lands
   between M4 (23.96%) and M0 (25.00%), close to M3
   (24.22%); where exactly it lands moves with the start
   credit (see below), which is now the decisive unknown.

## Start effect (Phase 7)

Mean lap-1 velocity 1.733 m/s vs mid-race 1.548 m/s.
Lap 1 is faster than the mid-race laps by 3.23 ±
1.08 s.

The dive value implied by elite 15 m start times at THIS field's race pace is
3.0-3.3 s (measured 15 m start
times of 6.1-6.4 s against covering 15 m at the field's mean race speed).
**The observed lap-1 advantage (3.23 s) is
consistent with the dive alone.** Note the tension inside the constant-credit
assumption: the model's elite-anchored 1.8 s is what the dive
is worth at elite pace, while at this slower field's pace the same start is
worth about 3.2 s, because
the dive's fixed 15 m advantage is measured against slower swimming. A single
constant cannot be right for both. The credit must still come from start-time
measurements rather than lap differences — estimating it from lap differences
would absorb genuine pacing into the correction.

Ranking across the pre-registered start-credit band (1.2-2.8 s):
**the winner changes across the band** (M4 at 1.2 s, M0 at 2.8 s; full grid in pilot_start_sensitivity.csv). The model ranking therefore DEPENDS on the start credit, which promotes measuring it from housekeeping to decisive.

Verdict on the Phase 7 question: **a dedicated, pace-aware start term is the
single highest-leverage improvement.** The lap-1 advantage no longer exceeds
the dive value, so no extra mechanism is required there; but the model ranking
moves with the assumed credit, and a constant credit is provably wrong across
paces. An explicit start phase (Task 19), or at minimum a per-race
S(v) = 15/v - t15 credit, is what removes this degree of freedom. beta_x or
gamma fitted without it will absorb the residual.

## Train/test split (generated, not consumed)

Grouped by swimmer, seed 20260829: 60 train /
20 test races (60/20
swimmers, overlap 0). Recorded here so the assignment is
frozen before any calibration happens. Note the pilot has
0 swimmers with more than one usable
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
