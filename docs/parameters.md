# Parameter provenance

Every parameter in the model, where its value came from, and how much weight it
can bear. Tasks 2 and 4.

**Read the classification first.** Nothing below is a measurement of any real
swimmer. Category A values are literature values for *other* populations,
transplanted here. Category B values were chosen to make the model reproduce a
plausible race. Category C values exist only to explore behaviour.

---

## Status of this document

Updated 2026-08-31 after two further verified literature passes (energetics,
2026-08-29, recorded in the project's `energetics_literature_sources.md`; dive
start and observed pacing, 2026-08-31). The physiological block now carries real
citations: `tau` is a measured swimming value, `E0` and `R` have age-relevant
literature anchors, and the start credit is bracketed by measured 15 m start
times. Remaining genuine gaps: a clean absolute VO2max for trained 15-18 males,
and numeric critical-speed/W' values (two directly relevant papers confirmed to
exist but paywalled; see literature notes).

---

## Classification

**Category A, literature-supported.** A published, verifiable measurement exists
for the quantity, in a population close enough to be arguable.

| Parameter | Symbol | Value |
|---|---|---|
| Water density | `rho` | 997 kg/m³ |
| Drag coefficient | `C_D` | 0.30 |
| Active frontal area | `A` | 0.230 m² |
| Propelling efficiency | `eta_p` | 0.60 |
| Gross mechanical efficiency | `eta_g` | 0.20 (contested, see below) |
| Cost exponent | `p` | 3.0 (derived from quadratic drag) |

**Category B, calibrated.** Chosen so the model reproduces known race behaviour.
These are model parameters that happen to carry physiological names. They are
**not** measurements and must never be described as such.

| Parameter | Symbol | Value | Calibrated against |
|---|---|---|---|
| Aerobic ceiling | `R` | 1250 W | 1:40.0 optimum jointly with E0; literature-plausible (see entry) |
| Effective energy reserve | `E0` | 50.32 kJ | 1:40.0 optimum for M0 at `phi` = 1; anchored by measured AOD (see entry) |
| Course economy factor | `phi` | 0.77-1.00 by model | 1:40.0 optimum for each variant |

**Category C, exploratory.** Used for sensitivity analysis and to define
competing models. No claim that any value is the true one.

| Parameter | Symbol | Value | Purpose |
|---|---|---|---|
| Oxygen kinetics time constant | `tau` | 16.5 s | M1-M4; **moved to Category A**, measured (see entry) |
| Reserve-coupled fatigue | `beta_E` | 0.28 | defines M2 |
| Position-coupled fatigue | `beta_x` | 0.28 | defines M3 |
| Fatigue-coupled ceiling | `gamma` | 0.18 | defines M4 |
| Velocity ceiling | `v_max` | 2.10 m/s | box constraint; slack in M0-M3 |
| Velocity floor | `v_min` | 1.20 m/s | keeps the solver in physical territory |
| Start credit | `START_OFFSET_S` | 1.80 s | comparison only; literature-anchored band 1.7-3.0 s (see entry) |

### Language rules that follow from this

Do not write "the swimmer has an anaerobic reserve of 50 kJ". Write "the model
uses an effective energy-reserve parameter `E0` = 50 kJ, calibrated to reproduce
a 1:40 optimum". The same applies to `R`, `tau`, and every `beta`.

---

## Full records

### rho — water density

- **Symbol:** ρ
- **Default:** 997 kg/m³
- **Units:** kg·m⁻³
- **Description:** density of the pool water; enters only through `K_d`.
- **Source:** standard physical property of fresh water at 25-28 °C.
- **Method of selection:** physical constant at legal competition temperature.
- **Plausible range:** 996.5-997.5 across any legal pool (25-28 °C).
- **Status:** **Measured / physical.**
- **Identifiable from race data:** no, and it does not need to be.
- **Notes:** varies by well under 1%. Any sensitivity analysis that swings ρ by
  10% is reporting a fiction; it is excluded from the elasticity figure for that
  reason. ρ, `C_D` and `A` enter only as a product, so their elasticities are
  identical by construction.

### C_D — drag coefficient

