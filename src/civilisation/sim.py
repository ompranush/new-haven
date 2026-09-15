import random
from statistics import mean

from .models import Citizen, World

NAMES = ["Maya", "Theo", "Iris", "Noah", "Ava", "Leo", "Sana", "Finn", "Nia", "Owen"]
JOBS = {"Farmer": 14, "Baker": 18, "Builder": 21, "Teacher": 20, "Medic": 26, "Merchant": 24}
GOALS = ["save for a home", "make a close friend", "master a craft", "start a family", "help the town"]

class Simulation:
    def __init__(self, seed=7, population=100):
        self.rng = random.Random(seed)
        citizens = [
            Citizen(i, f"{self.rng.choice(NAMES)} {i + 1}", self.rng.randint(18, 62),
                    self.rng.choice(list(JOBS)) if self.rng.random() > .12 else None,
                    round(self.rng.uniform(15, 180), 2), round(self.rng.uniform(42, 78), 1),
                    self.rng.random(), self.rng.random(), self.rng.choice(GOALS))
            for i in range(population)
        ]
        self.world = World(0, population * 2.2, citizens)
        self._record()

    @property
    def living(self):
        return [c for c in self.world.citizens if c.alive]

    def step(self):
        w, people = self.world, self.living
        w.day += 1
        w.food = max(0, w.food + sum(c.job == "Farmer" for c in people) * self.rng.uniform(1.2, 2.3) - len(people) * .9)
        for c in people:
            c.age += 1 / 365
            if c.job:
                c.wealth += JOBS[c.job] / 30
                c.happiness += .08
            elif self.rng.random() < .02:
                c.job = self.rng.choice(list(JOBS))
                w.events.append(f"{c.name} found work as a {c.job}.")
            else:
                c.happiness -= .25
            c.happiness = max(0, min(100, c.happiness - (.7 if w.food == 0 else 0)))
        self._socialise()
        self._life_events()
        if self.rng.random() < .06:
            event = self.rng.choice(["A warm rain improved the harvest.", "A trade caravan brought rare tools.", "A cold snap damaged stored food.", "A festival lifted the town's spirits."])
            w.events.append(event)
            if "harvest" in event: w.food += len(people) * .35
            if "cold" in event: w.food = max(0, w.food - len(people) * .3)
            if "festival" in event:
                for c in self.living: c.happiness = min(100, c.happiness + 4)
        self._record()

    def _socialise(self):
        people = self.living
        for c in people:
            if len(people) > 1 and self.rng.random() < c.sociability * .08:
                other = self.rng.choice(people)
                if other.id != c.id:
                    bond = c.relationships.get(other.id, 0) + self.rng.uniform(1, 4)
                    c.relationships[other.id] = other.relationships[c.id] = bond
                    if bond > 24 and not c.partner_id and not other.partner_id:
                        c.partner_id, other.partner_id = other.id, c.id
                        self.world.events.append(f"{c.name} and {other.name} became partners.")

    def _life_events(self):
        for c in list(self.living):
            if self.rng.random() < .00002 + max(0, c.age - 70) * .00008:
                c.alive = False
                self.world.events.append(f"{c.name} died at age {int(c.age)}.")
        parents = [c for c in self.living if c.partner_id and 22 <= c.age <= 42]
        if parents and self.rng.random() < len(parents) * .001:
            parent = self.rng.choice(parents)
            baby = Citizen(len(self.world.citizens), f"{self.rng.choice(NAMES)} {len(self.world.citizens)+1}", 0, None, 0, 70, self.rng.random(), self.rng.random(), self.rng.choice(GOALS))
            self.world.citizens.append(baby)
            self.world.events.append(f"{parent.name}'s household welcomed {baby.name}.")

    def summary(self):
        people = self.living
        return {"day": self.world.day, "population": len(people), "wealth": round(sum(c.wealth for c in people), 2), "happiness": round(mean(c.happiness for c in people), 1) if people else 0, "food": round(self.world.food, 1), "unemployment": round(100 * sum(c.job is None for c in people) / len(people), 1) if people else 0}

    def _record(self):
        self.world.history.append(self.summary())
