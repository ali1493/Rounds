"""
Dataclasses for Rounds. Kept minimal on purpose.
"""
from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


@dataclass(frozen=True)
class Violation:
    """A safety constraint violation on a stop. Hard violations block the stop."""
    constraint: str        # e.g. "wheelchair_vehicle_mismatch"
    severity: str          # "block" or "warn"
    message: str           # plain-English explanation


@dataclass
class StopCard:
    """One delivery stop, annotated with everything the driver needs."""
    route_stop_id: str
    route_id: str
    sequence_index: int
    client_id: str
    client_first_name: str
    client_last_name: str
    address_street: str
    unit_number: Optional[str]
    buzzer_code: Optional[str]
    address_city: str
    planned_arrival: Optional[str]   # ISO timestamp string
    
    # Safety flags surfaced from client data
    mobility_wheelchair: bool
    has_dog_on_premises: bool
    do_not_enter_home: bool
    requires_two_person_team: bool
    severe_allergens: list[str] = field(default_factory=list)   # e.g. ["peanut", "shellfish"]
    
    # Vehicle assigned to this route
    vehicle_id: str = ""
    vehicle_has_lift: bool = False
    vehicle_refrigerated: bool = False
    
    # Computed violations
    violations: list[Violation] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return any(v.severity == "block" for v in self.violations)