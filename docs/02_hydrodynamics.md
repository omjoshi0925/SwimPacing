# Hydrodynamics: deriving the cost function

Phase 4. The point of this phase is that `C(v) = k v^p` should not have free
parameters chosen to make the answer come out nicely. Both `k` and `p` follow
from drag physics plus two efficiencies.

---

## 1. Drag

A swimmer moving at velocity `v` experiences active drag

```
F_D = (1/2) rho C_D A v^2
```

- `rho`, water density, kg/m^3
- `C_D`, drag coefficient, dimensionless
- `A`, effective frontal area, m^2

The quadratic form assumes fully turbulent flow with a drag coefficient roughly
constant across the velocity range actually raced, about 1.6 to 2.0 m/s. Over
that narrow band this is reasonable. It would not be across a range including
gliding off a wall.

The three parameters only ever appear as a product, so define

```
K_d = (1/2) rho C_D A       [N s^2 / m^2]
```

With the defaults (`rho = 997`, `C_D = 0.30`, `A = 0.230`) this gives
`K_d = 34.4`.

Both `C_D` and `A` are **measured** values (Zamparo et al. 2009: `C_D` = 0.30 ±
0.09 for elite males in active drag; active frontal area 0.23-0.24 m²), and the
resulting product is independently checked against directly measured lumped
coefficients: 38 kg/m for elite male sprinters (Cortesi et al. 2024) and 22-30
for top swimmers (Toussaint 2002). 34.4 sits inside that spread.

**These values were corrected.** The model previously used `C_D` = 0.70 and
`A` = 0.090 m². Both were outside every measured value found, in opposite
directions, so their product looked right while neither factor was defensible.
See `docs/literature_notes.md`. Two lessons worth keeping: a lumped parameter
agreeing with the literature does not validate its components, and **passive**
frontal area (0.13-0.21 m²) is smaller than **active** area and is the wrong
quantity for a swimming model.

**Consequence for sensitivity analysis.** `rho`, `C_D` and `A` are not three
independent parameters. Their elasticities are identical by construction. And
`rho` varies by well under 1% across any legal competition temperature, so a
sensitivity analysis that swings it by 10% is reporting a fiction.

---

## 2. From drag to power, and the exponent

Power is force times velocity, so the rate of work done against drag is

```
P_d = F_D v = K_d v^3
```

**This is where `p = 3` comes from.** It is a consequence of a quadratic drag law,
not a modelling choice. A 5% increase in velocity requires about a 16% increase
in power.

---

## 3. From mechanical power to metabolic cost

Two efficiencies stand between the swimmer's metabolism and useful forward work.

**Propelling efficiency `eta_p`.** Not all mechanical work delivered to the water
produces thrust; some is left behind as kinetic energy in the wake. Default 0.60,
from Toussaint & Beek (1992), who report 61% in elite swimmers versus 44% in
triathletes. The literature spread is wide: ≈0.40 (Cortesi et al. 2024, elite
male sprinters) to 0.65-0.71 (Kolmogorov et al. 2021).

**Gross mechanical efficiency `eta_g`.** The fraction of metabolic energy that
becomes mechanical work at all. Default 0.20, from Zamparo et al. (2005).

**This is the least settled number in the model.** Kolmogorov et al. (2021)
report 0.049-0.068 for elite swimmers, a factor of 3-4 lower. The disagreement is
definitional rather than experimental: labs differ on what counts as useful
mechanical power and what metabolic baseline is subtracted. The consequence is
that **`k` is not identifiable from the literature**, so every absolute energy
figure this model produces is model-internal.

So

```
C(v) = P_d / (eta_p eta_g) = [ K_d / (eta_p eta_g) ] v^3
```

giving

```
k = K_d / (eta_p eta_g)   and   p = 3
```

With the defaults, the free-swimming coefficient is
`k_free = 34.40 / 0.12 = 286.6 W s^3 / m^3`. The model actually uses
`k = phi * k_free`, where `phi` is the course economy factor (see
`docs/parameters.md`), because the event is raced in a 25 yard pool.

### Sanity check at race pace

At the optimal `v* = 1.829 m/s`:

| quantity | value |
|---|---|
| drag force `F_D` | 115 N |
| power against drag `P_d` | 210 W |
| total mechanical power `P_d / eta_p` | 351 W |
| metabolic rate `C(v*)`, at `phi` = 1 | 1753 W |
| free-swimming cost per metre | 959 J/m |

The metabolic rate exceeds the aerobic ceiling `R` = 1250 W, which is required:
a 200 free is a supramaximal effort sustained by drawing down the reserve. A
model producing a race pace *below* the aerobic ceiling would be wrong.

**An unresolved check.** Capelli et al. (1998) report front-crawl energy cost
rising from 0.70 kJ/m at 1.0 m/s to 1.23 kJ/m at 1.5 m/s, and continuing to rise
exponentially. Extrapolating to 1.83 m/s puts free-swimming cost well above the
model's 959 J/m, so the model looks **cheap** relative to the free-swimming
literature. That is the direction `phi` is meant to absorb, since SCY racing
includes turns and underwaters that are cheaper per metre. But the size should be
checked once those figures are confirmed against the PDF: if the gap is much
larger than turns can explain, the cost function is wrong somewhere.

---

## 4. Varying the exponent honestly

`p` is derived, but it should still be tested, since the quadratic drag law is
an idealization and measured active-drag exponents run a little above 2.

Naively changing `p` while holding `k` fixed also changes the absolute cost at
race pace, so a "sensitivity to `p`" study would really be measuring a rescaling
of `k`. To avoid that, `k` is **re-anchored** whenever `p` moves, so that
`C(v_ref)` is preserved at a reference velocity `v_ref = 1.8288 m/s`:

```
k(p) = k3 * v_ref^3 / v_ref^p
```

This isolates the effect of curvature from the effect of level. See
`Swimmer.k` in `parameters.py`.

---

## 5. What the hydrodynamics do and do not control

Sweeping `C_D`, `A`, `rho`, `eta_p` and `eta_g` by ±25% and re-optimizing:

- **Race time moves a lot.** A 10% change in `C_D` is worth several seconds.
- **The optimal pacing shape does not move at all.** The first-50 share stays at
  25.00000% to eight decimal places across the entire sweep.

This is not a numerical coincidence. It is Result 2 in `01_derivation.md`: the
optimal shape depends only on the weights `wi`, and no hydrodynamic parameter
enters them. Figure `fig04_drag_sensitivity` is the picture of it, and the flat
right-hand panel is the finding.

**Practical reading.** A swimmer who reduces drag gets faster. They do not get a
different optimal race plan. Streamlining and pacing are separate problems, and
this model says so cleanly.

---

## 6. What the drag model leaves out

- **Wave drag** rises steeply near hull speed and is lumped into a constant
  `C_D` here. At 200 pace this is a real omission.
- **Turns and underwaters.** Underwater dolphin kicking has a different drag
  regime and a different economy. In SCY there are seven turns, so this is the
  single largest unmodelled effect in the whole project.
- **Intra-cycle velocity fluctuation.** Real velocity oscillates within each
  stroke. Since cost is convex in `v`, using the mean velocity *understates* the
  true cost, and the error grows with the size of the fluctuation.
- **Body position degrading with fatigue.** A tired swimmer's hips drop and `A`
  rises. This is not modelled as a changing `A`, but it is exactly the physical
  story behind the `beta_x` economy-decay term in `03_ode_model.md`.
