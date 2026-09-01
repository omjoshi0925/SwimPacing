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
| start-corrected (1.8 s) | 21.65% | 25.59% | 26.48% | 26.28% |

Mean half difference +4.54 s (positive split).
Mean lap-1 to lap-2 drop +2.72 s; mean lap-3 to lap-4
drop -0.23 s. The fade is overwhelmingly front-loaded,
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
| M0 | constant economy | 1.99 ± 0.34 | 0 |
| M1 | oxygen kinetics | 1.99 ± 0.34 | 0 |
| M2 | reserve fatigue | 3.80 ± 0.39 | 0 |
| M3 | position fatigue | 1.55 ± 0.32 | 0 |
| M4 | velocity ceiling | 1.40 ± 0.32 | 80 |

Reading, with small-n caution:

1. **M2 is contradicted.** Its predicted negative split has the wrong sign
   against every single race. This was the pre-registered expectation, and it
   is the one claim n = 80 can support, because it is a sign, not a
   magnitude.
2. **The front-loaded family (M4) tracks the data best**, and the observed
   drop pattern (large lap-1 to 2, none lap-3 to 4) is qualitatively M4's
   signature rather than M3's even fade. Ranking, not proof.
3. **Every model is beaten by the data's own front-loadedness.** Observed
   corrected lap-1 share (21.65%) is below even M4's prediction
   (23.96%). Either the start credit is too small, or a
   mechanism is missing (see below), or both.

## Start effect (Phase 7)

Mean lap-1 velocity 1.733 m/s vs mid-race 1.548 m/s.
Lap 1 is faster than the mid-race laps by 3.23 ±
1.08 s.

The literature-implied dive value for elite males is only about
3.0-3.3 s at this field's race
pace (measured 15 m start times of 6.1-6.4 s against covering 15 m at race
speed). **The observed lap-1 advantage is therefore roughly 1 s larger than
the dive alone explains.** The excess is pacing behaviour and fresh-swimmer
physiology, which is exactly why the start credit must come from start-time
measurements and never be estimated from lap differences — doing so would
absorb genuine pacing into the correction.

Ranking stability: across the whole pre-registered start-credit band
(1.2-2.8 s), the best-fitting model is **M4 at every
value** (see pilot_start_sensitivity.csv). The descriptive ranking does not
depend on the weakest number in the model.

Verdict on the Phase 7 question: **yes, a dedicated start term appears
necessary.** A constant credit is serviceable for shape comparison, but lap 1
mixes three separable effects (dive, underwater share, fresh-swimmer cost) that
an eight-segment model with an explicit start phase should separate. beta_x
fitted without that separation would absorb the residual.

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