- **Symbol:** C_D
- **Default:** 0.30
- **Units:** dimensionless
- **Description:** drag coefficient of the swimming body.
- **Source:** Zamparo, Gatta, Pendergast & Capelli (2009), *Active and passive
  drag: the role of trunk incline*, Eur J Appl Physiol 106(2):195-205.
- **Source population:** 6 male elite swimmers, age 20.0 ± 1.3 y (active drag
  group).
- **Method of selection:** reported mean for active drag in elite males.
- **Plausible range:** 0.23-0.43 (Zamparo 2009, across conditions); 0.33-0.61
  (Kolmogorov et al. 2021, elite swimmers, four strokes).
- **Status:** **Literature-based**, abstract-level verification.
- **Identifiable from race data:** no. Split times cannot separate C_D from A.
- **Notes:** **This value was changed.** The model previously used C_D = 0.70,
  which is above every measured value found. It had been chosen together with a
  too-small frontal area so that their product landed in the right place. Both
  are now set to measured values independently.

### A — active frontal area

- **Symbol:** A
- **Default:** 0.230 m²
- **Units:** m²
- **Description:** effective frontal area presented to the flow while swimming.
- **Source:** Zamparo et al. (2009), as above.
- **Source population:** 25 swimmers (14 M, 11 F), values for active swimming.
- **Method of selection:** reported active-swimming value, 0.23-0.24 m².
- **Plausible range:** 0.23-0.40 m² active; 0.13-0.21 m² passive.
- **Status:** **Literature-based**, abstract-level verification.
- **Identifiable from race data:** no.
- **Notes:** **This value was changed** from 0.090 m², which was below every
  measured value found. Passive area is smaller than active area and is the
  wrong quantity for a swimming model; using a passive figure is an easy and
  consequential mistake.

### K_d — lumped drag factor (derived)

- **Symbol:** K_d = ½ρC_D A
- **Value:** 34.40 N·s²·m⁻²
- **Derived from:** ρ, C_D, A above.
- **External check:** Cortesi, Gatta, Carmigniani & Zamparo (2024) measure an
  active-drag coefficient of 38 kg·m⁻¹ in 14 elite male sprinters; Toussaint
  (2002) reports 22-30 for top swimmers. The derived 34.4 sits inside that
  spread, which is a genuine independent check on the decomposition.
- **Status:** **Derived from Category A inputs.**

### eta_p — propelling efficiency

- **Symbol:** η_p
- **Default:** 0.60
- **Units:** dimensionless
- **Description:** fraction of mechanical work delivered to the water that
  produces useful thrust rather than wake kinetic energy.
- **Source:** Toussaint & Beek (1992), *Biomechanics of competitive front crawl
  swimming*, Sports Medicine 13(1):8-24, reporting 61% in elite swimmers versus
  44% in triathletes.
- **Plausible range:** 0.40 (Cortesi et al. 2024, elite male sprinters) to
  0.71 (Kolmogorov et al. 2021, elite 100 m swimmers). Wide and method-dependent.
- **Status:** **Literature-based**, abstract-level verification.
- **Identifiable from race data:** no.
- **Notes:** the spread is a factor of 1.8. Treat 0.60 as a central value inside
  a wide band, not as a known quantity.

### eta_g — gross mechanical efficiency

- **Symbol:** η_g
- **Default:** 0.20
- **Units:** dimensionless
- **Description:** fraction of metabolic energy that becomes mechanical work.
- **Source:** Zamparo, Pendergast, Mollendorf, Termin & Minetti (2005), *An
  energy balance of front crawl*, Eur J Appl Physiol 94:134-144, reporting
  overall efficiency 0.20 ± 0.03.
- **Plausible range:** **0.05 to 0.23, and the disagreement is not noise.**
  Kolmogorov, Vorontsov & Vilas-Boas (2021) report mechanical efficiency of
  0.049-0.068 in elite swimmers. That is a factor of 3-4 against Zamparo's 0.20.
