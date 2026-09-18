import json
import unittest
from urllib.error import URLError

from src.civilisation.cognition import Budget
from src.civilisation.godmode import apply_plan, dry_run, interpret_command, validate_plan
from src.civilisation.sim import Simulation


def action(kind, target, amount):
    return {"kind": kind, "target": target, "amount": amount, "reason": "Player requested this change."}


def plan(*actions):
    return {"summary": "A bounded world change.", "actions": list(actions), "limitations": []}


def response(value, **extra):
    return {"status": "completed", "usage": {"total_tokens": 120},
            "output": [{"content": [{"type": "output_text", "text": json.dumps(value)}]}], **extra}


class GodModeTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation(7, 30)

    def test_resources_have_exact_audit_and_preview_does_not_mutate(self):
        before = self.sim.save()
        command = plan(action("resource", "food", 50), action("resource", "treasury", -20), action("resource", "wood", 10))
        preview = dry_run(self.sim, command)
        self.assertEqual(self.sim.save(), before)
        result = apply_plan(self.sim, command)
        self.assertEqual(preview["after"]["food"], result.world.food)
        self.assertEqual(result.ledger["food_imported"], 50)
        self.assertEqual(result.ledger["god_money_removed"], 20)
        self.assertEqual(result.ledger["god_wood_added"], 10)
        self.assertAlmostEqual(result.ledger["money_closing"], result.ledger["money_opening"]-20)
        self.assertEqual(len([e for e in result.world.events if e["kind"] == "god_mode"]), 3)
        self.assertEqual(Simulation.load(result.save()).save(), result.save())

    def test_repair_spends_exact_resources_and_reduces_damage(self):
        damaged = apply_plan(self.sim, plan(action("building_damage", "0", 20)))
        repaired = apply_plan(damaged, plan(action("building_repair", "0", 10)))
        self.assertEqual(repaired.buildings[0]["condition"], 90)
        self.assertEqual(repaired.world.treasury, self.sim.world.treasury-20)
        self.assertEqual(repaired.resources["wood"], self.sim.resources["wood"]-5)
        self.assertEqual(repaired.resources["stone"], self.sim.resources["stone"]-3)
        self.assertEqual(repaired.ledger["repair_cost"], 20)

    def test_over_repair_or_unfunded_repair_is_atomic(self):
        self.sim.buildings[0]["condition"] = 80
        self.sim.world.treasury = 1
        original = self.sim.save()
        for value in (10, 21):
            with self.assertRaises(ValueError):
                apply_plan(self.sim, plan(action("building_repair", "0", value)))
            self.assertEqual(self.sim.save(), original)

    def test_council_and_tax_preserve_cooldowns(self):
        taxed = apply_plan(self.sim, plan(action("tax", "village", .15)))
        self.assertEqual(taxed.policies["tax_rate"], .15)
        with self.assertRaises(ValueError):
            apply_plan(taxed, plan(action("tax", "village", .08)))
        festival = apply_plan(self.sim, plan(action("council", "festival", 1)))
        self.assertEqual(festival.world.treasury, self.sim.world.treasury-40)
        with self.assertRaises(ValueError):
            apply_plan(festival, plan(action("council", "festival", 1)))

    def test_relationship_changes_are_bidirectional_bounded_not_marriage(self):
        self.sim.world.citizens[0].relationships["1"] = 95
        result = apply_plan(self.sim, plan(action("relationship", "0:1", 25)))
        self.assertEqual(result.world.citizens[0].relationships["1"], 100)
        self.assertEqual(result.world.citizens[1].relationships["0"], 25)
        self.assertIsNone(result.world.citizens[0].partner_id)
        with self.assertRaises(ValueError):
            apply_plan(self.sim, plan(action("relationship", "0:3000", 25)))

    def test_unsupported_request_returns_no_actions(self):
        unsupported = {"summary": "Cannot implement this request.", "actions": [], "limitations": ["War is not simulated."]}
        original = self.sim.save()
        result = interpret_command(self.sim, "Start a war", "fake-key", "model", Budget(), lambda _: response(unsupported))
        self.assertEqual(result, unsupported)
        self.assertEqual(apply_plan(self.sim, result).save(), original)

    def test_prompt_contains_no_key_and_uses_strict_output_without_tools(self):
        command = plan(action("resource", "food", 10))
        def transport(payload):
            self.assertNotIn("fake-secret-key", json.dumps(payload))
            self.assertTrue(payload["text"]["format"]["strict"])
            self.assertFalse(payload["store"])
            self.assertNotIn("tools", payload)
            return response(command)
        budget = Budget()
        result = interpret_command(self.sim, "Add 10 meals", "fake-secret-key", "model", budget, transport)
        self.assertEqual(result, command)
        self.assertEqual(budget.calls, 1)
        self.assertEqual(budget.tokens, 120)
        self.assertNotIn("fake-secret-key", self.sim.save())

    def test_invalid_user_input_does_not_spend_calls(self):
        budget = Budget()
        for value in ("", " "*30, "x"*2001, None):
            with self.assertRaises(ValueError):
                interpret_command(self.sim, value, "fake-key", "model", budget, lambda _: self.fail("Called"))
        self.assertEqual(budget.calls, 0)

    def test_failed_requests_count_once_and_never_mutate(self):
        before = self.sim.save()
        budget = Budget()
        def failed(_):
            raise URLError("offline")
        with self.assertRaises(ValueError):
            interpret_command(self.sim, "Add 10 meals", "fake-key", "model", budget, failed)
        self.assertEqual(budget.calls, 1)
        self.assertEqual(self.sim.save(), before)

    def test_incomplete_calls_still_account_reported_tokens(self):
        budget = Budget()
        with self.assertRaises(ValueError):
            interpret_command(self.sim, "Add 10 meals", "fake-key", "model", budget,
                              lambda _: response({}, status="incomplete"))
        self.assertEqual(budget.tokens, 120)

    def test_duplicate_actions_and_aggregate_cap_rejected(self):
        for value in (plan(action("resource", "food", 6000), action("resource", "wood", 6000)),
                      plan(action("resource", "food", 10), action("resource", "food", 10)),
                      plan(action("relationship", "0:1", 25), action("relationship", "1:0", 25)),
                      plan(action("resource", "food", 10**1000))):
            with self.assertRaises(ValueError):
                validate_plan(value)

    def test_invalid_key_header_cannot_leak_key_in_error(self):
        budget = Budget()
        with self.assertRaises(ValueError) as caught:
            interpret_command(self.sim, "Add 10 meals", "secret\nkey", "model", budget, lambda _: self.fail("Called"))
        self.assertNotIn("secret", str(caught.exception))
        self.assertEqual(budget.calls, 0)

    def test_invalid_targets_reject_all_prior_changes(self):
        before = self.sim.save()
        with self.assertRaises(ValueError):
            apply_plan(self.sim, plan(action("resource", "food", 10), action("building_damage", "3000", 10)))
        self.assertEqual(self.sim.save(), before)


if __name__ == "__main__":
    unittest.main()
