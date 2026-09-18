import json
import unittest
from unittest.mock import Mock
from src.civilisation.sim import Simulation


class SimulationTests(unittest.TestCase):
    def test_seed_and_save_replay_match_full_state(self):
        a,b = Simulation(42,40),Simulation(42,40)
        a.step(90)
        b.step(90)
        self.assertEqual(a.save(),b.save())
        restored = Simulation.load(a.save())
        for sim in (a,restored):
            sim.intervene("storm")
            sim.step(45)
        self.assertEqual(a.save(),restored.save())

    def test_ten_seeds_survive_one_year_with_bounded_needs(self):
        for seed in range(10):
            sim = Simulation(seed)
            sim.step(365)
            self.assertGreaterEqual(len(sim.living),90)
            self.assertGreater(sim.world.food,0)
            self.assertGreaterEqual(sim.world.treasury,0)
            for c in sim.living:
                self.assertTrue(0 <= c.x < 24 and 0 <= c.y < 20)
                self.assertFalse(c.x == 19 and c.y != 9)
                for value in (c.health,c.energy,c.happiness,c.hunger):
                    self.assertTrue(0 <= value <= 100)
                self.assertGreaterEqual(c.wealth,0)
                if c.partner_id is not None:
                    self.assertEqual(sim.world.citizens[c.partner_id].partner_id,c.id)

    def test_meal_money_transfers_to_farm(self):
        sim = Simulation(1,10)
        sim._socialise = lambda: None
        sim._life_events = lambda: None
        for c in sim.living:
            c.energy = 0
        before_money = sum(c.wealth for c in sim.living)+sim.world.treasury+sum(b["cash"] for b in sim.businesses)
        before_food = sim.world.food
        sim.rng.choices = Mock(return_value=["Clear"])
        sim.step()
        self.assertAlmostEqual(sim.world.food,before_food-10-sim.ledger["food_lost"])
        after_money = sum(c.wealth for c in sim.living)+sim.world.treasury+sum(b["cash"] for b in sim.businesses)
        self.assertAlmostEqual(before_money,after_money)
        self.assertTrue(all(c.energy > 0 for c in sim.living))

    def test_partner_zero_and_widow_cleanup(self):
        sim = Simulation(1,2)
        first,second = sim.world.citizens
        first.partner_id,second.partner_id = 1,0
        first.health = 0
        sim._life_events()
        self.assertFalse(first.alive)
        self.assertIsNone(second.partner_id)
        self.assertTrue(any(e["kind"] == "bereavement" for e in sim.world.events))
        self.assertFalse(any(0 in b["workers"] for b in sim.businesses))

    def test_birth_has_parents_and_no_adult_roles(self):
        sim = Simulation(1,2)
        a,b = sim.world.citizens
        a.age=b.age=30
        a.partner_id,b.partner_id=1,0
        sim.rng.random=Mock(side_effect=[1,1,0]+[0.5]*5)
        sim._life_events()
        baby=sim.world.citizens[-1]
        self.assertEqual(baby.parent_ids,[0,1])
        self.assertIsNone(baby.job)
        self.assertIsNone(baby.partner_id)
        self.assertFalse(sim._hire(baby,sim.businesses[0]))

    def test_council_costs_and_rejection_are_atomic(self):
        sim=Simulation()
        before=sim.world.treasury
        sim.intervene("education")
        self.assertEqual(sim.world.treasury,before-80)
        self.assertEqual(sim.policies["education"],1)
        sim.world.treasury=0
        state=sim.save()
        with self.assertRaises(ValueError):
            sim.intervene("festival")
        self.assertEqual(state,sim.save())
        with self.assertRaises(ValueError):
            sim.intervene("aid")
        self.assertEqual(sim.world.treasury,0)

    def test_decisions_are_constrained_and_single_use(self):
        sim=Simulation()
        sim.intervene("storm")
        decision=sim.pending_decisions[-1]
        with self.assertRaises(ValueError):
            sim.apply_decision(decision["id"],"create_money","no")
        sim.apply_decision(decision["id"],"rest","Recover after the flood")
        with self.assertRaises(ValueError):
            sim.apply_decision(decision["id"],"rest","again")
        self.assertEqual(sim.decision_log[-1]["action"],"rest")

    def test_malformed_saves_are_rejected(self):
        original=json.loads(Simulation().save())
        mutations=[lambda d:d.update(version=999),lambda d:d["world"].update(food=-1),lambda d:d["world"]["citizens"][0].update(x=99),lambda d:d["world"]["citizens"][0].update(partner_id=1),lambda d:d["businesses"][0].update(workers=[999]),lambda d:d.update(rng=[0,0,0]),lambda d:d["world"].update(food=float("inf"))]
        for mutation in mutations:
            data=json.loads(json.dumps(original))
            mutation(data)
            with self.assertRaises(ValueError):
                Simulation.load(json.dumps(data))
        for text in ("null","{}","[]","not json"):
            with self.assertRaises(ValueError):
                Simulation.load(text)

    def test_snapshot_is_detached_and_json_serializable(self):
        sim=Simulation()
        snapshot=sim.snapshot()
        snapshot["events"].clear()
        self.assertTrue(sim.world.events)
        self.assertEqual(len(snapshot["terrain"]),480)
        json.dumps(snapshot,allow_nan=False)

    def test_invalid_steps(self):
        for days in (0,366,1.5,True,"1"):
            with self.assertRaises(ValueError):
                Simulation().step(days)

if __name__ == "__main__":
    unittest.main()