- **Status:** **Literature-based but contested.**
- **Identifiable from race data:** no.
- **Notes:** **This is the least settled number in the model and the most
  important caveat in this document.** The gap is definitional, not
  experimental: labs differ on what counts as useful mechanical power and what
  metabolic baseline is subtracted. The direct consequence is that `k` is *not
  identifiable from the literature*, so every absolute energy figure the model
  produces is model-internal and must not be compared with published energy
  costs without stating which efficiency convention is in play.

  **Correct unit conversion.** Efficiency is the fraction of metabolic energy
  that becomes mechanical work, so the conversion is a multiplication:

  ```
  mechanical energy = metabolic energy × efficiency
  ```

  E0 = 50.32 kJ metabolic → 50.32 × 0.20 = 10.06 kJ total mechanical work, of
  which 50.32 × η_p × η_g = 50.32 × 0.12 = 6.04 kJ is delivered against drag.
  An earlier version of this repository said "divide", which inflates the figure
  by roughly an order of magnitude. Fixed.

### phi — course economy factor

- **Symbol:** φ
- **Default:** 1.000 (M0), 0.858 (M1), 0.747 (M2), 0.754 (M3), 0.811 (M4)
- **Units:** dimensionless
- **Description:** multiplies the cost coefficient, `k = φ·K_d/(η_p·η_g)`.
  Represents the per-metre cost reduction of racing in a 25 yard pool relative
  to free swimming at the same mean velocity.
- **Source:** none. This is the model's one openly calibrated scalar.
- **Method of selection:** solved so each model variant produces a 1:40.0
  optimum with the same engine parameters.
- **Plausible range:** 0.6-1.0. φ = 1 claims no course advantage at all.
- **Status:** **Calibrated (Category B).**
- **Identifiable from race data:** only jointly with `E0`; see the identifiability
  section below.
- **Notes:** this parameter exists so the model's missing physics has a name and
  a number instead of being hidden inside an efficiency. A 200 SCY contains a
  dive start, seven turns and eight underwater phases across 182.88 m, and those
  phases are faster and cheaper per metre than surface swimming. φ = 0.75 claims
  that discount is 25%.

  Two things make φ useful rather than merely convenient. It is **comparable
  across model variants**: a variant needing φ far from 1 is demanding a large
  unexplained economy, which is evidence against it. And it gives Task 19 a
  falsifiable target: an explicit eight-segment start-and-turn model should
  drive φ toward 1, and if it does not, the discount was never about turns.

### p — cost exponent

- **Symbol:** p
- **Default:** 3.0
- **Units:** dimensionless
- **Description:** exponent in C(v) = k·v^p.
- **Source:** **derived**, not assumed. Power against a quadratic drag law is
  P = F·v = K_d·v³.
- **Plausible range:** 3.0-3.22. Berger et al. (1999, reported in Toussaint
  2002) measured a drag-force exponent of 2.22 rather than 2.00, which implies
  p = 3.22. Swept from 2.0 to 4.5 in the sensitivity analysis.
- **Status:** **Derived from Category A inputs.**
- **Identifiable from race data:** in principle yes, jointly with the fatigue
  parameters, but the optimal shape depends on p only weakly.
- **Notes:** the central even-pacing result holds for every p > 1, so no
  conclusion in this project rests on p being exactly 3.

### R — aerobic ceiling

- **Symbol:** R
- **Default:** 1250 W
- **Units:** W (metabolic)
- **Description:** maximum sustained rate of oxidative energy supply. Plays the
  role of critical power.
- **Source for the value:** none; calibrated jointly with E0.
- **Method of selection:** chosen so that race pace is supramaximal (metabolic
  cost at the optimum, 1753 W, exceeds R), which a 200 requires.
- **Plausibility anchor (2026-08-31):** R = 1250 W metabolic is 1250/20.9 ≈
  59.8 mL O2/s ≈ 3.59 L/min, i.e. ≈52.8 mL/kg/min for a 68 kg swimmer — below
  the measured VO2max of 57.9 ± 5.1 mL/kg/min in well-trained adult male
  swimmers (Pessoa Filho et al. 2012), as a sustainable ceiling should be.
  A clean absolute VO2max for trained males aged 15-18 specifically was NOT
  found and remains a gap.
- **Status:** **Calibrated (Category B), literature-plausible.** Still never a
  measurement of any swimmer.
- **Identifiable from race data:** weakly, and only from swimmers racing several
  distances.
- **Notes:** do not describe this as the swimmer's aerobic capacity.

### E0 — effective energy reserve

