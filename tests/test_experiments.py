import unittest
from src.civilisation.experiments import compare


class ExperimentTests(unittest.TestCase):
    def test_paired_experiments_reproduce(self):
        a = compare(seed=7, population=20, seeds=2, horizon=30, scenario="storm")
        b = compare(seed=7, population=20, seeds=2, horizon=30, scenario="storm")
        self.assertEqual(a, b)
        self.assertEqual([r["seed"] for r in a["runs"]], [7, 8])
        self.assertEqual(a["mode"], "rules")
        self.assertIn("delta_stddev", a["aggregate"])

    def test_experiment_bounds(self):
        for kwargs in ({"seeds": 100}, {"horizon": 0}, {"horizon": 366}, {"scenario": "unknown"}):
            with self.assertRaises(ValueError):
                compare(**kwargs)

    def test_unavailable_intervention_is_reported_not_forced(self):
        result = compare(seed=7, population=20, seeds=2, horizon=30, scenario="storm")
        for run in result["runs"]:
            self.assertIn("intervention_applied", run)
            self.assertIn("intervention_note", run)
            self.assertIsNotNone(run["impact_week"])
            if not run["intervention_applied"]:
                self.assertIn("Not applied:", run["intervention_note"])
                self.assertEqual(run["baseline"], run["treatment"])
