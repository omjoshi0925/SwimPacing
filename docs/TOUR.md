# A one-page tour, for the reader deciding whether to read

This repository asks one narrow question and tries to answer it honestly: for
a 15-18 year old male swimmer racing the 200-yard freestyle, what does optimal
pacing look like, and can competing fatigue mechanisms be told apart from real
race splits? Five nested models (M0-M4) share one calibrated engine and differ
only in their fatigue mechanism; their predictions were tested against 345
usable races under a pre-registered protocol. The registered outcome is
reported as it fell: M3 (position-coupled economy decay) has the lowest
held-out error, but no model wins by the pre-registered criterion, the ranking
moves across the registered start-credit band, and the deviation-vs-performance
hypothesis came back null. The nulls are results here, not failures.

## Reading order (about an hour)

1. **`README.md`** (5 min) — the claim, the headline numbers, how to run
   everything.
2. **`docs/model_definitions.md`** (10 min) — M0-M4: one engine, five fatigue
   mechanisms, and which observable could separate them.
3. **`docs/01_derivation.md`** (10 min, skimmable) — why even pacing is a
   theorem in this model class, and why the optimal *shape* depends only on
   economy decay.
4. **`docs/assumptions.md`** (10 min) — the honest half of the project: every
   assumption, what it costs, and what would falsify the model. Start with A1;
   the un-modelled dive start is the decisive uncertainty in everything that
   follows.
5. **`docs/validation_plan.md`** (skim §3-§8) — the pre-registration: primary
   metric, swimmer-grouped split, win criteria, H1, and the amendment log.
6. **`results/validation/report_v0_2.md`** (10 min) — the registered held-out
   evaluation exactly as run, including the start-credit sensitivity band and
   the H1 null.
7. **`docs/parameters.md`** (reference, not linear reading) — provenance for
   every constant: Category A (literature-supported), B (calibrated),
   C (exploratory), with the language rules that keep calibrated numbers from
   masquerading as physiology.
8. **`docs/architecture.md`**, then code (optional) — the module map and data
   flow in one page; from there `src/model.py` and `src/calibration.py` are
   the two files that matter, and `DEV_WORKFLOW.md` says how any checkpoint is
   verified.
9. **`paper/`** — the manuscript drafted from all of the above; CI compiles
   it on every paper or bibliography push.

If you read only one thing, read `results/validation/report_v0_2.md` and then
`docs/assumptions.md` to see how seriously its caveats are taken.

## Three commitments the analysis was run under

- **The pilot-v0.1 fits are exploratory**, labeled as such everywhere they
  appear; they informed priors and surfaced the start-credit confound, nothing
  more.
- **The held-out test set (25% of swimmers, seed 20260829) stayed untouched
  until the registered evaluation** — enforced structurally by a leakage guard
  that raises on test rows, not by etiquette — and was opened exactly once, on
  2026-09-03.
- **Fitted parameters are estimates, never measured physiology.** `beta_x` =
  0.228 is a number that makes a model fit; no swimmer was measured to have
  it.

Data note: subjects are minors, so published rows carry anonymous S-numbers
only; verbatim sources never enter the repository, and their public sha256
digests let anyone re-fetch the official page and verify the dataset was built
from the genuine file.

## Where the project stands

Bands A-I of `ATOMIC_COMMIT_ROADMAP.md` — infrastructure and CI, the
start-credit re-scope, synthetic-verified calibration machinery, exploratory
pilot fits, multi-meet ingest tooling, expansion to the frozen pilot-v0.2
dataset, the registered fits and held-out comparison with bootstrap CIs and
mixed-effects H1, the verified literature record (one paywalled anchor still
outstanding), and the drafted paper — are substantially executed. What remains
is code-quality polish. The roadmap is kept as an audit record: the plan as
written, with dated annotations for everything that diverged, folded, or
landed in a different shape.
