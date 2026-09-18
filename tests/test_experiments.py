import unittest
from src.civilisation.experiments import compare


class ExperimentTests(unittest.TestCase):
    def test_paired_experiments_reproduce(self):
        a = compare(seed=7, population=20, seeds=2, horizon=30, scenario="aid")
        b = compare(seed=7, population=20, seeds=2, horizon=30, scenario="aid")
        self.assertEqual(a, b)
        self.assertEqual([r["seed"] for r in a["runs"]], [7, 8])
        self.assertEqual(a["mode"], "rules")
        self.assertIn("delta_stddev", a["aggregate"])

    def test_experiment_bounds(self):
        for kwargs in ({"seeds": 100}, {"horizon": 0}, {"horizon": 366}, {"scenario": "unknown"}):
            with self.assertRaises(ValueError):
                compare(**kwargs)
