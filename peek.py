import duckdb

DATA_DIR = r"C:\Users\LENOVO\Documents\Heckathon\buildersvault-hackathon-kit-main\tracks\food-security-delivery\data\raw"

con = duckdb.connect()

tables = ['clients', 'drivers', 'vehicles', 'depots', 'routes',
          'route_stops', 'delivery_requests', 'delivery_request_items',
          'inventory_items']

for t in tables:
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{DATA_DIR}\\{t}.parquet')")

print("=== Allergy severity values (peanut as example) ===")
print(con.execute("SELECT DISTINCT allergy_peanut_severity FROM clients ORDER BY 1").fetchdf())

print("\n=== Wheelchair clients ===")
print(con.execute("SELECT COUNT(*) AS wheelchair_clients FROM clients WHERE mobility_wheelchair = true").fetchdf())

print("\n=== Vehicles with lifts ===")
print(con.execute("SELECT vehicle_id, type, wheelchair_lift, refrigerated FROM vehicles ORDER BY vehicle_id").fetchdf())

print("\n=== Enrolment status distribution ===")
print(con.execute("SELECT enrolment_status, COUNT(*) FROM clients GROUP BY 1").fetchdf())

print("\n=== Example: 3 stops with client + driver + vehicle joined ===")
result = con.execute("""
    SELECT
        rs.sequence_index,
        c.client_id,
        c.first_name,
        c.last_name,
        c.mobility_wheelchair,
        c.allergy_peanut_severity,
        c.enrolment_status,
        d.driver_id,
        d.first_name AS driver_first,
        v.vehicle_id,
        v.wheelchair_lift,
        v.refrigerated
    FROM route_stops rs
    JOIN clients c ON rs.client_id = c.client_id
    JOIN routes r ON rs.route_id = r.route_id
    JOIN drivers d ON r.driver_id = d.driver_id
    JOIN vehicles v ON r.vehicle_id = v.vehicle_id
    LIMIT 3
""").fetchdf()
print(result.to_string())

print("\n=== Routes with both wheelchair clients and severe allergies (top 5) ===")
result = con.execute("""
    SELECT
        r.route_id,
        r.service_date,
        r.driver_id,
        r.vehicle_id,
        v.wheelchair_lift,
        v.refrigerated,
        COUNT(*) FILTER (WHERE c.mobility_wheelchair) AS wheelchair_stops,
        COUNT(*) FILTER (WHERE c.allergy_peanut_severity = 'severe'
                          OR c.allergy_tree_nut_severity = 'severe'
                          OR c.allergy_shellfish_severity = 'severe'
                          OR c.allergy_dairy_severity = 'severe') AS severe_allergy_stops,
        COUNT(*) AS total_stops
    FROM routes r
    JOIN route_stops rs ON r.route_id = rs.route_id
    JOIN clients c ON rs.client_id = c.client_id
    JOIN vehicles v ON r.vehicle_id = v.vehicle_id
    GROUP BY 1, 2, 3, 4, 5, 6
    HAVING wheelchair_stops > 0 AND severe_allergy_stops > 0
    ORDER BY wheelchair_stops DESC, severe_allergy_stops DESC
    LIMIT 5
""").fetchdf()
print(result.to_string())