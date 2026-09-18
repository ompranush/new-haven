"""Independent contracts for consequential interventions, not cosmetic events."""
import math
import unittest
from unittest.mock import patch

from src.civilisation.sim import Simulation


class ConsequentialWorldAcceptance(unittest.TestCase):
    def test_relief_is_not_a_repeatable_money_and_food_faucet(self):
        world = Simulation(7, 100)
        world.intervene("storm")
        food, treasury = world.world.food, world.world.treasury
        world.intervene("aid")
        self.assertGreater(world.world.food, food)
        self.assertLess(world.world.treasury, treasury)
        after = world.save()
        with self.assertRaises(ValueError):
            world.intervene("aid")
        self.assertEqual(world.save(), after, "Rejected repeat relief must be atomic")

    def test_storm_has_multi_day_food_and_fiscal_consequences(self):
        for seed in (0, 7, 19, 42):
            with self.subTest(seed=seed):
                baseline = Simulation(seed, 100)
                storm = Simulation.load(baseline.save())
                storm.intervene("storm")
                self.assertLess(storm.world.food, baseline.world.food)
                # Remove additional weather shocks, not citizen randomness: this
                # isolates the persistence of the one deliberately introduced storm.
                with patch.object(baseline.rng, "choices", return_value=["Clear"]), patch.object(storm.rng, "choices", return_value=["Clear"]):
                    baseline.step(7)
                    storm.step(7)
                self.assertLess(storm.world.food, baseline.world.food)
                self.assertLess(storm.world.treasury, baseline.world.treasury)

    def test_resume_preserves_consequences_and_future_randomness(self):
        original = Simulation(19, 100)
        with patch.object(original.rng, "choices", return_value=["Clear"]):
            original.step(15)
        original.intervene("storm")
        resumed = Simulation.load(original.save())
        self.assertEqual(original.snapshot(), resumed.snapshot())
        original.step(35)
        resumed.step(35)
        self.assertEqual(original.save(), resumed.save())

    def test_unfunded_relief_rejection_changes_nothing(self):
        world = Simulation(7, 100)
        world.intervene("storm")
        world.world.treasury = 0
        before = world.save()
        with self.assertRaises(ValueError):
            world.intervene("aid")
        self.assertEqual(before, world.save())

    def test_recovery_consumes_real_funds_and_materials_not_time_alone(self):
        world = Simulation(7, 100)
        world.intervene("storm")
        damaged = [b["condition"] for b in world.buildings]
        self.assertTrue(any(value < 100 for value in damaged))
        world.world.treasury = 0
        world._repair_buildings()
        self.assertEqual(damaged, [b["condition"] for b in world.buildings])
        world.world.treasury = 100
        wood, stone = world.resources["wood"], world.resources["stone"]
        world._repair_buildings()
        self.assertGreater(sum(b["condition"] for b in world.buildings), sum(damaged))
        self.assertTrue(any(b["condition"] < 100 for b in world.buildings))
        self.assertLess(world.world.treasury, 100)
        self.assertLess(world.resources["wood"], wood)
        self.assertLess(world.resources["stone"], stone)
        after = [b["condition"] for b in world.buildings]
        world.resources["wood"] = 0
        world._repair_buildings()
        self.assertEqual(after, [b["condition"] for b in world.buildings])

    def test_daily_resource_ledgers_explain_stock_changes(self):
        world = Simulation(42, 100)
        for day in range(90):
            world.step()
            ledger = world.ledger
            with self.subTest(day=day):
                self.assertAlmostEqual(ledger["food_closing"], ledger["food_opening"] + ledger["food_produced"] + ledger["food_imported"] - ledger["food_consumed"] - ledger["food_lost"], places=6)
                self.assertAlmostEqual(ledger["money_closing"], ledger["money_opening"] + ledger["trade_income"] - ledger["maintenance_cost"] - ledger["repair_cost"] - ledger["relief_cost"], places=6)

    def test_multi_seed_years_keep_resources_and_needs_valid(self):
        for seed in (0, 7, 19, 42):
            with self.subTest(seed=seed):
                world = Simulation(seed, 100)
                world.step(365)
                self.assertGreater(len(world.living), 0)
                for value in (world.world.food, world.world.treasury):
                    self.assertTrue(math.isfinite(value) and value >= 0)
                for business in world.businesses:
                    self.assertTrue(math.isfinite(business["cash"]) and business["cash"] >= 0)
                for citizen in world.living:
                    for name in ("happiness", "health", "energy", "hunger"):
                        self.assertTrue(0 <= getattr(citizen, name) <= 100)
                    self.assertGreaterEqual(citizen.wealth, 0)
                self.assertEqual(world.save(), Simulation.load(world.save()).save())
