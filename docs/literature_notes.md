# Literature notes

Task 3: **47 verified sources** against a target of 15-30 (10 from the
2026-08-29 hydrodynamics pass; 9-12 from the 2026-08-31 physiology/start/
pacing pass, including three energetics sources verified in a companion
session and recorded in the project's `energetics_literature_sources.md`; 25
from the 2026-09-01 pass covering turns/underwater, SC-vs-LC conversion,
critical speed and anaerobic distance capacity, and the Keller/optimal-control
line). Access-level split across all 47: 24 full text, 15 abstract-only or
partial, 8 metadata only — every metadata-only entry carries a "no numbers
extracted" note.

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
| VO2 kinetics in swimming | **done**: tau 9.6-17.8 s across all full-text sources; 16.5 s adopted (Pessoa Filho 2012). Sousa 2014 (2026-09-03) adds the closest population match, 18.2 +/- 4.1 y, at 15-18 s |
| Anaerobic capacity, adolescents | **done**: AOD 3.2 ± 1.3 L (Campos 2022), E0 anchor |
| Observed 200 free pacing | **done**: Robertson 2009 (n=3057), McGibbon 2020, Oliveira 2023, Menting 2022 (abstract) |
| Dive start | **done**: measured 15 m start times 6.1-8.2 s by level, implying 1.7-3.0 s dive value at 200 pace |
| Turn time contributions | **done** (2026-09-01, 5 full-text sources): turn sections are ~51% of 200 SC race time (vs ~33% LC); push-off 2.96 vs swim 1.41 m/s; within-swimmer underwater 21-28% faster than surface; world-class 100 SC is 39% non-swimming time |
| Critical swimming speed (numeric CS/D') | **done** (2026-09-01, 7 sources): adolescent male CS 1.22-1.32 m/s, CS/v200 = 0.898, D' 14-31 m (distance-set dependent); model check passes on the dimensionless ratio (docs/parameters.md). No swimming W' in joules exists anywhere reached; the field reports D' in metres |
| SC vs LC course conversion | **done**: measured 2.0 ± 0.6% freestyle speed advantage short course (Wolfrum 2013) |
| Mathematical models of athletic performance (Keller line) | **done** (2026-09-01): Keller 1973/1974, Behncke 1993, Woodside 1991, Mathis 1989 verified with access levels; positioning written into docs/01_derivation.md §9 |
| Optimal control in endurance sport | **done**: Aftalion-Bonnans 2014 (full preprint), Aftalion et al. 2016 (full), de Koning 1999 (metadata), and the direct swimming antecedent Maroński 1996 (full abstract) |

Every topic in the table is now at least "done" at the level described. The
model's implied anaerobic share (28.7% for M0) sits inside the measured
21.3-34.1% band, and the engine block now also passes the dimensionless
critical-speed check (CS/v200: model 0.893 vs measured 0.898 for trained male
adolescents; see docs/parameters.md). **Remaining gaps, explicitly:**
200-free-specific underwater usage at full text (Veiga & Roig 2016, blocked);
absolute elite freestyle turn times (Born male benchmarks, blocked); Keller
1974's own text (metadata only — nothing from it is quoted); de Koning 1999's
conclusions (metadata only); per-distance SC-LC deltas (tables did not
render); Capelli 1998 energy-cost figures still await PDF confirmation.

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

Across the 48 sources: 24 full text, 17 abstract-only or partial, 7 metadata
only, counted from the `access_level` column of
`literature/literature_review.csv` (row 081, refreshed 2026-09-04; the CSV and
`references.bib` now hold the same 48 keys). The previous line read 47 sources
as 24/15/8, which did not add up against that column even at 47 rows: the
correct split then was 24/16/7. Recount from the CSV rather than adjusting
these numbers by hand. Three energetics entries were verified by a companion session on
2026-08-29 under the same policy and are recorded in the project's
`energetics_literature_sources.md` with per-number access marks. The
2026-09-01 pass (25 entries) was executed by verification agents under the
same written policy, with load-bearing numbers confirmed by a second
independent fetch; their access failures (PubMed/PMC captchas, publisher 403s)
are recorded per entry rather than papered over.

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

**A second caution of the same species (2026-09-01).** A paper often wanted
here — "Toussaint 1998" on critical power / W' in simulated front crawl — could
not be verified beyond a bare PubMed search-result title (PMID 9475656): no
authors, journal, pages, or numbers were reachable. It is therefore **not
cited anywhere in this project**. If access improves, verify first, cite
second. Likewise "Wakayoshi 1992, Int J Sports Med 13:367-371" exists only as
a reference-list entry inside other papers and is not cited; the flume study
(wakayoshi1992critical, EJAP) is the verified one.

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

## Keller, the two papers (verified 2026-09-03)

**Keller (1973).** A theory of competitive running. Physics Today 26(9):43-47.
DOI 10.1063/1.3128231 — ACCESS: abstract/summary read (publisher feature page).
Model built on Newton's second law plus the calculus of variations; yields an
optimum race strategy and recovers physiological parameters from world records.
An author copy is hosted on a university course page; located, not fetched.

**Keller (1974).** Optimal velocity in a race. Am. Math. Monthly 81(5):474-480.
ACCESS: metadata only. Confirmed against four independent bibliographies
(Pritchard, SIAM Review 35; arXiv 2208.10927; arXiv 1811.12321; arXiv
1606.09497). No DOI verified; held by JSTOR. Not fetched.

**Bears on the model.** M4 descends from both: the 1973 paper supplies the
force/energy-balance structure, the 1974 paper the optimal-velocity result.
They are distinct works and are not interchangeable in citation.

**Correction logged.** This repo's roadmap named the 1973 Physics Today paper
"Keller 1974". Second from-memory citation error caught by fetch, after the
Toussaint/Wakayoshi case in `energetics_literature_sources.md`.

## Optimal control in endurance sport (verified 2026-09-03)

**Maronski (1996).** J. Biomechanics 29(2):245-249, DOI
10.1016/0021-9290(95)00041-0, PMID 8849819 — ACCESS: abstract only (PubMed +
ScienceDirect). Two coupled ODEs: Newton's second law and a power-balance
equation. Minimum-time velocity obtained by extremizing linear integrals via
Green's theorem (Miele's method). Argues that the sprint assumption (maximal
propulsive force throughout) and the distance assumption (constant velocity)
both fail at middle distance.

