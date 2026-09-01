"""
Parameter definitions for the 200 freestyle pacing optimization model.

Unit convention (SI throughout the internal model):
    distance   metres
    velocity   metres / second
    time       seconds
    force      newtons
    power      watts (joules / second)
    energy     joules

The event is 200 yards short course (SCY). Distances are converted to metres
at the boundary so that the hydrodynamic model stays in SI. Split times are
reported in seconds, which is course independent.

Every default in this file is traceable to a published value or to an
explicit calibration step. See docs/02_hydrodynamics.md and
docs/parameters.md for the provenance of each number.
"""

from __future__ import annotations

from dataclasses import dataclass, replace, asdict

YARD_M = 0.9144

# ---------------------------------------------------------------------------
# Course geometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Course:
    """Geometry of the raced event."""

    name: str
    split_distance_m: float  # distance covered by one recorded split
    n_splits: int
    pool_length_m: float

    @property
    def total_distance_m(self) -> float:
        return self.split_distance_m * self.n_splits

    @property
    def n_turns(self) -> int:
        return int(round(self.total_distance_m / self.pool_length_m)) - 1


SCY_200 = Course(
    name="200 free SCY",
    split_distance_m=50.0 * YARD_M,  # 45.72 m
    n_splits=4,
    pool_length_m=25.0 * YARD_M,  # 22.86 m
)

LCM_200 = Course(
    name="200 free LCM",
    split_distance_m=50.0,
    n_splits=4,
    pool_length_m=50.0,
)


