from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Citizen:
    id: int
    name: str
    age: float
    job: Optional[str]
    wealth: float
    happiness: float
    personality: dict
    goal: str
    partner_id: Optional[int] = None
    alive: bool = True
    x: int = 0
    y: int = 0
    health: float = 100.0
    energy: float = 85.0
    hunger: float = 0.0
    activity: str = "settling in"
    goal_progress: float = 0.0
    memories: list = field(default_factory=list)
    relationships: dict = field(default_factory=dict)
    parent_ids: list = field(default_factory=list)
    gender: str = "unspecified"
    political_economic: float = 0.0
    political_social: float = 0.0
    daily_wage: float = 0.0

    def remember(self, text, day=0):
        self.memories.append({"day": day, "text": text})
        del self.memories[:-30]

@dataclass
class World:
    day: int
    food: float
    citizens: list
    width: int = 24
    height: int = 20
    weather: str = "Clear"
    treasury: float = 600.0
    food_price: float = 1.0
    events: list = field(default_factory=list)
    history: list = field(default_factory=list)
