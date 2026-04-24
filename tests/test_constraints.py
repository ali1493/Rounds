"""
Tests that prove constraint enforcement rejects bad inputs.
This is a production-readiness signal called out in the framing doc.
"""
import pytest
from rounds.models import StopCard, Violation
from rounds.constraints import (
    check_severe_allergen,
    check_wheelchair_vehicle,
    check_closure_status,
    check_all,
)


def make_stop(**overrides) -> StopCard:
    """Helper: build a StopCard with sensible defaults, override what you need."""
    defaults = dict(
        route_stop_id="STOP-TEST",
        route_id="RTE-TEST",
        sequence_index=1,
        client_id="CLI-TEST",
        client_first_name="Test",
        client_last_name="Client",
        address_street="123 Main St",
        unit_number=None,
        buzzer_code=None,
        address_city="Victoria",
        planned_arrival="2026-04-25T09:00:00",
        mobility_wheelchair=False,
        has_dog_on_premises=False,
        do_not_enter_home=False,
        requires_two_person_team=False,
        severe_allergens=[],
        vehicle_id="VEH-99",
        vehicle_has_lift=False,
        vehicle_refrigerated=False,
    )
    defaults.update(overrides)
    return StopCard(**defaults)


# ---------- Severe allergen ----------

def test_severe_allergen_fires_when_present():
    stop = make_stop(severe_allergens=["peanut"])
    violations = check_severe_allergen(stop)
    assert len(violations) == 1
    assert violations[0].constraint == "severe_allergen"
    assert violations[0].severity == "warn"
    assert "peanut" in violations[0].message.lower()


def test_severe_allergen_silent_when_absent():
    stop = make_stop(severe_allergens=[])
    assert check_severe_allergen(stop) == []


def test_severe_allergen_reports_each():
    stop = make_stop(severe_allergens=["peanut", "shellfish"])
    violations = check_severe_allergen(stop)
    assert len(violations) == 2
    constraints = {v.message for v in violations}
    assert any("peanut" in m for m in constraints)
    assert any("shellfish" in m for m in constraints)


# ---------- Wheelchair / vehicle ----------

def test_wheelchair_blocks_when_no_lift():
    stop = make_stop(mobility_wheelchair=True, vehicle_has_lift=False, vehicle_id="VEH-07")
    violations = check_wheelchair_vehicle(stop)
    assert len(violations) == 1
    assert violations[0].severity == "block"
    assert violations[0].constraint == "wheelchair_vehicle_mismatch"


def test_wheelchair_silent_when_lift_present():
    stop = make_stop(mobility_wheelchair=True, vehicle_has_lift=True, vehicle_id="VEH-06")
    assert check_wheelchair_vehicle(stop) == []


def test_wheelchair_silent_for_non_wheelchair_client():
    stop = make_stop(mobility_wheelchair=False, vehicle_has_lift=False)
    assert check_wheelchair_vehicle(stop) == []


# ---------- Closure status ----------

def test_closure_blocks_for_deceased_client():
    stop = make_stop()
    violations = check_closure_status(
        stop,
        enrolment_status="deceased",
        closure_date="2026-03-01",
        service_date="2026-04-25",
    )
    assert len(violations) == 1
    assert violations[0].severity == "block"
    assert violations[0].constraint == "post_closure_delivery"


def test_closure_blocks_for_closed_client():
    stop = make_stop()
    violations = check_closure_status(
        stop,
        enrolment_status="closed",
        closure_date="2026-03-15",
        service_date="2026-04-25",
    )
    assert len(violations) == 1
    assert violations[0].severity == "block"


def test_closure_silent_for_active_client():
    stop = make_stop()
    violations = check_closure_status(
        stop,
        enrolment_status="active",
        closure_date=None,
        service_date="2026-04-25",
    )
    assert violations == []


def test_closure_silent_for_paused_client():
    stop = make_stop()
    # paused clients ARE on-route deliberately
    violations = check_closure_status(
        stop,
        enrolment_status="paused",
        closure_date=None,
        service_date="2026-04-25",
    )
    assert violations == []


# ---------- Combined ----------

def test_check_all_combines_violations():
    stop = make_stop(
        mobility_wheelchair=True,
        vehicle_has_lift=False,
        severe_allergens=["peanut"],
    )
    violations = check_all(
        stop,
        enrolment_status="deceased",
        closure_date="2026-03-01",
        service_date="2026-04-25",
    )
    # Should fire all three: allergen warn + wheelchair block + closure block
    assert len(violations) == 3
    severities = [v.severity for v in violations]
    assert severities.count("block") == 2
    assert severities.count("warn") == 1