# ---------------------------------------------------------------------------
# Swimmer parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Swimmer:
    """
    Physiological and hydrodynamic parameters for a single swimmer.

    Hydrodynamic block
    ------------------
    See docs/parameters.md for the full provenance record. Every value below is
    a measured literature value or a stated calibration; none is chosen to make
    a result come out.

    rho     water density, kg/m^3. Competition pools run 25-28 C, rho ~= 997.
            Varies under 1% across any legal water temperature.
    Cd      drag coefficient of the swimming body, dimensionless.
            0.30 +/- 0.09, elite males, active drag (Zamparo et al. 2009).
            Measured range across that study 0.23-0.43; Kolmogorov et al. 2021
            report 0.33-0.61 for elite swimmers across four strokes.
    A       effective frontal area, m^2. 0.23-0.24 during active swimming
            (Zamparo et al. 2009). Passive values are smaller (0.13-0.21) and
            are NOT the right quantity here.
    eta_p   propelling efficiency: the fraction of mechanical work delivered to
            the water that produces useful thrust rather than kinetic energy
            left behind in the wake. The literature spread is wide and
            method-dependent: 0.61 elite vs 0.44 triathletes (Toussaint & Beek
            1992), ~0.40 elite male sprinters (Cortesi et al. 2024), 0.65-0.71
            elite 100 m swimmers (Kolmogorov et al. 2021).
    eta_g   gross mechanical efficiency: metabolic power converted to
            mechanical power.

            WARNING. This is the least settled number in the model. Zamparo et
            al. 2005 report overall efficiency 0.20 +/- 0.03; Kolmogorov et al.
            2021 report 0.049-0.068 for elite swimmers. That is a factor of 3-4,
            and it is definitional rather than measurement error (what counts as
            useful mechanical power, and what metabolic baseline is subtracted).
            The consequence is that k is NOT identifiable from the literature.
            Treat any absolute energy figure from this model as model-internal.

    Physiological block
    -------------------
    R       aerobic ceiling, W. The maximum sustained rate at which metabolic
            energy can be supplied oxidatively. Plays the role of critical
            power in the two-parameter critical-power model.
    E0      anaerobic reserve, J. Finite store of energy usable above R.
            Plays the role of W' in the critical-power model.

            IMPORTANT UNITS NOTE. E0 here is METABOLIC energy, not mechanical
            work. Published W' values of 15-25 kJ are mechanical. The conversion
            is a MULTIPLICATION, because efficiency is the fraction of metabolic
            energy that becomes mechanical work:

                mechanical energy = metabolic energy x efficiency

            So a metabolic E0 of 50 kJ is 50 x 0.20 = 10.0 kJ of total
            mechanical work at the assumed gross efficiency, of which
            50 x eta_p x eta_g = 50 x 0.12 = 6.0 kJ is delivered against drag.
            Dividing instead of multiplying inflates the figure by roughly an
            order of magnitude, and it is the easiest error to make here.
    tau     time constant of the aerobic response, s. R_eff(t) = R (1 - e^{-t/tau}).
            Set tau = 0 for an instantaneous aerobic ceiling.
            16.5 s = measured primary-component tau at severe intensity in
            well-trained male swimmers (Pessoa Filho et al. 2012, full text).
            Swimming-specific measurements span 9.6-17.8 s; elite adults at
            actual 200 m race pace measure 10.5 +/- 2.5 s (Sousa et al. 2011),
            so 16.5 is the conservative end of a cited range, no longer a
            provenance gap. The optimal SHAPE is provably tau-independent in
            M0/M1/M3, so no shape conclusion moves with this choice.

    Two competing fatigue mechanisms, both dimensionless, both zero by default.
    They inflate the metabolic cost of a given velocity, representing loss of
    stroke economy as the swimmer tires, and they make opposite predictions.

    beta_E  reserve-coupled decay. Cost multiplier (1 + beta_E * D) where
            D = 1 - E/E0 is the fraction of the anaerobic store already spent.
            Economy is a function of how much fuel is left. Because holding
            back early keeps E high and economy good, this mechanism rewards a
            slow opening and predicts a NEGATIVE split.

    beta_x  position-coupled decay. Cost multiplier (1 + beta_x * x/L) where x
            is distance covered. Economy degrades with time and accumulated
            stroke count regardless of how hard the swimmer went. Because the
            same velocity is simply cheaper early than late, this mechanism
            rewards banking speed early and predicts a POSITIVE split.

    Real 200 frees are positively split even after the dive start is credited
    back, so the two are empirically separable. See docs/03_ode_model.md.

    gamma   fatigue-coupled velocity ceiling, dimensionless. The attainable
            velocity falls to v_max (1 - gamma * D) as the reserve empties.
            A constraint-side route to positive splitting rather than a
            cost-side one. gamma = 0 disables it.

    Cost-function block
    -------------------
    phi     course economy factor, dimensionless. Multiplies the cost
            coefficient: k = phi * K_d / (eta_p eta_g).

            This is the model's one openly calibrated scalar, and it exists
            because the model describes free swimming while the event is raced
            in a 25 yard pool with a dive start, seven turns and eight
            underwater phases. Those phases are faster and cheaper per metre
            than surface swimming, so a swimmer covering 182.88 m of SCY racing
            spends less than 182.88 m of free swimming at the same mean
            velocity would cost. phi < 1 is that discount.

            Naming it does three things a hidden fudge factor would not. It
            keeps the measured hydrodynamic parameters at their measured values.
            It makes the size of the missing physics visible and comparable
            across model variants: a variant needing phi far from 1 is demanding
            a large unexplained economy. And it gives Task 19 (the eight-segment
            start/turn model) a target, because an explicit turn model should
            drive phi toward 1.

            phi = 1 means "free swimming", i.e. no course discount claimed.

    p       exponent in C(v) = k v^p. The drag derivation gives p = 3 exactly.
            Kept as a free parameter so its influence can be tested. Note that
            Berger et al. (1999, via Toussaint 2002) measured a drag-force
            exponent of 2.22 rather than 2.00, implying p = 3.22.
    k       cost coefficient. Derived from the hydrodynamic block when p = 3.
            For p != 3 it is re-anchored so C(v_ref) is preserved, which keeps
            a p sweep interpretable. See cost_coefficient().

    Kinematic bounds
    ----------------
    v_max   maximum attainable free-swimming velocity, m/s. Roughly the
            swimmer's flat-out 25 pace.
    v_min   lower bound, m/s. Prevents the optimizer from exploring
            physically meaningless slow solutions.
    """

    label: str = "reference_M1518"

    # hydrodynamics  (measured; see docs/parameters.md)
    rho: float = 997.0
    Cd: float = 0.30
    A: float = 0.230
    eta_p: float = 0.60
    eta_g: float = 0.20

    # physiology  (CALIBRATED, not measured; see docs/parameters.md Category B)
    R: float = 1250.0
    E0: float = 50_320.0
    tau: float = 0.0
    beta_E: float = 0.0
    beta_x: float = 0.0
    gamma: float = 0.0

    # cost function
    phi: float = 1.0        # course economy factor; 1.0 = free swimming
    p: float = 3.0

    # kinematic bounds
    v_max: float = 2.10
    v_min: float = 1.20

    # reference velocity used to re-anchor k when p is varied
    v_ref: float = 1.8288  # m/s, equals 200 yd in 100.0 s

    # ---------------------------------------------------------------- helpers
    @property
    def drag_factor(self) -> float:
        """K_d in F_drag = K_d v^2, units N s^2 / m^2."""
        return 0.5 * self.rho * self.Cd * self.A

    @property
    def eta(self) -> float:
        """Overall efficiency: metabolic power to power dissipated against drag."""
        return self.eta_p * self.eta_g

    @property
    def k3_free(self) -> float:
        """
        Free-swimming cost coefficient implied by the drag derivation at p = 3,
        with no course discount applied. This is the quantity that is in
        principle comparable with published energy-cost measurements.
        """
        return self.drag_factor / self.eta

    @property
    def k3(self) -> float:
        """Cost coefficient actually used at p = 3, including the course factor."""
        return self.phi * self.k3_free

    def cost_per_metre(self, v: float) -> float:
        """Metabolic energy per metre at velocity v, J/m. Equals k v^(p-1)."""
        return self.k * v ** (self.p - 1.0)

    @property
    def k(self) -> float:
        """
        Cost coefficient actually used by C(v) = k v^p.

        At p = 3 this is the drag-derived value. Away from p = 3 the
        coefficient is re-anchored so that C(v_ref) is unchanged, which
        isolates the effect of curvature from a trivial rescaling of cost.
        """
        if abs(self.p - 3.0) < 1e-12:
            return self.k3
        c_ref = self.k3 * self.v_ref**3
        return c_ref / self.v_ref**self.p

    @property
    def constant_economy(self) -> bool:
        """True when no fatigue mechanism is active and closed forms apply."""
        return self.beta_E == 0.0 and self.beta_x == 0.0 and self.gamma == 0.0

    def with_(self, **kwargs) -> "Swimmer":
        """Return a copy with fields replaced."""
        return replace(self, **kwargs)

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update(
            drag_factor=self.drag_factor,
            eta=self.eta,
            k=self.k,
        )
        return d