- **Symbol:** E0
- **Default:** 50 320 J
- **Units:** J (metabolic, not mechanical)
- **Description:** finite energy store usable above R. Plays the role of W'.
- **Source for the value:** none; solved so M0 with φ = 1 gives a 1:40.0
  optimum.
- **Plausibility anchor (2026-08-31):** measured accumulated oxygen deficit in
  age-matched swimmers (14.9 ± 2.6 y, Campos et al. 2022, full text) is
  3.2 ± 1.3 L O2 ≈ 67 ± 27 kJ metabolic (at 20.9 kJ/L). E0 = 50.3 kJ sits
  inside that band's lower half, sensible for the usable-in-race reserve
  relative to a to-exhaustion deficit.
- **Status:** **Calibrated (Category B), literature-anchored.**
- **Identifiable from race data:** only jointly with φ. See below.
- **Notes:** implies an anaerobic share of 28.7% of total race energy for M0.
  That figure is *output*, not input, and it has not yet been checked against a
  published anaerobic-contribution measurement for the 200 freestyle. Doing so
  is a high-value validation check once the physiology literature is in.

### tau — oxygen kinetics time constant

- **Symbol:** τ
- **Default:** 16.5 s (updated from the exploratory 20 s on 2026-08-31)
- **Units:** s
- **Description:** R(t) = R(1 − e^(−t/τ)).
- **Source:** Pessoa Filho, Alves, Reis, Greco & Denadai (2012), IJSM
  33(9):744-748: τ = 16.5 ± 5.1 s at severe intensity, 17.8 ± 5.9 s heavy
  (male, well-trained, full text). Sousa et al. (2011), IJSM 32(10):765-770:
  τ = 10.53 ± 2.51 s in elite males swimming 200 m at actual race pace (full
  text). Pelarigo et al. (2017): 9.6-16.3 s, female, submaximal (full text).
- **Plausible range:** 9.6-17.8 s across every swimming-specific full-text
  measurement found. None reaches the old 20 s value.
- **Status:** **Literature-supported (Category A)** for the value; note the
  populations are adult, not 15-18.
- **Identifiable from race data:** no. τ changes race time and leaves the optimal
  split shape exactly unchanged at this calibration, for every value tested up to
  200 s, so split sheets carry no information about it.
- **Notes:** with a much smaller reserve the energy path constraint can bind and
  the shape does then move slightly. That is a model boundary, not a
  physiological claim, and it does not occur near the calibrated parameters.

### beta_E, beta_x, gamma — fatigue parameters

- **Defaults:** `beta_E` = 0.28 (M2), `beta_x` = 0.28 (M3), `gamma` = 0.18 (M4);
  all zero in M0 and M1.
- **Units:** dimensionless.
- **Source:** none. These *define* the competing models rather than describing a
  measured swimmer.
- **Method of selection:** magnitudes chosen to produce a clearly visible
  departure from even pacing, comparable in size to real split distributions.
- **Status:** **Exploratory (Category C).** They become fitted parameters in
  Task 14, at which point their fitted values are estimates, still not
  measurements.
- **Identifiable from race data:** **yes, and this is the point of the project.**
  These are the only parameters in the model that change the optimal pacing
  shape, so the shape is exactly the observable that informs them.
- **Notes:** the physiological basis for `beta_x` is now cited: Figueiredo et
  al. (2011, full text) measured arm-stroke propelling efficiency of 0.40-0.43
  falling significantly from lap 1 to lap 4 of a 200 m front crawl race
  (p = 0.002), and lap energy cost of 1.71/1.56/1.44/1.70 kJ/m. Within-race
  economy decay is real and measured. The MAGNITUDE of `beta_x` remains
  exploratory until fitted, and the lap-cost profile they measure is U-shaped
  rather than linear, which cautions against the linear form as more than a
  first approximation.

### v_max, v_min — kinematic bounds

- **Defaults:** 2.10 and 1.20 m/s.
- **Source:** none; assumed.
- **Status:** **Assumed (Category C).**
- **Notes:** `v_max` is slack at the optimum in M0-M3, so it does not affect
  those results at all. It is load-bearing only in M4, where the ceiling falls
  with fatigue and binds. For a 100 free it would bind and the structure of the
  answer would change.