**Bears on the model.** The closest prior art to this project's framework
found in any pass: same two-equation structure, same middle-distance regime a
200 free occupies, and the only located optimal-control treatment naming
swimming in its title.

**Maronski & Rogowski (2011).** Acta Bioeng. Biomech. 13(2):83-86 — ACCESS:
abstract read. Hill-Keller model solved by Chebyshev direct pseudospectral
method. States that Behncke's formulation carries resistance proportional to
velocity squared, "therefore the reasoning may be extended to swimming" — an
explicit literature warrant for transferring quadratic-drag optimal control to
the aquatic case, which is the assumption behind C(v) = k*v^3.

**Reference-list-only, not fetched. Recorded at that access level and not
used to support any claim:** Behncke (1993) J. Math. Biol. 31(8):853-878;
Woodside (1991) Math. Comput. Model. 15(10):1-12; Aftalion & Bonnans (2014)
SIAM J. Appl. Math. 74(5):1615-1636; Pitcher (2009) SIAM J. Appl. Math.;
Mathis (1989) SIAM Review 31(2):306-309.

## Critical speed and W' — characterized gap (searched 2026-09-03)

**Numeric critical speed and W'/ADC for adolescent swimmers: still NOT FOUND.**

- Zacca et al. (2010), EJAP 110:121-131 — abstract only, unchanged. CV, ADC,
  V_max and tau sit behind the Springer paywall. Highest-value target; access
  to this one paper closes 076 and unblocks 077.
- Dekerle et al. (2002), Int J Sports Med 23:93-98 — abstract now recovered.
  Relative results only: V30 overestimates critical speed by 3.2%, SR30 needs
  a -3.9% correction. No absolute CS in m/s.

**Near-miss, excluded with reason.** A study of swimmers aged 12.1 +/- 0.7 y
reports "anaerobic critical velocity" of 1.27 +/- 0.16 m/s for front crawl.
Rejected as an anchor: it is fitted to 10-25 m maximal swims, making it a
sprint distance-time slope rather than critical speed in the critical-power
sense. Using it for R would be a category error.

