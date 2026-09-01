"""
Verification tests.

These are not style checks. Each one pins a claim the write-up makes, so that
if a later change to the model quietly breaks a stated result, the test fails
rather than the paper being wrong.

Run with:  python -m pytest tests -q
"""

import numpy as np
import pytest

from src import model, optimization, simulator
from src.parameters import REFERENCE, SCY_200, WORKING, Swimmer

C = SCY_200


# ---------------------------------------------------------------------------
# Physical plausibility of the calibration
# ---------------------------------------------------------------------------


def test_drag_factor_matches_published_range():
    """
    K_d = 1/2 rho Cd A, built from separately measured Cd and active frontal
    area (Zamparo et al. 2009). Directly measured lumped coefficients are 38
    kg/m (Cortesi et al. 2024, elite male sprinters) and 22-30 (Toussaint 2002),
    so the derived value must land inside that spread rather than outside it.
    """
    assert 22.0 <= REFERENCE.drag_factor <= 38.0


def test_drag_components_are_individually_defensible():
    """
    The regression this guards against actually happened: Cd = 0.70 and
    A = 0.090 were previously chosen so their PRODUCT landed in the measured
    band while each factor sat outside every measured value. A reviewer checking
    the components would have caught it.
    """
    assert 0.23 <= REFERENCE.Cd <= 0.61, "outside measured active-drag Cd range"
    assert 0.13 <= REFERENCE.A <= 0.40, "outside measured frontal-area range"


def test_efficiency_conversion_is_a_multiplication():
    """
    mechanical energy = metabolic energy x efficiency.

    An earlier revision of the docs said "divide", which inflates the figure by
    roughly an order of magnitude. Pinned here because it is a units error that
    reads plausibly either way.
    """
    metabolic = REFERENCE.E0
    against_drag = metabolic * REFERENCE.eta
    assert against_drag < metabolic
    assert against_drag == pytest.approx(metabolic * REFERENCE.eta_p * REFERENCE.eta_g)
    assert 3_000.0 < against_drag < 12_000.0


def test_metabolic_rate_at_race_pace_is_supramaximal_but_sane():
    """
    A 200 free is raced above VO2max. For a ~68 kg male that means a metabolic
    rate somewhere above roughly 1.3 kW and well below 2.5 kW.
    """
    v = model.even_pace_velocity(REFERENCE, C)
    rate = float(model.metabolic_rate(v, REFERENCE))
    assert 1300.0 < rate < 3000.0
    assert rate > REFERENCE.R, "race pace must exceed the aerobic ceiling"


def test_reference_race_time_is_realistic_for_the_population():
    """Male 15-18, 200 free SCY: a 1:35 to 1:50 optimum is the plausible band."""
    T = model.optimal_solution_closed_form(REFERENCE, C)["race_time"]
    assert 95.0 < T < 110.0


def test_anaerobic_share_is_inside_the_measured_band():
    """
    Implied anaerobic share of total race energy, checked against measured
    values for the 200 m front crawl: 21.3 +/- 2.9% (Sousa et al. 2011, elite
    males at race pace) to 34.1% (Figueiredo et al. 2011, international, LCM).
    The band below widens the measured 21-34% by a few points because the
    model's share is an output of a calibration, not a measurement, and the two
    sources themselves disagree by 13 points.
    """
    for sw in (REFERENCE, WORKING):
        opt = model.optimal_solution_closed_form(sw, C)
        aerobic = float(model.aerobic_supply(opt["race_time"], sw))
        share = sw.E0 / (sw.E0 + aerobic)
        assert 0.17 < share < 0.40, f"{sw.label}: implied anaerobic share {share:.1%}"


def test_all_five_models_reproduce_a_realistic_race_time():
    """phi is calibrated per variant so the comparison is about shape, not speed."""
    from src.parameters import MODELS
    from src import optimization as _opt
    for name, sw in MODELS.items():
        if model._closed_form_ok(sw):
            T = model.optimal_solution_closed_form(sw, C)["race_time"]
            assert abs(T - 100.0) < 0.1, f"{name} optimum is {T:.2f} s"


