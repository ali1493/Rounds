"""
Load route data from parquet files and annotate with constraint violations.
"""
import duckdb
from pathlib import Path
from rounds.models import StopCard
from rounds.constraints import check_all, SEVERE_ALLERGENS_TO_CHECK


# Update this path if your kit is elsewhere
DATA_DIR = Path(r"C:\Users\LENOVO\Documents\Heckathon\buildersvault-hackathon-kit-main\tracks\food-security-delivery\data\raw")


def _connect():
    """Open a duckdb connection with parquet views registered."""
    con = duckdb.connect()
    tables = ['clients', 'drivers', 'vehicles', 'depots', 'routes',
              'route_stops', 'delivery_requests', 'delivery_request_items',
              'inventory_items']
    for t in tables:
        path = DATA_DIR / f"{t}.parquet"
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{path}')")
    return con


def list_routes_for_driver(driver_id: str) -> list[dict]:
    """List all routes assigned to a driver, most recent first."""
    con = _connect()
    rows = con.execute("""
        SELECT
            r.route_id,
            r.service_date,
            r.driver_id,
            r.vehicle_id,
            r.planned_start_time,
            r.planned_end_time,
            r.planned_stops,
            v.type AS vehicle_type,
            v.wheelchair_lift,
            v.refrigerated
        FROM routes r
        JOIN vehicles v ON r.vehicle_id = v.vehicle_id
        WHERE r.driver_id = ?
        ORDER BY r.service_date DESC
    """, [driver_id]).fetchdf()
    return rows.to_dict(orient='records')


def list_drivers() -> list[dict]:
    """Get the list of drivers for the login dropdown."""
    con = _connect()
    rows = con.execute("""
        SELECT driver_id, first_name, last_name, role_type
        FROM drivers
        ORDER BY driver_id
    """).fetchdf()
    return rows.to_dict(orient='records')


def get_stops_for_route(route_id: str) -> list[StopCard]:
    """
    Returns annotated StopCards for the given route, in sequence order.
    Each card has its safety flags computed and constraint violations attached.
    """
    con = _connect()
    
    # Build allergen severity columns for the SELECT
    allergen_cols = ", ".join(
        f"c.allergy_{a}_severity AS allergy_{a}" for a in SEVERE_ALLERGENS_TO_CHECK
    )
    
    rows = con.execute(f"""
        SELECT
            rs.route_stop_id,
            rs.route_id,
            rs.sequence_index,
            rs.planned_arrival,
            c.client_id,
            c.first_name AS client_first_name,
            c.last_name AS client_last_name,
            c.address_street,
            c.unit_number,
            c.buzzer_code,
            c.address_city,
            c.mobility_wheelchair,
            c.has_dog_on_premises,
            c.do_not_enter_home,
            c.requires_two_person_team,
            c.enrolment_status,
            c.closure_date,
            r.service_date,
            v.vehicle_id,
            v.wheelchair_lift,
            v.refrigerated,
            {allergen_cols}
        FROM route_stops rs
        JOIN clients c ON rs.client_id = c.client_id
        JOIN routes r ON rs.route_id = r.route_id
        JOIN vehicles v ON r.vehicle_id = v.vehicle_id
        WHERE rs.route_id = ?
        ORDER BY rs.sequence_index
    """, [route_id]).fetchdf()
    
    cards = []
    for _, row in rows.iterrows():
        # Collect severe allergens
        severe = [a for a in SEVERE_ALLERGENS_TO_CHECK if row[f"allergy_{a}"] == "severe"]
        
        card = StopCard(
            route_stop_id=row["route_stop_id"],
            route_id=row["route_id"],
            sequence_index=int(row["sequence_index"]),
            client_id=row["client_id"],
            client_first_name=row["client_first_name"],
            client_last_name=row["client_last_name"],
            address_street=row["address_street"],
            unit_number=row.get("unit_number"),
            buzzer_code=row.get("buzzer_code"),
            address_city=row["address_city"],
            planned_arrival=str(row["planned_arrival"]) if row["planned_arrival"] else None,
            mobility_wheelchair=bool(row["mobility_wheelchair"]),
            has_dog_on_premises=bool(row["has_dog_on_premises"]),
            do_not_enter_home=bool(row["do_not_enter_home"]),
            requires_two_person_team=bool(row["requires_two_person_team"]),
            severe_allergens=severe,
            vehicle_id=row["vehicle_id"],
            vehicle_has_lift=bool(row["wheelchair_lift"]),
            vehicle_refrigerated=bool(row["refrigerated"]),
        )
        
        # Run constraint checks
        card.violations = check_all(
            card,
            enrolment_status=str(row["enrolment_status"]),
            closure_date=str(row["closure_date"]) if row["closure_date"] else None,
            service_date=str(row["service_date"]),
        )
        
        cards.append(card)
    
    return cards


if __name__ == "__main__":
    # Smoke test: load our hero violation route
    cards = get_stops_for_route("RTE-0002")
    blocked = [c for c in cards if c.is_blocked]
    print(f"RTE-0002: {len(cards)} stops, {len(blocked)} blocked")
    for c in blocked[:3]:
        print(f"  Stop {c.sequence_index}: {c.client_first_name} {c.client_last_name}")
        for v in c.violations:
            print(f"    [{v.severity}] {v.constraint}: {v.message[:80]}")