REFERENCE = Swimmer()

# ---------------------------------------------------------------------------
# Swimmer archetypes used in the sensitivity and personalization work
# ---------------------------------------------------------------------------

#: The model variants compared in docs/model_definitions.md. Each holds the
#: same engine (R, E0) and the same measured hydrodynamics, and differs only in
#: which fatigue mechanism is active. phi is calibrated per variant so all four
#: reproduce a 1:40.0 optimum, which makes phi itself a readable diagnostic:
#: the further from 1, the more unexplained course economy that variant needs.
# tau = 16.5 s throughout M1-M4: cited swimming measurement (see Swimmer
# docstring), replacing the exploratory 20 s. phi recalibrated per variant at
# the new tau on 2026-08-31; shapes unchanged where theory says they cannot
# move (M0/M1 exactly even, M3 closed form), slightly shifted for M2/M4.
MODELS = {
    "M0_constant_economy":  REFERENCE,
    "M1_oxygen_kinetics":   REFERENCE.with_(label="M1_oxygen_kinetics",
                                            tau=16.5, phi=0.8826),
    "M2_reserve_fatigue":   REFERENCE.with_(label="M2_reserve_fatigue",
                                            tau=16.5, beta_E=0.28, phi=0.7719),
    "M3_position_fatigue":  REFERENCE.with_(label="M3_position_fatigue",
                                            tau=16.5, beta_x=0.28, phi=0.7755),
    "M4_velocity_ceiling":  REFERENCE.with_(label="M4_velocity_ceiling",
                                            tau=16.5, gamma=0.18, phi=0.8378),
}

