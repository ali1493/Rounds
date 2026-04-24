"""
Three constraint checks for Rounds.

Each function takes a StopCard and returns a Violation or None.
Pure functions — no I/O, no side effects, easy to test.
"""
from rounds.models import StopCard, Violation


# Allergens we check for at "severe" level
SEVERE_ALLERGENS_TO_CHECK = [
    "peanut", "tree_nut", "shellfish", "fish",
    "egg", "soy", "wheat", "dairy"
]


def check_severe_allergen(stop: StopCard) -> list[Violation]:
    """
    A client with a severe allergen flag means the driver must know.
    This doesn't BLOCK the stop — the system would have already filtered
    matching items at the depot. But the driver still needs to know
    in case of accidental cross-contact.
    """
    violations = []
    for allergen in stop.severe_allergens:
        violations.append(Violation(
            constraint="severe_allergen",
            severity="warn",
            message=f"Severe {allergen.replace('_', ' ')} allergy. Do not hand any food containing {allergen.replace('_', ' ')}. Call ops if anything looks uncertain.",
        ))
    return violations


def check_wheelchair_vehicle(stop: StopCard) -> list[Violation]:
    """
    Wheelchair clients must be served by a vehicle with a wheelchair lift.
    This is a hard block — if the vehicle doesn't have a lift,
    the driver cannot complete the delivery. Call ops to reassign.
    """
    if stop.mobility_wheelchair and not stop.vehicle_has_lift:
        return [Violation(
            constraint="wheelchair_vehicle_mismatch",
            severity="block",
            message=f"Client uses a wheelchair but vehicle {stop.vehicle_id} has no lift. Stop cannot be completed. Call ops.",
        )]
    return []


def check_closure_status(stop: StopCard, enrolment_status: str, closure_date: str | None, service_date: str) -> list[Violation]:
    """
    Closed or deceased clients should not receive deliveries.
    The fact that this stop is even on the route means something
    went wrong upstream. Block and call ops — do not knock on the door.
    """
    if enrolment_status in ("deceased", "closed"):
        if closure_date and service_date and service_date >= closure_date:
            return [Violation(
                constraint="post_closure_delivery",
                severity="block",
                message=f"Client enrolment is {enrolment_status} (since {closure_date}). Do not attempt delivery. Call ops to remove from route.",
            )]
    return []


def check_all(stop: StopCard, enrolment_status: str, closure_date: str | None, service_date: str) -> list[Violation]:
    """Run all constraint checks on a stop. Returns combined list of violations."""
    violations = []
    violations.extend(check_severe_allergen(stop))
    violations.extend(check_wheelchair_vehicle(stop))
    violations.extend(check_closure_status(stop, enrolment_status, closure_date, service_date))
    return violations