def test_course_economy_factor_is_a_bounded_claim():
    """
    phi < 1 claims SCY racing is cheaper per metre than free swimming. A dive,
    seven turns and eight underwaters over 182.88 m can justify a discount of
    tens of percent, not a factor of two.
    """
    from src.parameters import MODELS
    for name, sw in MODELS.items():
        assert 0.6 <= sw.phi <= 1.0, f"{name} needs phi = {sw.phi:.3f}"


# ---------------------------------------------------------------------------
# The central theorem: even pacing under constant economy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("p", [2.0, 2.5, 3.0, 3.5, 4.0, 5.0])
def test_even_pacing_optimal_for_every_exponent(p):
    sw = REFERENCE.with_(p=p)
    opt = optimization.optimize_static(sw, C, n_starts=10)
    assert opt["max_split_spread_s"] < 1e-4
    assert np.allclose(opt["split_fractions"], 0.25, atol=1e-6)


@pytest.mark.parametrize("field,value", [
    ("R", 900.0), ("R", 1500.0),
    ("E0", 20_000.0), ("E0", 60_000.0),
    ("Cd", 0.55), ("Cd", 0.90),
    ("A", 0.075), ("A", 0.110),
    ("eta_p", 0.50), ("eta_g", 0.25),
])
def test_shape_invariant_to_every_non_fatigue_parameter(field, value):
    """
    The headline negative result. Changing the engine or the hull changes the
    race time and leaves the optimal split distribution at exactly even.
    """
    sw = REFERENCE.with_(**{field: value})
    opt = optimization.optimize_static(sw, C, n_starts=8)
    assert np.allclose(opt["split_fractions"], 0.25, atol=1e-6)


@pytest.mark.parametrize("tau", [0.0, 10.0, 20.0, 30.0, 40.0])
def test_oxygen_kinetics_do_not_change_the_shape(tau):
    """
    Total aerobic supply depends on race duration alone, not on how velocity is
    distributed, so realistic VO2 kinetics cannot make uneven pacing optimal.

    The tau values here span the physiologically plausible range and all leave
    the energy path constraint slack. See the next test for what happens once
    it binds.
    """
    sw = REFERENCE.with_(tau=tau)
    assert model.optimal_solution_closed_form(sw, C)["path_feasible"]
    opt = optimization.optimize_static(sw, C, n_starts=8)
    assert np.allclose(opt["split_fractions"], 0.25, atol=1e-6)


@pytest.mark.parametrize("tau", [20.0, 60.0, 120.0, 200.0])
def test_path_constraint_is_slack_at_the_calibrated_reserve(tau):
    """
    At the corrected calibration the energy path constraint never binds, for any
    tau, so the even-pacing result holds unconditionally here.

    This CHANGED. With the previous (too small) E0 of 35 kJ the reserve dipped
    negative near the 150 for tau above about 40 s, and the result had to be
    stated with a condition. Enlarging E0 to 50.3 kJ during the drag-parameter
    correction removed that boundary entirely. It was an artifact of an
    undersized reserve, not a physiological finding, which is worth recording:
    a qualitative "result" disappeared when a parameter error was fixed.
    """
    sw = REFERENCE.with_(tau=tau)
    assert model.optimal_solution_closed_form(sw, C)["path_feasible"]