#: Optimal split fractions for each model on SCY_200, cached.
#:
#: M0, M1 and M3 have closed forms and are recomputed on demand in about a
#: millisecond. M2 and M4 are path dependent, have no closed form, and each take
#: roughly a minute of ODE-in-the-loop optimization. Since they depend only on
#: fixed parameters, recomputing them for every race in a dataset would be
#: thousands of times slower for an identical answer.
#:
#: Regenerate with:  python -m scripts.refresh_predictions
#: Any change to MODELS above invalidates these and the script must be re-run;
#: tests/test_pipeline.py checks the cache against a live solve.
PREDICTED_SHAPES_SCY200 = {
    "M0_constant_economy":  (0.250000, 0.250000, 0.250000, 0.250000),
    "M1_oxygen_kinetics":   (0.250000, 0.250000, 0.250000, 0.250000),
    "M2_reserve_fatigue":   (0.276800, 0.259000, 0.240100, 0.224100),
    "M3_position_fatigue":  (0.242200, 0.247500, 0.252700, 0.257600),
    "M4_velocity_ceiling":  (0.239600, 0.249200, 0.254100, 0.257100),
}

ARCHETYPES = {
    "reference": REFERENCE,
    "aerobic": REFERENCE.with_(label="aerobic_dominant", R=1400.0, E0=24_000.0),
    "anaerobic": REFERENCE.with_(label="anaerobic_dominant", R=1120.0, E0=48_000.0),
    "high_drag": REFERENCE.with_(label="high_drag", Cd=0.82, A=0.100),
    "low_drag": REFERENCE.with_(label="low_drag", Cd=0.60, A=0.082),
    "fatiguer": REFERENCE.with_(label="fatigue_prone", tau=16.5, beta_x=0.35),
    "durable": REFERENCE.with_(label="fatigue_resistant", tau=16.5, beta_x=0.08),
}

# The working model used for the headline Phase 5 results: oxygen kinetics plus
# position-coupled economy decay, the combination that reproduces the positive
# split seen in real races. It is M3 under another name.
#
# Note what is held fixed and what moves. R and E0 are the SAME as REFERENCE,
# so every variant describes one athlete rather than four different ones, and
# the measured hydrodynamic block is untouched. The only thing that moves is
# phi, the course economy factor, which falls from 1.00 to 0.754. Read that as:
# to reproduce a 1:40 while paying for slow oxygen kinetics and decaying
# economy, this model has to claim SCY racing is about 25% cheaper per metre
# than free swimming at the same mean velocity. Seven turns, eight underwater
# phases and a dive start over 182.88 m make a discount of that size plausible,
# but it is a claim the model asserts rather than derives, and Task 19 (the
# eight-segment start and turn model) is what would test it.
WORKING = MODELS["M3_position_fatigue"].with_(label="working_M1518")


# ---------------------------------------------------------------------------
# Start and turn correction
# ---------------------------------------------------------------------------

# The model describes free swimming. A recorded split 1 also contains the dive
# start and the first underwater, which are worth roughly 1.5-2.5 s in SCY
# relative to a flying push at race pace. START_OFFSET_S is subtracted from
# model split 1 when model output is compared with recorded splits. It is NOT
# applied inside the optimizer, because it is a fixed time credit that does not
# depend on the chosen velocities and therefore cannot shift the optimum.
START_OFFSET_S = 1.80
