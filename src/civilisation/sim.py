import random
from statistics import mean

from .models import Citizen, World

NAMES = ["Maya", "Theo", "Iris", "Noah", "Ava", "Leo", "Sana", "Finn", "Nia", "Owen"]
JOBS = {"Farmer": 1.45, "Baker": 1.65, "Builder": 1.85, "Teacher": 1.75, "Medic": 2.05, "Merchant": 1.9}
GOALS = ["save for a home", "make a close friend", "master a craft", "start a family", "help the town"]
WORKPLACES = {"Farmer": (3, 6), "Baker": (8, 3), "Builder": (10, 6), "Teacher": (7, 2), "Medic": (7, 2), "Merchant": (8, 3)}
LANDMARKS = {"farm": (3, 6), "market": (8, 3), "workshop": (10, 6), "square": (6, 4), "home": (5, 6)}


class Simulation:
    """A reproducible, rule-based civilisation where one step is one day."""

    def __init__(self, seed: int = 7, population: int = 100):
        self.seed = seed
        self.rng = random.Random(seed)
        citizens = [
            Citizen(
                i, f"{self.rng.choice(NAMES)} {i + 1}", self.rng.randint(18, 62),
                self.rng.choice(list(JOBS)) if self.rng.random() > 0.12 else None,
                round(self.rng.uniform(15, 180), 2), round(self.rng.uniform(42, 78), 1),
                self.rng.random(), self.rng.random(), self.rng.choice(GOALS),
                x=self.rng.randint(2, 10), y=self.rng.randint(1, 7),
                energy=round(self.rng.uniform(58, 92), 1), hunger=round(self.rng.uniform(5, 25), 1),
            )
            for i in range(population)
        ]
        self.world = World(0, population * 2.4, citizens)
        self._record()

    @property
    def living(self):
        return [citizen for citizen in self.world.citizens if citizen.alive]

    def step(self, days: int = 1) -> None:
        if not 1 <= days <= 3650:
            raise ValueError("days must be between 1 and 3650")
        for _ in range(days):
            self._step_one_day()

    def intervene(self, scenario: str) -> None:
        """Apply a deliberate, recorded world intervention."""
        effects = {
            "festival": ("The council funded a lantern festival.", lambda: self._festival()),
            "storm": ("A severe river storm hit New Haven.", lambda: self._storm()),
            "aid": ("A relief convoy replenished town stores.", lambda: self._aid()),
            "market": ("The market introduced a food-price cap.", lambda: self._price_cap()),
        }
        if scenario not in effects:
            raise ValueError("unknown intervention")
        message, apply = effects[scenario]
        apply()
        self._event(message)

    def _step_one_day(self) -> None:
        world, people = self.world, self.living
        world.day += 1
        world.weather = self.rng.choices(["Clear", "Rain", "Wind"], weights=[6, 2, 1])[0]
        farmer_count = sum(citizen.job == "Farmer" for citizen in people)
        harvest = farmer_count * (5.8 if world.weather == "Rain" else 4.7 if world.weather == "Clear" else 3.4)
        world.food = max(0, world.food + harvest - len(people) * 1.0)
        scarcity = max(0, len(people) * 1.5 - world.food) / max(1, len(people))
        world.food_price = round(min(2.5, max(0.55, 0.78 + scarcity * 0.32)), 2)
        for citizen in people:
            self._live_day(citizen)
        self._socialise()
        self._life_events()
        self._world_event()
        if world.food < max(10, len(self.living) * 0.18):
            self._food_shortage()
        self._record()

    def _live_day(self, citizen: Citizen) -> None:
        world = self.world
        if citizen.job:
            wage = JOBS[citizen.job] * (0.75 + 0.35 * citizen.ambition) * (0.6 + 0.4 * citizen.energy / 100)
            tax = wage * 0.06
            citizen.wealth += wage - tax
            world.treasury += tax
            citizen.activity = f"working at the {citizen.job.lower()} site"
            target = WORKPLACES[citizen.job]
            citizen.energy = max(18, citizen.energy - self.rng.uniform(4, 9))
        elif self.rng.random() < 0.025 + (0.025 if citizen.wealth < 10 else 0):
            citizen.job = self.rng.choice(list(JOBS))
            citizen.activity = "starting a new job"
            citizen.remember(f"Found work as a {citizen.job} on day {world.day}.")
            self._event(f"{citizen.name} found work as a {citizen.job}.")
            target = WORKPLACES[citizen.job]
        else:
            citizen.activity = "looking for work"
            target = LANDMARKS["market"]
            citizen.energy = min(100, citizen.energy + self.rng.uniform(1, 5))

        meal_cost = world.food_price
        citizen.hunger = min(100, citizen.hunger + 11)
        if world.food >= 1 and citizen.wealth >= meal_cost:
            world.food -= 1
            citizen.wealth -= meal_cost
            citizen.hunger = max(0, citizen.hunger - 22)
            citizen.activity = citizen.activity if citizen.job else "buying food at the market"
        else:
            citizen.hunger = min(100, citizen.hunger + 8)
            citizen.remember(f"Could not afford a full meal on day {world.day}.")
        citizen.wealth -= 0.23  # shared housing and upkeep
        wellbeing = (citizen.energy - 55) / 90 - citizen.hunger / 70 + (0.35 if citizen.wealth > 10 else -0.45)
        citizen.happiness = max(0, min(100, citizen.happiness + wellbeing + self.rng.uniform(-0.5, 0.5)))
        citizen.age += 1 / 365
        self._move_towards(citizen, target)

    def _move_towards(self, citizen: Citizen, target: tuple[int, int]) -> None:
        x, y = citizen.x, citizen.y
        citizen.x = min(10, max(2, x + (target[0] > x) - (target[0] < x)))
        citizen.y = min(7, max(1, y + (target[1] > y) - (target[1] < y)))

    def _socialise(self) -> None:
        people = self.living[:]
        self.rng.shuffle(people)
        for citizen, other in zip(people[::2], people[1::2]):
            if self.rng.random() > 0.18 + 0.42 * citizen.sociability:
                continue
            bond = citizen.relationships.get(other.id, 0) + self.rng.uniform(0.8, 2.8)
            citizen.relationships[other.id] = other.relationships[citizen.id] = bond
            citizen.activity = f"talking with {other.name}"
            other.activity = f"talking with {citizen.name}"
            if self.rng.random() < 0.35:
                citizen.remember(f"Talked with {other.name} on day {self.world.day}.")
                other.remember(f"Talked with {citizen.name} on day {self.world.day}.")
                citizen.happiness = min(100, citizen.happiness + 0.8)
                other.happiness = min(100, other.happiness + 0.8)
            if bond > 24 and not citizen.partner_id and not other.partner_id:
                citizen.partner_id, other.partner_id = other.id, citizen.id
                self._event(f"{citizen.name} and {other.name} became partners.")

    def _life_events(self) -> None:
        for citizen in list(self.living):
            if self.rng.random() < 0.00002 + max(0, citizen.age - 70) * 0.00008:
                citizen.alive = False
                self._event(f"{citizen.name} died at age {int(citizen.age)}.")
        parents = [citizen for citizen in self.living if citizen.partner_id and 22 <= citizen.age <= 42 and citizen.hunger < 35]
        if parents and self.rng.random() < len(parents) * 0.0008:
            parent = self.rng.choice(parents)
            baby = Citizen(len(self.world.citizens), f"{self.rng.choice(NAMES)} {len(self.world.citizens)+1}", 0, None, 2, 70, self.rng.random(), self.rng.random(), self.rng.choice(GOALS), x=parent.x, y=parent.y, activity="resting at home")
            baby.remember(f"Born into {parent.name}'s household on day {self.world.day}.")
            self.world.citizens.append(baby)
            self._event(f"{parent.name}'s household welcomed {baby.name}.")

    def _world_event(self) -> None:
        if self.rng.random() >= 0.055:
            return
        event = self.rng.choice(["harvest", "trade", "cold", "festival"])
        if event == "harvest":
            self.world.food += len(self.living) * 0.45
            self._event("Warm rain improved the harvest.")
        elif event == "trade":
            self.world.treasury += 26
            self._event("A trade caravan brought rare tools.")
        elif event == "cold":
            self.world.food = max(0, self.world.food - len(self.living) * 0.35)
            self._event("A cold snap damaged stored food.")
        else:
            self._festival()
            self._event("A festival lifted the town's spirits.")

    def _festival(self) -> None:
        cost = min(18, self.world.treasury)
        self.world.treasury -= cost
        for citizen in self.living:
            citizen.happiness = min(100, citizen.happiness + 3)
            citizen.remember(f"Joined the lantern festival on day {self.world.day}.")

    def _storm(self) -> None:
        loss = min(self.world.food * 0.22, max(12, len(self.living) * 0.45))
        self.world.food -= loss
        self.world.weather = "Storm"
        for citizen in self.living:
            citizen.energy = max(0, citizen.energy - 6)
            citizen.remember(f"Weathered the river storm on day {self.world.day}.")

    def _aid(self) -> None:
        self.world.food += len(self.living) * 1.5
        self.world.treasury += 20

    def _price_cap(self) -> None:
        self.world.food_price = max(0.55, self.world.food_price - 0.18)
        self.world.treasury = max(0, self.world.treasury - 12)

    def _food_shortage(self) -> None:
        if not self.world.events or "Food stores are dangerously low." not in self.world.events[-1]:
            self._event("Food stores are dangerously low.")
            for citizen in self.living:
                citizen.happiness = max(0, citizen.happiness - 1.5)
                citizen.remember(f"Worried about scarce food on day {self.world.day}.")

    def _event(self, text: str) -> None:
        self.world.events.append(f"Day {self.world.day}: {text}")
        del self.world.events[:-60]

    def summary(self) -> dict:
        people = self.living
        return {
            "day": self.world.day, "population": len(people),
            "wealth": round(sum(c.wealth for c in people), 2),
            "happiness": round(mean(c.happiness for c in people), 1) if people else 0,
            "food": round(self.world.food, 1), "food_price": self.world.food_price,
            "treasury": round(self.world.treasury, 1), "weather": self.world.weather,
            "unemployment": round(100 * sum(c.job is None for c in people) / len(people), 1) if people else 0,
        }

    def _record(self) -> None:
        self.world.history.append(self.summary())