@pytest.mark.parametrize("E0_kJ,tau,binds", [
    (10.0, 20.0, True), (20.0, 20.0, True), (25.0, 20.0, False),
    (25.0, 60.0, True), (50.32, 60.0, False),
])
def test_path_constraint_machinery_still_works_when_the_reserve_is_small(E0_kJ, tau, binds):
    """
    The path-constraint handling is real machinery and must stay tested even
    though the default parameters no longer exercise it.

    A small reserve combined with slow kinetics still produces a terminal-
    constraint solution that would run the reserve negative mid-race. When that
    happens the closed form is only a LOWER BOUND on the true race time, and the
    numerical solver must return something strictly slower and no longer even.
    """
    sw = REFERENCE.with_(E0=E0_kJ * 1000.0, tau=tau)
    closed = model.optimal_solution_closed_form(sw, C)
    assert closed["path_feasible"] is not binds

    if binds:
        assert closed["energy"].min() < -100.0
        opt = optimization.optimize_static(sw, C, n_starts=12)
        assert opt["race_time"] > closed["race_time"]
        P = np.asarray(opt["split_fractions"])
        assert P.max() - P.min() > 1e-4


def test_oxygen_kinetics_do_slow_the_race():
    """Sanity check on the above: tau is not simply being ignored."""
    fast = model.optimal_solution_closed_form(REFERENCE.with_(tau=0.0), C)["race_time"]
    slow = model.optimal_solution_closed_form(REFERENCE.with_(tau=30.0), C)["race_time"]
    assert slow > fast + 5.0


# ---------------------------------------------------------------------------
# Cross-validation of the three solvers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("beta_x", [0.0, 0.15, 0.30, 0.50])
def test_closed_form_matches_slsqp_and_ode(beta_x):
    sw = REFERENCE.with_(tau=20.0, beta_x=beta_x)
    closed = model.optimal_solution_closed_form(sw, C)
    solved = optimization.optimize_static(sw, C, n_starts=8)
    ode = simulator.simulate(closed["velocities"], sw, C)

    assert abs(closed["race_time"] - solved["race_time"]) < 1e-6
    assert abs(closed["race_time"] - ode["race_time"]) < 1e-4
    assert abs(ode["terminal_energy"]) < 1.0  # joules, out of tens of kJ


def test_midpoint_weighting_is_exact_not_approximate():
    """
    The per-split weight w_i = 1 + beta_x * xbar_i / L is derived by integrating
    a multiplier that is linear in x, so it should agree with the ODE to solver
    tolerance rather than to quadrature error.
    """
    sw = REFERENCE.with_(beta_x=0.40)
    v = np.full(4, 1.80)
    discrete = float(np.sum(model.split_energy_demand(v, C, sw)))
    ode = simulator.simulate(v, sw, C)
    integrated = sw.E0 + float(model.aerobic_supply(ode["race_time"], sw)) - ode["terminal_energy"]
    assert abs(discrete - integrated) / discrete < 1e-6


# ---------------------------------------------------------------------------
# Fatigue mechanisms make opposite predictions
# ---------------------------------------------------------------------------


def test_position_fatigue_gives_a_positive_split():
    opt = optimization.optimize(REFERENCE.with_(tau=20.0, beta_x=0.30), C)
    P = np.asarray(opt["split_fractions"])
    assert P[0] < P[1] < P[2] < P[3]
    assert P[3] - P[0] > 0.005


@pytest.mark.slow
def test_reserve_fatigue_gives_a_negative_split():
    """
    The refutable prediction. Holding back early keeps the reserve high and
    economy good, so this mechanism wants a slow opening. Real 200 frees are
    positively split, which is evidence against it.
    """
    opt = optimization.optimize_full(REFERENCE.with_(tau=20.0, beta_E=0.40), C,
                                     n_starts=4)
    P = np.asarray(opt["split_fractions"])
    assert P[0] > P[3]


def test_optimal_shape_depends_only_on_weights():
    """
    Two swimmers with wildly different engines and hulls but the same beta_x
    must have identical optimal split fractions, even though their race times
    differ by many seconds.
    """
    a = REFERENCE.with_(beta_x=0.25, R=1000.0, E0=30_000.0, Cd=0.60)
    b = REFERENCE.with_(beta_x=0.25, R=1600.0, E0=95_000.0, Cd=0.58, A=0.078)
    Pa = model.optimal_solution_closed_form(a, C)["split_fractions"]
    Pb = model.optimal_solution_closed_form(b, C)["split_fractions"]
    Ta = model.optimal_solution_closed_form(a, C)["race_time"]
    Tb = model.optimal_solution_closed_form(b, C)["race_time"]
    assert np.allclose(Pa, Pb, atol=1e-9)
    assert abs(Ta - Tb) > 5.0


