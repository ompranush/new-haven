import unittest

from src.civilisation.sim import Simulation


class SimulationTests(unittest.TestCase):
    def test_seeded_runs_match_after_long_simulation(self):
        first, second = Simulation(42, 40), Simulation(42, 40)
        first.step(120)
        second.step(120)
        self.assertEqual(first.summary(), second.summary())
        self.assertEqual(first.world.events, second.world.events)

    def test_needs_and_economy_remain_bounded(self):
        sim = Simulation(14, 50)
        sim.step(180)
        self.assertGreaterEqual(sim.world.food, 0)
        self.assertGreaterEqual(sim.world.treasury, 0)
        self.assertGreaterEqual(sim.world.food_price, 0.55)
        self.assertLessEqual(sim.world.food_price, 2.5)
        for citizen in sim.living:
            self.assertGreaterEqual(citizen.hunger, 0)
            self.assertLessEqual(citizen.hunger, 100)
            self.assertGreaterEqual(citizen.energy, 0)
            self.assertLessEqual(citizen.energy, 100)
            self.assertGreaterEqual(citizen.happiness, 0)
            self.assertLessEqual(citizen.happiness, 100)

    def test_food_is_consumed_once_per_day(self):
        sim = Simulation(7, 100)
        sim.step(10)
        self.assertGreater(sim.world.food, 20)

    def test_goal_led_movement_stays_on_world(self):
        sim = Simulation(2, 20)
        sim.step(15)
        for citizen in sim.living:
            self.assertGreaterEqual(citizen.x, 2)
            self.assertLessEqual(citizen.x, 10)
            self.assertGreaterEqual(citizen.y, 1)
            self.assertLessEqual(citizen.y, 7)
            self.assertTrue(citizen.activity)

    def test_interventions_are_recorded_and_deterministic(self):
        sim = Simulation(9, 20)
        before = sim.world.food
        sim.intervene("aid")
        self.assertGreater(sim.world.food, before)
        self.assertIn("relief convoy", sim.world.events[-1])
        with self.assertRaises(ValueError):
            sim.intervene("unknown")

    def test_invalid_step_is_rejected(self):
        with self.assertRaises(ValueError):
            Simulation().step(0)
        with self.assertRaises(ValueError):
            Simulation().step(4000)


if __name__ == "__main__":
    unittest.main()
