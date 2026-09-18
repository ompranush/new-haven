"""Independent failure-path and long-run acceptance checks."""
import unittest
import math
import json

from src.civilisation.sim import Simulation

from src.civilisation.cognition import Budget, reflect


class ReviewWorld:
    pending_decisions = [{"id": 1, "citizen_id": 0, "event": "Storm", "day": 2}]

    def __init__(self):
        self.applied = []

    def snapshot(self):
        return {"citizens": [{"id": 0, "name": "Maya", "memories": []}]}

    def apply_decision(self, *args):
        self.applied.append(args)


class CognitionReviewTests(unittest.TestCase):
    def test_malformed_provider_responses_fail_without_changing_world(self):
        cases = [None, [], {"usage": "bad"}, {"usage": {"total_tokens": float("inf")}},
                 {"usage": {"total_tokens": True}}, {"output": None},
                 {"output": [None]}, {"output": [{"content": [None]}]},
                 {"status": "incomplete", "output": []}]
        for response in cases:
            with self.subTest(response=response):
                world, budget = ReviewWorld(), Budget()
                with self.assertRaisesRegex(ValueError, "invalid"):
                    reflect(world, "test", "model", budget, lambda _: response)
                self.assertFalse(world.applied)
                self.assertEqual(budget.calls, 1)


class SimulationReviewTests(unittest.TestCase):
    def test_loaded_event_ids_cannot_collide_with_next_generated_event(self):
        data = json.loads(Simulation(7, 20).save())
        data['event_counter'] = 0
        with self.assertRaises(ValueError):
            Simulation.load(json.dumps(data))
        data['event_counter'] = 1
        data['pending_decisions'] = [{'id': 999999, 'citizen_id': 0, 'day': 0, 'event': 'Invalid event'}]
        with self.assertRaises(ValueError):
            Simulation.load(json.dumps(data))

    def test_long_runs_resume_exactly_and_keep_family_and_payroll_consistent(self):
        for seed in (0, 7, 19):
            with self.subTest(seed=seed):
                sim = Simulation(seed, 40)
                sim.step(365)
                resumed = Simulation.load(sim.save())
                sim.step(90)
                resumed.step(90)
                self.assertEqual(sim.save(), resumed.save())
                worker_ids = [i for b in sim.businesses for i in b['workers']]
                self.assertEqual(len(worker_ids), len(set(worker_ids)))
                self.assertEqual(set(worker_ids), {c.id for c in sim.living if c.job})
                for c in sim.living:
                    if c.age < 18:
                        self.assertIsNone(c.job)
                        self.assertIsNone(c.partner_id)
                    if c.partner_id is not None:
                        partner = sim.world.citizens[c.partner_id]
                        self.assertTrue(partner.alive)
                        self.assertEqual(partner.partner_id, c.id)
                self.assertTrue(all(math.isfinite(v) for v in sim.summary().values()
                                    if isinstance(v, (int, float))))

    def test_partner_zero_is_cleared_on_bereavement(self):
        sim = Simulation(7, 20)
        zero, other = sim.world.citizens[:2]
        zero.partner_id, other.partner_id = 1, 0
        zero.health = 0
        sim._life_events()
        self.assertFalse(zero.alive)
        self.assertIsNone(other.partner_id)
        self.assertTrue(any('lost their partner' in m['text'] for m in other.memories))

    def test_price_cap_persists_and_unfunded_action_is_atomic(self):
        sim = Simulation(7, 20)
        sim.intervene('market')
        for _ in range(10):
            sim.step()
            self.assertLessEqual(sim.world.food_price, .8)
        sim.world.treasury = 0
        before = sim.save()
        with self.assertRaises(ValueError):
            sim.intervene('festival')
        self.assertEqual(sim.save(), before)

    def test_extinct_world_can_advance_save_and_resume(self):
        sim = Simulation(7, 20)
        for c in sim.world.citizens:
            c.health = 0
        sim._life_events()
        self.assertFalse(sim.living)
        sim.step(30)
        resumed = Simulation.load(sim.save())
        resumed.step()
        self.assertEqual(resumed.summary()['population'], 0)
        self.assertEqual(resumed.summary()['unemployment'], 0)
