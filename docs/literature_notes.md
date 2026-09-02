# Literature notes

Task 3: **22 verified sources** against a target of 15-30 (10 from the
2026-08-29 hydrodynamics pass, 9-12 from the 2026-08-31 physiology/start/pacing
pass, including three energetics sources verified in a companion session and
recorded in the project's `energetics_literature_sources.md`).

Files: `literature/references.bib`, `literature/literature_review.csv`.

---

## Status and what is missing

Coverage by topic after the two passes:

| Topic | Status |
|---|---|
| Active drag, drag coefficient, frontal area | **done**, 5 sources |
| Propelling and mechanical efficiency | **done**, 4 sources |
| Energy cost of swimming vs velocity | **done**, 2 sources |
| Aerobic/anaerobic contribution, 200 free | **done**: 65.9% (Figueiredo 2011) to 78.6% (Sousa 2011) aerobic — a real 13-point spread, carry as a range |
| VO2 kinetics in swimming | **done**: tau 9.6-17.8 s across all full-text sources; 16.5 s adopted |
| Anaerobic capacity, adolescents | **done**: AOD 3.2 ± 1.3 L (Campos 2022), E0 anchor |
| Observed 200 free pacing | **done**: Robertson 2009 (n=3057), McGibbon 2020, Oliveira 2023, Menting 2022 (abstract) |
| Dive start | **done**: measured 15 m start times 6.1-8.2 s by level, implying 1.7-3.0 s dive value at 200 pace |
| Turn time contributions | **done** (2026-09-01, 5 full-text sources): turn sections are ~51% of 200 SC race time (vs ~33% LC); push-off 2.96 vs swim 1.41 m/s; within-swimmer underwater 21-28% faster than surface; world-class 100 SC is 39% non-swimming time |
| Critical swimming speed (numeric CS/W') | confirmed to exist (Toussaint 1998; Zacca 2010) but paywalled; **no numbers yet** |
| Mathematical models of athletic performance (Keller line) | **not started** |
| Optimal control in endurance sport | **not started** |

Items 1-4 of the previous "highest-value remaining" list are now closed. The
model's implied anaerobic share (28.7% for M0) sits inside the measured
21.3-34.1% band — the plausibility check is now literature-bounded rather than
assumed. **Remaining searches**, in order: turn and underwater time
contributions in short course (what `phi` stands in for); numeric critical
speed and W' values (papers identified, paywalled); Keller (1974) and the
optimal-control-in-running line for positioning the paper.

---

## Verification policy

Every entry in the `.bib` was confirmed to exist through a search result or a
fetched page. **Nothing was reconstructed from memory.** Each entry records how
far verification got:

- **full text read**: the numbers are quoted from the paper itself.
- **abstract only**: numbers come from the abstract. Check against the PDF
  before they appear in the paper.
- **metadata only**: existence and bibliographic details confirmed, publisher
  page blocked. **No numbers extracted.**

Across the 22 sources: 14 full text, 5 abstract-only or partial, 3 metadata
only. Three energetics entries were verified by a companion session on
2026-08-29 under the same policy and are recorded in the project's
`energetics_literature_sources.md` with per-number access marks.

Notably, the three sources most often cited in this area (Kolmogorov &
Duplishcheva 1992, Toussaint et al. 1988, Havriluk 2007) are precisely the three
that could only be confirmed at metadata level. Values usually attributed to
Toussaint 1988 are quoted here through Toussaint's own 2002 proceedings paper
instead, and labelled as such.

**A caution worth recording.** An initial search targeted a researcher named
"Zamparini", who does not exist in this literature. The real and prolific author
is **Paola Zamparo**. Two of the load-bearing sources here are hers. Half-
remembered author names are exactly how fabricated citations enter a
bibliography, and the correct response is to search, find nothing, and say so.

---

## What the literature changed in the model

Three findings, in descending order of consequence.

### 1. Two drag parameters were outside every measured value

The model used `C_D` = 0.70 and `A` = 0.090 m². Measured values:

| | model (old) | measured | source |
|---|---|---|---|
| `C_D` | 0.70 | 0.30 ± 0.09 (elite males, active); range 0.23-0.61 | Zamparo 2009, Kolmogorov 2021 |
| `A` | 0.090 m² | 0.23-0.24 m² active; 0.13-0.21 m² passive | Zamparo 2009 |

Both were wrong, in opposite directions, so their **product** landed near the
measured lumped coefficient while each factor sat outside the evidence. That is
a specific and instructive failure mode: a lumped parameter agreeing with the
literature does not validate its components, and a reviewer checking components
would find it immediately.

Corrected to `C_D` = 0.30 and `A` = 0.230, giving `K_d` = 34.4, which sits
inside the independently measured band (38 kg/m in Cortesi 2024; 22-30 in
Toussaint 2002). The decomposition is now defensible as well as the product.

A related trap: **passive frontal area is smaller than active area** and is the
wrong quantity for a swimming model. Using a passive figure would understate
drag by roughly half.

### 2. Gross mechanical efficiency is not a settled number

| Source | Reported efficiency | Population |
|---|---|---|
| Zamparo et al. 2005 | 0.20 ± 0.03 (overall) | swimmers, 1.0-1.4 m/s |
| Kolmogorov et al. 2021 | 0.049-0.068 (mechanical) | 8 world top-10 swimmers |

A factor of 3-4, between two legitimate peer-reviewed sources. The gap is
**definitional**, not experimental: labs differ on what counts as useful
mechanical power and what metabolic baseline is subtracted.

**Consequence: `k` is not identifiable from the literature.** Every absolute
energy figure this model produces is model-internal and cannot be compared with
published energy costs without stating the efficiency convention. This is now
flagged in `parameters.py`, `docs/parameters.md` and the README.

Propelling efficiency has the same problem in milder form: 0.40 (Cortesi 2024),
0.61 (Toussaint & Beek 1992), 0.65-0.71 (Kolmogorov 2021). A factor of 1.8.

### 3. The drag exponent may not be exactly 2

Berger et al. (1999), reported in Toussaint 2002, measured `F_d = 16.4·v^2.22`
rather than a clean quadratic. That implies `p` = 3.22 rather than 3.

This does **not** threaten any conclusion, because the central even-pacing
result holds for every `p` > 1 and the optimal shape depends on `p` only weakly.
It does mean the p-sweep in the sensitivity analysis is exercising a real
uncertainty rather than a hypothetical one.

---

## Model-relevant numbers, collected

Everything numeric that was verified, with its access level. Anything marked
[abstract] or [metadata] needs PDF confirmation before publication.

| Quantity | Value | Source | Access |
|---|---|---|---|
| Lumped drag `K` | 22-30 (top swimmers) | Toussaint 2002 | full text |
| Active drag `k_a` | 38 kg/m | Cortesi 2024 | full text |
| Passive drag `k_p` | 25 kg/m | Cortesi 2024 | full text |
| Drag exponent | 2.22 | Berger 1999 via Toussaint 2002 | full text |
| `C_D` active | 0.30 ± 0.09 | Zamparo 2009 | abstract |
| `C_D` range | 0.33-0.61 | Kolmogorov 2021 | full text |
| Frontal area active | 0.23-0.24 m² | Zamparo 2009 | abstract |
| Frontal area passive | 0.13-0.21 m² | Zamparo 2009 | abstract |
| `eta_p` | 0.61 elite / 0.44 triathlete | Toussaint & Beek 1992 | abstract |
| `eta_p` | ≈0.40 | Cortesi 2024 | full text |
| `eta_p` | 0.65-0.71 | Kolmogorov 2021 | full text |
| `eta_g` | 0.20 ± 0.03 | Zamparo 2005 | abstract |
| `eta_g` | 0.049-0.068 | Kolmogorov 2021 | full text |
| Energy cost | 600-800 J/m at 1.0-1.4 m/s | Zamparo 2005 | abstract |
| Energy cost | 0.70 kJ/m at 1.0 → 1.23 kJ/m at 1.5 m/s | Capelli 1998 | abstract, **flagged** |
| Metabolic power | 3346-3560 W (elite males, 100 m) | Kolmogorov 2021 | full text |

**An unresolved check.** The model's free-swimming cost at race pace is about
960 J/m. Capelli 1998 reports 1230 J/m at 1.5 m/s and rising exponentially,
which extrapolates well above 960 at 1.83 m/s. The model therefore looks
**cheap** relative to the free-swimming literature. That is consistent with what
`phi` is for (SCY racing includes turns and underwaters that are cheaper per
metre), but the sign and rough size should be checked properly once the Capelli
figures are confirmed against the PDF. If the gap turns out to be much larger
than turns can explain, the cost function is wrong somewhere.

---

## Turns and underwater phases (added 2026-09-01)

The gap the previous pass called "the biggest remaining" is now closed with
five full-text sources (verification agent-assisted, same policy: nothing
reported that was not actually fetched; access levels in the .bib).

What the numbers establish, in the model's terms:

1. **Turn sections dominate short-course racing.** Using the standard section
   definition (5 m into the wall + 10 m out), turns account for
   **50.84 ± 0.28% of 200 m SC race time** (Cuenca-Fernández 2022, elite men
   and women) against ~33% in long course; Born 2021 independently gives
   ~51.8-52.7% for women's 200 SC free. The turn sections cover 57% of the
   distance in ~51% of the time, i.e. they are swum meaningfully faster than
   the surface sections.
2. **The wall is a speed subsidy.** Push-off velocity 2.96 ± 0.14 m/s against
   free swimming at 1.41 ± 0.06 m/s in the same SC races (Born 2022, IM);
   within the same swimmers, underwater dolphin kick runs 1.76-1.86 m/s vs
   1.43-1.45 m/s surface (Veiga 2022, youth national team) — a 21-28%
   within-swimmer premium. At world-class level, 39% of a SC 100 free is
   non-swimming time (Pla 2021).
3. Still missing at full text: 200-free-specific underwater usage (Veiga &
   Roig 2016, metadata only) and absolute elite freestyle turn times (Born's
   male-benchmark paper, metadata only).

This is precisely the physical content of `phi`: a large fraction of an SCY
race is ridden on wall push-offs and underwater kicking that move the swimmer
faster than surface swimming at plausibly lower propulsive cost per metre.
The quantitative synthesis (what band this implies for `phi`) lives in
`docs/parameters.md` under the phi entry.
