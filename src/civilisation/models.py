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
    sociability: float
    ambition: float
    goal: str
    partner_id: Optional[int] = None
    alive: bool = True
    relationships: dict[int, float] = field(default_factory=dict)

@dataclass
class World:
    day: int
    food: float
    citizens: list[Citizen]
    events: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
