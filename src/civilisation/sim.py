import random
from statistics import mean

from .models import Citizen, World

NAMES = ["Maya", "Theo", "Iris", "Noah", "Ava", "Leo", "Sana", "Finn", "Nia", "Owen"]
JOBS = {"Farmer": 14, "Baker": 18, "Builder": 21, "Teacher": 20, "Medic": 26, "Merchant": 24}
GOALS = ["save for a home", "make a close friend", "master a craft", "start a family", "help the town"]


class Simulation:
    """A deterministic, rule-based civilisation. One step represents one day."""

    def __init__(self, seed: int = 7, population: int = 100):
        self.seed = seed
        self.rng = random.Random(seed)
        citizens = [
            Citizen(
                i,
                f"{self.rng.choice(NAMES)} {i + 1}",
                self.rng.randint(18, 62),
                self.rng.choice(list(JOBS)) if self.rng.random() > 0.12 else None,
                round(self.rng.uniform(15, 180), 2),
                round(self.rng.uniform(42, 78), 1),
                self.rng.random(),
                self.rng.random(),
                self.rng.choice(GOALS),
                x=self.rng.randint(2, 10),
                y=self.rng.randint(1, 7),
            )
            for i in range(population)
        ]
        self.world = World(0, population * 2.2, citizens)
        self._record()

    @property
    def living(self):
        return [citizen for citizen in self.world.citizens if citizen.alive]

    def step(self, days: int = 1) -> None:
        if days < 1:
            raise ValueError("days must be at least one")
        for _ in range(days):
            self._step_one_day()

    def _step_one_day(self) -> None:
        world, people = self.world, self.living
        world.day += 1
        world.weather = self.rng.choices(["Clear", "Rain", "Wind"], weights=[6, 2, 1])[0]
        harvest_factor = 0.75 if world.weather == "Wind" else 1.15 if world.weather == "Rain" else 1.0
        world.food = max(
            0,
            world.food
            + sum(citizen.job == "Farmer" for citizen in people) * self.rng.uniform(1.2, 2.3) * harvest_factor
            - len(people) * 0.9,
        )
        for citizen in people:
            citizen.age += 1 / 365
            citizen.x = min(10, max(2, citizen.x + self.rng.choice((-1, 0, 1))))
            citizen.y = min(7, max(1, citizen.y + self.rng.choice((-1, 0, 1))))
            if citizen.job:
                citizen.wealth += JOBS[citizen.job] / 30
                citizen.happiness += 0.08
            elif self.rng.random() < 0.02:
                citizen.job = self.rng.choice(list(JOBS))
                self._event(f"{citizen.name} found work as a {citizen.job}.")
                citizen.remember(f"Found work as a {citizen.job} on day {world.day}.")
            else:
                citizen.happiness -= 0.25
            citizen.happiness = max(0, min(100, citizen.happiness - (0.7 if world.food == 0 else 0)))
        self._socialise()
        self._life_events()
        self._world_event()
        if world.food < max(12, len(self.living) * 0.25):
            self._food_shortage()
        self._record()

    def _socialise(self) -> None:
        people = self.living[:]
        self.rng.shuffle(people)
        for citizen, other in zip(people[::2], people[1::2]):
            bond = citizen.relationships.get(other.id, 0) + self.rng.uniform(1, 4) * (0.5 + citizen.sociability)
            citizen.relationships[other.id] = other.relationships[citizen.id] = bond
            if bond > 18 and self.rng.random() < 0.12:
                citizen.remember(f"Spent time with {other.name} on day {self.world.day}.")
                other.remember(f"Spent time with {citizen.name} on day {self.world.day}.")
            if bond > 24 and not citizen.partner_id and not other.partner_id:
                citizen.partner_id, other.partner_id = other.id, citizen.id
                self._event(f"{citizen.name} and {other.name} became partners.")
                citizen.remember(f"Began a partnership with {other.name}.")
                other.remember(f"Began a partnership with {citizen.name}.")

    def _life_events(self) -> None:
        for citizen in list(self.living):
            if self.rng.random() < 0.00002 + max(0, citizen.age - 70) * 0.00008:
                citizen.alive = False
                self._event(f"{citizen.name} died at age {int(citizen.age)}.")
        parents = [citizen for citizen in self.living if citizen.partner_id and 22 <= citizen.age <= 42]
        if parents and self.rng.random() < len(parents) * 0.001:
            parent = self.rng.choice(parents)
            baby = Citizen(
                len(self.world.citizens),
                f"{self.rng.choice(NAMES)} {len(self.world.citizens) + 1}",
                0,
                None,
                0,
                70,
                self.rng.random(),
                self.rng.random(),
                self.rng.choice(GOALS),
                x=parent.x,
                y=parent.y,
            )
            baby.remember(f"Born into {parent.name}'s household on day {self.world.day}.")
            self.world.citizens.append(baby)
            self._event(f"{parent.name}'s household welcomed {baby.name}.")

    def _world_event(self) -> None:
        if self.rng.random() >= 0.06:
            return
        event = self.rng.choice([
            "A warm rain improved the harvest.",
            "A trade caravan brought rare tools.",
            "A cold snap damaged stored food.",
            "A festival lifted the town's spirits.",
        ])
        self._event(event)
        if "harvest" in event:
            self.world.food += len(self.living) * 0.35
        elif "caravan" in event:
            self.world.treasury += 35
        elif "cold" in event:
            self.world.food = max(0, self.world.food - len(self.living) * 0.3)
        elif "festival" in event:
            for citizen in self.living:
                citizen.happiness = min(100, citizen.happiness + 4)
                citizen.remember(f"Joined the lantern festival on day {self.world.day}.")

    def _food_shortage(self) -> None:
        if not self.world.events or "Food stores are dangerously low." not in self.world.events[-1]:
            self._event("Food stores are dangerously low.")
            for citizen in self.living:
                citizen.happiness = max(0, citizen.happiness - 2)
                citizen.remember(f"Worried about scarce food on day {self.world.day}.")

    def _event(self, text: str) -> None:
        self.world.events.append(f"Day {self.world.day}: {text}")
        del self.world.events[:-40]

    def summary(self) -> dict:
        people = self.living
        return {
            "day": self.world.day,
            "population": len(people),
            "wealth": round(sum(citizen.wealth for citizen in people), 2),
            "happiness": round(mean(citizen.happiness for citizen in people), 1) if people else 0,
            "food": round(self.world.food, 1),
            "unemployment": round(100 * sum(citizen.job is None for citizen in people) / len(people), 1) if people else 0,
            "weather": self.world.weather,
        }

    def _record(self) -> None:
        self.world.history.append(self.summary())
