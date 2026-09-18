import unittest
from src.civilisation.cognition import Budget, reflect, validate_decision


class FakeWorld:
    pending_decisions = [{"id": 1, "citizen_id": 0, "event": "A storm damaged the farm", "day": 2}]
    def __init__(self):
        self.applied = []
    def snapshot(self):
        return {"citizens": [{"id": 0, "name": "Maya", "memories": []}]}
    def apply_decision(self, *args):
        self.applied.append(args)


class CognitionTests(unittest.TestCase):
    def test_disabled_missing_key_never_calls_transport(self):
        with self.assertRaises(ValueError):
            reflect(FakeWorld(), "", "model", Budget(), lambda _: self.fail("network called"))

    def test_valid_response_applies_only_allowed_action(self):
        world, budget = FakeWorld(), Budget(max_calls=1)
        def transport(payload):
            self.assertFalse(payload["store"])
            self.assertLessEqual(payload["max_output_tokens"], 400)
            self.assertNotIn("api_key", payload)
            return {"usage": {"total_tokens": 80}, "output": [{"content": [{"type": "output_text", "text": '{"action":"help_neighbor","reason":"Help rebuild the farm."}'}]}]}
        reflect(world, "test-key", "model", budget, transport)
        self.assertEqual(world.applied[0][1], "help_neighbor")
        self.assertEqual(budget.tokens, 80)
        with self.assertRaises(ValueError):
            reflect(world, "test-key", "model", budget, lambda _: self.fail("budget bypass"))

    def test_invalid_response_cannot_change_world(self):
        world, budget = FakeWorld(), Budget()
        with self.assertRaises(ValueError):
            reflect(world, "test-key", "model", budget, lambda _: {"output": []})
        self.assertFalse(world.applied)
        self.assertEqual(budget.calls, 1)

    def test_arbitrary_actions_rejected(self):
        for value in ({"action": "delete_world", "reason": "test"}, {"action": "rest", "reason": "", "extra": 1}, []):
            with self.assertRaises(ValueError):
                validate_decision(value)
