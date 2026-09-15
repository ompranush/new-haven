import unittest
from src.civilisation.sim import Simulation

class SimulationTests(unittest.TestCase):
    def test_seed_is_reproducible(self):
        self.assertEqual(Simulation(42).summary(), Simulation(42).summary())

    def test_step_advances_world(self):
        sim = Simulation(1, 20)
        sim.step()
        self.assertEqual(sim.summary()["day"], 1)
        self.assertGreaterEqual(sim.summary()["food"], 0)

if __name__ == "__main__":
    unittest.main()
