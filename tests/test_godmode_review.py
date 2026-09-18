"""Independent adversarial checks; no network requests or real credentials."""
import json
import unittest

from src.civilisation.cognition import Budget
from src.civilisation.godmode import apply_plan, interpret_command, plan_fingerprint
from src.civilisation.sim import Simulation
from src.civilisation.society import situation
from src.civilisation.controller import handle_action, public_ai


def plan(*actions):
    return {"summary": "A bounded village intervention", "actions": list(actions), "limitations": []}


def action(kind="resource", target="food", amount=20):
    return {"kind": kind, "target": target, "amount": amount, "reason": "Requested by the player"}


def response(value):
    return {"status": "completed", "usage": {"total_tokens": 30}, "output": [
        {"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}
    ]}


class GodModeIndependentReview(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation(7, 40)

    def test_success_is_atomic_copy_not_mutation(self):
        before = self.sim.save()
        result = apply_plan(self.sim, plan(action()))
        self.assertEqual(self.sim.save(), before)
        self.assertEqual(result.world.food, self.sim.world.food + 20)
        self.assertEqual(Simulation.load(result.save()).snapshot(), result.snapshot())

    def test_later_failed_action_does_not_partially_apply(self):
        before = self.sim.save()
        with self.assertRaises(ValueError):
            apply_plan(self.sim, plan(action(), action("resource", "treasury", -10000)))
        self.assertEqual(self.sim.save(), before)

    def test_reversed_relationship_pair_cannot_bypass_change_bound(self):
        before = self.sim.save()
        with self.assertRaises(ValueError):
            apply_plan(self.sim, plan(action("relationship", "0:1", 25), action("relationship", "1:0", 25)))
        self.assertEqual(self.sim.save(), before)

    def test_same_day_change_invalidates_fingerprint(self):
        fingerprint = plan_fingerprint(self.sim)
        day = self.sim.world.day
        self.sim.intervene("storm")
        self.assertEqual(self.sim.world.day, day)
        self.assertNotEqual(plan_fingerprint(self.sim), fingerprint)
        self.assertEqual(plan_fingerprint(Simulation.load(self.sim.save())), plan_fingerprint(self.sim))

    def test_invalid_shapes_and_numbers_never_mutate(self):
        candidates = [plan(action(amount=True)), plan(action(amount=float("nan"))),
                      plan(action(amount=float("inf"))), plan(action(kind="run_python")),
                      plan(action(target="api_key")), plan(action(amount=10001))]
        extra = plan(action())
        extra["actions"][0]["execute"] = "arbitrary code"
        candidates.append(extra)
        before = self.sim.save()
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    apply_plan(self.sim, candidate)
                self.assertEqual(before, self.sim.save())

    def test_refusals_and_malformed_responses_count_without_mutation(self):
        cases = [None, [], {"status": "incomplete"}, {"output": [None]},
                 {"output": [{"content": [{"type": "refusal", "refusal": "Cannot comply"}]}]},
                 response(plan(action(kind="execute")))]
        before = self.sim.save()
        for result in cases:
            with self.subTest(result=result):
                budget = Budget()
                with self.assertRaises(ValueError):
                    interpret_command(self.sim, "Supply food", "fake-review-key", "test-model", budget,
                                      transport=lambda _payload, output=result: output)
                self.assertEqual(budget.calls, 1)
                self.assertEqual(self.sim.save(), before)

    def test_interpretation_does_not_apply_and_never_embeds_key(self):
        before = self.sim.save()
        budget = Budget(max_calls=1)
        def transport(payload):
            self.assertNotIn("fake-review-key", json.dumps(payload))
            self.assertIs(payload["store"], False)
            return response(plan(action()))
        result = interpret_command(self.sim, "Supply food", "fake-review-key", "test-model", budget, transport)
        self.assertEqual(self.sim.save(), before)
        self.assertNotIn("fake-review-key", json.dumps(result))
        self.assertEqual(budget.calls, 1)
        with self.assertRaises(ValueError):
            interpret_command(self.sim, "Supply food", "fake-review-key", "test-model", budget,
                              lambda _: self.fail("Spent past explicit call cap"))


class SocietyIndependentReview(unittest.TestCase):
    def test_inequality_and_politics_are_calculated_from_citizens(self):
        sim = Simulation(7, 4)
        for i, citizen in enumerate(sim.living):
            citizen.wealth = 100 if i == 3 else 0
            citizen.age = 30
            citizen.political_economic = -1 if i < 2 else 1
        data = situation(sim)
        self.assertEqual(data["wealth"]["gini"], .75)
        self.assertEqual(data["wealth"]["top10_share"], 100)
        self.assertEqual(data["politics"]["groups"]["economic"], {"collective": 2, "balanced": 0, "market": 2})
        self.assertIsNone(data["crime"]["rate_per_1000_citizen_days"])

    def test_save_replay_and_exposure_denominator(self):
        original = Simulation(77, 40)
        original.step(20)
        resumed = Simulation.load(original.save())
        self.assertEqual(original.snapshot(), resumed.snapshot())
        original.step(20)
        resumed.step(20)
        self.assertEqual(original.snapshot(), resumed.snapshot())
        crime = situation(original)["crime"]
        exposure = sum(r["population"] for r in original.society_observations)
        self.assertEqual(crime["observation_days"], 30)
        self.assertEqual(crime["citizen_days"], exposure)
        self.assertEqual(crime["rate_per_1000_citizen_days"], 1000*len(original.crime_events)/exposure)

    def test_gender_does_not_drive_money_or_employment(self):
        first = Simulation(19, 40)
        second = Simulation.load(first.save())
        for c in second.world.citizens:
            c.gender = {"woman": "man", "man": "nonbinary", "nonbinary": "woman"}[c.gender]
        first.step(30)
        second.step(30)
        self.assertEqual([(c.wealth, c.job, c.daily_wage) for c in first.world.citizens],
                         [(c.wealth, c.job, c.daily_wage) for c in second.world.citizens])
        self.assertEqual(first.crime_events, second.crime_events)


class ControllerIndependentReview(unittest.TestCase):
    def setUp(self):
        self.state = {"sim": Simulation(7, 40), "budget": Budget(), "api_key": "", "ai_enabled": False}

    def preview(self):
        self.state["god_pending"] = {"id": "review-plan", "fingerprint": plan_fingerprint(self.state["sim"]),
                                     "plan": plan(action()), "preview": {"effects": ["Food +20"]}}

    def test_same_day_stale_confirm_rejected_without_mutation(self):
        self.preview()
        self.state["sim"].intervene("storm")
        before = self.state["sim"].save()
        with self.assertRaises(ValueError):
            handle_action(self.state, {"action": "god_apply", "plan_id": "review-plan"})
        self.assertEqual(self.state["sim"].save(), before)
        self.assertIsNone(self.state["god_pending"])

    def test_confirm_consumed_and_duplicate_cannot_apply(self):
        self.preview()
        handle_action(self.state, {"action": "god_apply", "plan_id": "review-plan"})
        before = self.state["sim"].save()
        with self.assertRaises(ValueError):
            handle_action(self.state, {"action": "god_apply", "plan_id": "review-plan"})
        self.assertEqual(self.state["sim"].save(), before)

    def test_key_and_budget_survive_world_reset_but_do_not_leak(self):
        handle_action(self.state, {"action": "configure_ai", "api_key": "fake-review-key", "model": "test-model",
                                   "enabled": True, "max_calls": 7})
        self.state["budget"].calls = 3
        handle_action(self.state, {"action": "reset", "seed": 99, "population": 40})
        self.assertEqual(self.state["api_key"], "fake-review-key")
        self.assertEqual(self.state["budget"].calls, 3)
        self.assertNotIn("fake-review-key", json.dumps(public_ai(self.state)))
        self.assertNotIn("fake-review-key", self.state["sim"].save())
        handle_action(self.state, {"action": "forget_ai"})
        self.assertEqual(self.state["api_key"], "")
        self.assertFalse(public_ai(self.state)["enabled"])
        self.assertEqual(self.state["budget"].calls, 3)

    def test_invalid_settings_do_not_partially_update(self):
        before = dict(self.state)
        with self.assertRaises(ValueError):
            handle_action(self.state, {"action": "configure_ai", "api_key": "fake-review-key", "model": "test-model",
                                       "enabled": "true", "max_calls": 7})
        self.assertEqual(self.state, before)


if __name__ == "__main__":
    unittest.main()
