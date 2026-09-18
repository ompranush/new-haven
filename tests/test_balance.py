"""Conservation, migration and exploit regression checks for the physical economy."""
import json
import unittest
from src.civilisation.sim import Simulation


class BalanceTests(unittest.TestCase):
    def test_repairs_need_actual_workers(self):
        sim=Simulation()
        sim.intervene("storm")
        for citizen in sim.living:
            citizen.energy=0
        before=[b["condition"] for b in sim.buildings]
        sim._repair_buildings()
        self.assertEqual(before,[b["condition"] for b in sim.buildings])

    def test_rules_and_ai_are_distinct_and_timestamp_execution(self):
        sim=Simulation()
        sim.intervene("storm")
        item=sim.pending_decisions[-1]
        sim.step(3)
        sim.apply_decision(item["id"],"organize","Speak with neighbours")
        decision=sim.decision_log[-1]
        self.assertEqual(decision["source"],"ai")
        self.assertEqual(decision["day"],3)
        self.assertEqual(decision["trigger_day"],0)
        self.assertIn("no council policy",decision["effect"])
        self.assertTrue(any(d.get("source")=="rules" for d in sim.decision_log))
        self.assertEqual(sim.save(),Simulation.load(sim.save()).save())

    def test_day_zero_flood_and_relief_account_for_every_resource(self):
        sim = Simulation()
        sim.intervene("storm")
        sim.intervene("aid")
        ledger = sim.ledger
        self.assertAlmostEqual(ledger["food_closing"],ledger["food_opening"]-ledger["food_lost"]+ledger["food_imported"])
        self.assertAlmostEqual(ledger["money_closing"],ledger["money_opening"]-ledger["repair_cost"]-ledger["relief_cost"])

    def test_good_interventions_cannot_be_spammed(self):
        for action in ("festival","education","automation"):
            sim = Simulation()
            sim.intervene(action)
            before = sim.save()
            with self.assertRaises(ValueError):
                sim.intervene(action)
            self.assertEqual(before,sim.save())

    def test_old_v1_save_migrates_to_intact_buildings(self):
        old = json.loads(Simulation().save())
        for field in ("buildings","active_effects","resources","ledger","cooldowns"):
            old.pop(field)
        sim = Simulation.load(json.dumps(old))
        self.assertTrue(all(b["condition"]==100 for b in sim.buildings))
        self.assertEqual(sim.active_effects,[])
        sim.step(10)
        self.assertEqual(sim.save(),Simulation.load(sim.save()).save())

    def test_invalid_physical_state_is_rejected(self):
        for field,value in (("resources",{"wood":-1,"stone":10}),("active_effects",[{"kind":"flood","label":"bad","severity":2,"days_remaining":10}]),("cooldowns",{"aid":999999})):
            data=json.loads(Simulation().save())
            data[field]=value
            with self.assertRaises(ValueError):
                Simulation.load(json.dumps(data))