# ---------------------------------------------------------------------------
# Energy accounting and constraints
# ---------------------------------------------------------------------------


def test_optimum_exhausts_the_reserve():
    """Leftover fuel at the touch means the swimmer could have gone faster."""
    for sw in (REFERENCE, WORKING):
        opt = optimization.optimize(sw, C)
        assert abs(opt["terminal_energy"]) < 1.0


def test_reserve_never_goes_negative_at_the_optimum():
    for sw in (REFERENCE, WORKING):
        opt = optimization.optimize(sw, C)
        traj = simulator.simulate(np.asarray(opt["velocities"]), sw, C)
        assert traj["min_energy"] > -1.0
        assert traj["feasible"]


def test_matched_budget_strategies_all_spend_the_same_energy():
    """The premise that makes the pacing penalty a fair comparison."""
    for name in simulator.STRATEGY_SHAPES:
        r = simulator.run_strategy(name, REFERENCE, C)
        assert abs(r["terminal_energy"]) < 1.0


# ---------------------------------------------------------------------------
# Pacing penalties
# ---------------------------------------------------------------------------


def test_every_named_strategy_is_at_least_as_slow_as_the_optimum():
    rows = optimization.compare_strategies(REFERENCE, C)
    for r in rows:
        assert r["penalty_s"] >= -1e-6, f"{r['strategy']} beat the optimum"


def test_penalty_grows_with_the_size_of_the_opening_error():
    res = optimization.opening_penalty_curve([0.0, 0.02, 0.05, 0.10], REFERENCE, C)
    pen = res["penalty_s"]
    assert pen[0] < 1e-6
    assert np.all(np.diff(pen) > 0)


def test_penalty_is_locally_quadratic_not_linear():
    """
    Doubling a small opening error should roughly quadruple the penalty. This is
    why small pacing errors are cheap and large ones are not, and it is the
    reason the objective looks flat near the optimum.
    """
    res = optimization.opening_penalty_curve([0.01, 0.02], REFERENCE, C)
    ratio = res["penalty_s"][1] / res["penalty_s"][0]
    assert 3.5 < ratio < 4.5


def test_symmetric_errors_cost_about_the_same_under_constant_economy():
    """
    A structural property of the constant-economy model, and one of its
    testable weaknesses: it says opening 5% too fast and 5% too slow cost
    nearly the same, which coaches would dispute.
    """
    res = optimization.opening_penalty_curve([-0.05, 0.05], REFERENCE, C)
    lo, hi = res["penalty_s"]
    assert abs(lo - hi) / max(lo, hi) < 0.15


# ---------------------------------------------------------------------------
# Bookkeeping
# ---------------------------------------------------------------------------


def test_start_offset_cannot_change_the_optimum():
    """
    The dive credit is a constant subtracted from split 1, so it shifts T by a
    constant and leaves the argmin untouched. Stated in the code, checked here.
    """
    opt = model.optimal_solution_closed_form(WORKING, C)
    shifted = model.apply_start_offset(opt["split_times"], 1.8)
    assert abs(shifted.sum() - (opt["race_time"] - 1.8)) < 1e-12


def test_cost_coefficient_reanchors_when_the_exponent_moves():
    """Varying p must not silently rescale the cost at race pace."""
    base = REFERENCE
    for p in (2.0, 3.0, 4.0):
        sw = base.with_(p=p)
        assert abs(float(model.metabolic_rate(sw.v_ref, sw))
                   - base.k3 * base.v_ref**3) < 1e-6


def test_format_time_reads_like_a_split_sheet():
    assert model.format_time(100.017) == "1:40.02"
    assert model.format_time(24.5) == "24.50"
