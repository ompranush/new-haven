import unittest

from src.civilisation.sim import Simulation


class SimulationTests(unittest.TestCase):
    def test_seed_is_reproducible_after_multiple_days(self):
        first, second = Simulation(42, 20), Simulation(42, 20)
        first.step(20)
        second.step(20)
        self.assertEqual(first.summary(), second.summary())
        self.assertEqual(first.world.events, second.world.events)

    def test_step_advances_world_and_records_history(self):
        sim = Simulation(1, 20)
        sim.step(3)
        self.assertEqual(sim.summary()["day"], 3)
        self.assertEqual(len(sim.world.history), 4)
        self.assertGreaterEqual(sim.summary()["food"], 0)

    def test_citizens_have_spatial_state_and_can_remember(self):
        sim = Simulation(2, 20)
        sim.step(10)
        for citizen in sim.living:
            self.assertGreaterEqual(citizen.x, 2)
            self.assertLessEqual(citizen.x, 10)
            self.assertGreaterEqual(citizen.y, 1)
            self.assertLessEqual(citizen.y, 7)
        self.assertTrue(any(citizen.memories for citizen in sim.living))

    def test_invalid_step_is_rejected(self):
        with self.assertRaises(ValueError):
            Simulation().step(0)


if __name__ == "__main__":
    unittest.main()
