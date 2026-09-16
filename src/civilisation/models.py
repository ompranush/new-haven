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
    x: int = 0
    y: int = 0
    memories: list[str] = field(default_factory=list)
    relationships: dict[int, float] = field(default_factory=dict)

    def remember(self, memory: str) -> None:
        """Keep a small, human-readable personal history."""
        self.memories.append(memory)
        del self.memories[:-6]


@dataclass
class World:
    day: int
    food: float
    citizens: list[Citizen]
    width: int = 12
    height: int = 9
    weather: str = "Clear"
    treasury: float = 120.0
    events: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
