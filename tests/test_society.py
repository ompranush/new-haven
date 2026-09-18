import json
import unittest

from src.civilisation.sim import Simulation
from src.civilisation.society import advance_society, situation


class SocietyTests(unittest.TestCase):
    def test_metrics_use_real_balances_and_edges(self):
        sim = Simulation(7, 2)
        a, b = sim.living
        a.wealth, b.wealth = 0, 100
        a.relationships[str(b.id)] = 60
        b.relationships[str(a.id)] = 80
        stats = situation(sim)
        self.assertEqual(stats["wealth"]["gini"], .5)
        self.assertEqual(stats["wealth"]["median"], 50)
        self.assertEqual(stats["relationships"]["friendships"], 1)
        self.assertEqual(stats["relationships"]["mean_trust"], 70)
        self.assertIsNone(stats["crime"]["rate_per_1000_citizen_days"])

    def test_replay_and_migration_preserve_random_stream(self):
        sim = Simulation(11, 50)
        sim.step(40)
        clone = Simulation.load(sim.save())
        sim.step(20)
        clone.step(20)
        self.assertEqual(sim.save(), clone.save())
        old = json.loads(sim.save())
        old.pop("crime_events")
        old.pop("society_observations")
        for c in old["world"]["citizens"]:
            for key in ("gender", "political_economic", "political_social", "daily_wage"):
                c.pop(key)
        migrated = Simulation.load(json.dumps(old))
        self.assertEqual(migrated.rng.getstate(), sim.rng.getstate())
        self.assertEqual(migrated.save(), Simulation.load(json.dumps(old)).save())
        self.assertIsNone(situation(migrated)["crime"]["rate_per_1000_citizen_days"])

    def test_theft_transfers_money_and_records_exposure(self):
        sim = Simulation(7, 100)
        sim.world.food = 0
        opening = sim._money()
        for day in range(1, 61):
            sim.world.day = day
            advance_society(sim)
        self.assertAlmostEqual(opening, sim._money())
        stats = situation(sim)["crime"]
        self.assertGreater(stats["incidents_30d"], 0)
        self.assertEqual(stats["observation_days"], 30)
        self.assertEqual(stats["citizen_days"], 3000)
        self.assertAlmostEqual(stats["rate_per_1000_citizen_days"], stats["incidents_30d"]/3)
        self.assertTrue(all(c.wealth >= 0 for c in sim.living))

    def test_identity_not_used_in_pay_or_daily_dynamics(self):
        sim = Simulation(3, 50)
        clone = Simulation.load(sim.save())
        for c in clone.living:
            c.gender = "nonbinary"
        sim.step(30)
        clone.step(30)
        self.assertEqual(sim.summary(), clone.summary())
        self.assertEqual([c.wealth for c in sim.living], [c.wealth for c in clone.living])
        self.assertEqual([c.daily_wage for c in sim.living], [c.daily_wage for c in clone.living])
        self.assertIsNone(situation(clone)["equality"]["wealth_ratio"])

    def test_tampered_society_state_is_rejected(self):
        sim = Simulation(4, 20)
        sim.step(2)
        for field, value in (("gender", "invalid"), ("political_social", 2), ("political_economic", True), ("daily_wage", -1)):
            data = json.loads(sim.save())
            data["world"]["citizens"][0][field] = value
            with self.assertRaises(ValueError):
                Simulation.load(json.dumps(data))
        data = json.loads(sim.save())
        data["society_observations"][0]["population"] = -1
        with self.assertRaises(ValueError):
            Simulation.load(json.dumps(data))


if __name__ == "__main__":
    unittest.main()
