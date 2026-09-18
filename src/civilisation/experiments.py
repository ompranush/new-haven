"""Paired-seed experiments with isolated worlds and explicit resource bounds."""
from statistics import mean, pstdev

from .sim import Simulation

METRICS = ("population", "happiness", "food", "wealth", "unemployment", "treasury")
SCENARIOS = ("storm", "education", "automation", "festival", "tax")


def compare(seed=7, population=100, seeds=3, horizon=90, scenario="education", cognition=None):
    if type(seeds) is not int or not 1 <= seeds <= 10:
        raise ValueError("Choose between 1 and 10 seeds.")
    if type(horizon) is not int or not 1 <= horizon <= 365:
        raise ValueError("Choose a horizon between 1 and 365 days.")
    if scenario not in SCENARIOS:
        raise ValueError("Unknown experiment scenario.")
    runs = []
    for offset in range(seeds):
        baseline, treatment = Simulation(seed + offset, population), Simulation(seed + offset, population)
        ai_calls = 0
        intervention_applied = False
        intervention_note = "AI comparison; no council intervention" if cognition else "Not attempted"
        impact_week = None
        for day in range(horizon):
            baseline.step()
            treatment.step()
            if cognition is None and day == min(9, horizon - 1):
                try:
                    treatment.intervene(scenario)
                    intervention_applied = True
                    intervention_note = "Applied on day " + str(treatment.world.day)
                except ValueError as error:
                    intervention_note = "Not applied: " + str(error)
            elif cognition is not None and treatment.pending_decisions:
                ai_calls += bool(cognition(treatment))
            if day == 16:
                sa, sb = baseline.summary(), treatment.summary()
                impact_week = {k: round(sb[k] - sa[k], 3) for k in METRICS}
        before, after = baseline.summary(), treatment.summary()
        runs.append({"seed": seed + offset, "baseline": before, "treatment": after, "ai_calls": ai_calls,
                     "intervention_applied": intervention_applied, "intervention_note": intervention_note, "impact_week": impact_week,
                     "delta": {k: round(after.get(k, 0) - before.get(k, 0), 3) for k in METRICS}})
    aggregate = {side: {k: round(mean(r[side].get(k, 0) for r in runs), 3) for k in METRICS}
                 for side in ("baseline", "treatment", "delta")}
    aggregate["delta_stddev"] = {k: round(pstdev(r["delta"][k] for r in runs), 3) for k in METRICS}
    return {"scenario": scenario, "horizon": horizon, "seeds": seeds, "mode": "ai" if cognition else "rules",
            "runs": runs, "aggregate": aggregate,
            "note": "Interventions are attempted on day 10 (or the last day of shorter runs). Unavailable actions are reported per seed, not forced. Paired starting seeds; stochastic paths can diverge after intervention. Toy-model results, not evidence about real societies. AI outputs are not deterministic."}