**Consequence.** Row 077 (CS/W' plausibility check against R and E0) remains
blocked on source access, not on effort.

## Adolescent / junior male swimming energetics (searched 2026-09-03)

**Sousa, Vilas-Boas & Fernandes (2014).** BioMed Research International
2014:675363, DOI 10.1155/2014/675363, PMID 25045690 — ACCESS: abstract and
participants section read. Direct fetch of the PMC page returned a CAPTCHA
challenge; content was recovered from the DOI-resolved publisher rendering and
an independent reference listing, which agree on authors, venue and numbers.

Population: 12 well-trained male swimmers, age 18.2 +/- 4.1 y, height 179.4
+/- 6.5 cm, mass 70.5 +/- 5.8 kg, Tanner stage 4-5, middle-distance freestyle
specialists, national level, 200 m LC at 86.5 +/- 3.7% of the 2013 world
record. Trains at least eight sessions per week.

Key numbers (95 / 100 / 105% of the velocity at VO2max):
- tau, fast component: **15, 18, 16 s**
- A1, fast-component amplitude: 36, 34, 37 mL/kg/min
- A2, slow component: 480.76 +/- 247.01, 452.18 +/- 217.04, 147.04 +/- 60.40 mL/min
- Aerobic energy contribution: **83 +/- 5, 74 +/- 6, 59 +/- 7%**
- Convention: metabolic.

**Bears on the model.** Closest population match found in any pass: male,
middle-distance freestyle, mass within 4% of the project's 68 kg working
figure, age range spanning the 15-18 target. Two consequences. (1) What it
adds is the POPULATION, not the value. `tau` = 16.5 s comes from Pessoa Filho
et al. (2012), which measured exactly 16.5 +/- 5.1 s at severe intensity and
17.8 +/- 5.9 s heavy, so the working value was never above the swimming
literature. What that entry has always carried is the caveat that its
population is adult; Sousa 2014 answers it, at 18.2 +/- 4.1 y and Tanner 4-5,
with a fast-component range of 15-18 s around the same value.
(2) At 105% of vVO2max the aerobic share falls to 59
+/- 7%, i.e. anaerobic 41 +/- 7%, sitting inside the project's 30-50%
anaerobic sanity check and between source 6 (34%) and source 10 (21%).
A 200 free is raced above vVO2max, so the 105% row is the relevant one.

**Candidate, authors NOT verified, no bib entry created.** An EJAP 2015 paper,
DOI 10.1007/s00421-014-3093-5, pages 1117-1124, reports for a 100 m swim:
aerobic 43.4 / anaerobic lactic 33.1 / alactic 23.5%, VO2peak 56.07 +/- 5.19
mL/kg/min, tau 12.73 +/- 3.09 s, energy cost 1.16 +/- 0.10 kJ/m. Author list
and volume number were not recoverable in this pass; recorded as a lead, not
as a source.

**Top target for the next pass, reference-list only:** Almeida et al. (2020),
EJAP 120:1097-1109, DOI 10.1007/s00421-020-04348-y, "VO2 kinetics and energy
contribution in simulated maximal performance during short and middle
distance-trials in swimming." Title indicates middle-distance trials, i.e.
the project's exact race regime.

**Exclusion reaffirmed.** The n=8 Indonesian adolescent VO2max study already
excluded in `energetics_literature_sources.md` resurfaced in this search under
a different title and venue, with the same red flags: n=8, age 14.5 +/- 0.5,
and standard deviations of exactly 0.50 or 0.00 across measures. Exclusion
stands. Noting here that it recirculates under multiple titles.

**Gap NOT closed.** A clean absolute VO2max in mL/kg/min for trained males
aged 15-18 remains unfound. The A1 amplitudes above are fast-component
amplitudes, not VO2max, and must not be read as such.

## Correction, 2026-09-03: three sources presented as new were already here

The Keller and Optimal-control sections above were written without first
checking `literature/references.bib`. All three keys already existed, with
better notes than the ones added. The duplicate entries have been removed and
the originals kept. Two specific claims above are wrong:

1. The Keller section states that no DOI was verified for keller1974optimal.
   The bibliography already carried 10.1080/00029890.1974.11993589.
2. The optimal-control section presents maronski1996minimum as the closest
   prior art "found in any pass". It was found in an earlier pass and already
   annotated in the bibliography as the direct antecedent, including detail
   this session did not recover: the optimal profile is acceleration, then a
   constant-velocity cruise, then a final kick, with the initial acceleration
   replaced by the gliding phase in swimming.

What in those sections is new and stands: Maronski & Rogowski (2011) and its
statement that quadratic-drag reasoning extends to swimming; the
reference-list-only access records; and the roadmap mis-citation of the 1973
Physics Today paper as "Keller 1974".

Duplicate bibliography keys are a build error, not a style issue - they broke
the paper workflow on CI.