### START_OFFSET_S — dive start credit

- **Default:** 1.80 s
- **Units:** s
- **Description:** time credited back to split 1 when comparing model
  free-swimming splits with recorded splits.
- **Source (anchor, 2026-08-31):** measured elite male 15 m start times are
  6.12 ± 0.16 s (Tor, Pease & Ball 2014, n=29, full text) and 6.41 ± 0.45 s
  (Rudnik, Rejman & Vilas-Boas 2023, n=22 international, full text). Covering
  15 m at a 200-pace velocity of 1.6-1.85 m/s takes 8.1-9.4 s, so the dive is
  worth roughly 1.7-3.0 s depending on level and pace. 1.80 s is the
  conservative end of that measured band.
- **Empirical cross-check (pilot, n=80):** lap 1 is 2.8 ± 0.5 s faster than
  the mid-race laps — about 1 s MORE than the dive band explains. That excess
  is pacing and fresh-swimmer effects, which is precisely why this credit must
  come from start-time measurements and never from lap differences.
- **Status:** **Literature-anchored estimate (Category B).** Upgraded from
  Category C on 2026-08-31; still not a per-swimmer measurement.
- **Identifiable from race data:** yes, from 15 m split times, which is the
  single highest-value optional column in the data schema.
- **Notes:** **this is the weakest number in the project and it sits directly on
  the main theory-versus-data comparison.** It pushes observed splits in the same
  direction as `beta_x`, so fitting `beta_x` without a good start correction will
  absorb the dive into the fatigue parameter and overstate it. Because it is a
  constant subtracted from split 1, it shifts T by a constant and cannot change
  which velocity profile is optimal, which is why it is applied only at
  comparison time and never inside the optimizer.

---

## Identifiability

Which parameters can race data actually inform? This matters more than
plausibility, because a parameter the data cannot see is a parameter the model
comparison cannot judge.

| Parameter | Informed by split shape? | Informed by race time? | Verdict |
|---|---|---|---|
| `beta_E`, `beta_x`, `gamma` | **yes, strongly** | weakly | **identifiable** |
| `p` | weakly | yes | weakly identifiable |
| `E0`, `R` | no | yes, jointly | not separately identifiable |
| `phi` | no | yes, jointly with E0/R | not separately identifiable |
| `C_D`, `A`, `rho`, `eta_p`, `eta_g` | **no, provably** | only through their product | not identifiable |
| `tau` | no (below 40 s) | yes | not identifiable from splits |
| `START_OFFSET_S` | yes, confounded with `beta_x` | yes | identifiable only with 15 m splits |

Two structural facts drive this table, both proved in `docs/01_derivation.md`:

1. The optimal split distribution is `P_i ∝ w_i^(1/p)` with
   `w_i = 1 + beta_x·x̄_i/L`. Nothing else enters. So split shape informs the
   fatigue parameters and `p`, and literally nothing else.
2. `k`, `E0`, `R` and `phi` trade off against each other in the race-time
   equation. A single race time is one equation in four unknowns.

**Consequence for Task 14.** Only the fatigue parameters should be fitted to
pacing data. Fitting `E0`, `R` or `phi` to split shapes will produce
meaningless estimates, because the shape does not depend on them. They should be
fixed by calibration to race time and held there, and the paper should say so.

---

## Changes made in this revision

| What | From | To | Why |
|---|---|---|---|
| `C_D` | 0.70 | 0.30 | old value above every measured value found |
| `A` | 0.090 m² | 0.230 m² | old value below every measured value found |
| `E0` | 35 kJ (M0) / 82 kJ (working) | 50.32 kJ, shared | recalibrated after the drag fix; one engine across all variants |
| `phi` | did not exist | 0.75-1.00 by variant | names the SCY turn and underwater discount instead of hiding it |
| Efficiency wording | "divide by efficiency" | "multiply by efficiency" | the old wording was wrong by an order of magnitude |
| `tau`, `R`, start credit | implied literature backing | marked PROVENANCE GAP | no verified citation yet |

The old C_D and A were individually indefensible even though their product was
about right. That is worth stating plainly: a lumped parameter landing in the
measured range does not make its factors correct, and a reviewer who checks the
components will notice.
