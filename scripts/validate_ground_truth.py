"""
Ground truth validation: scan every stop, run constraints, report counts.
"""
from collections import Counter
from rounds.loader import _connect, get_stops_for_route


def main():
    print("Starting validation...", flush=True)
    
    con = _connect()
    route_ids = con.execute("SELECT route_id FROM routes ORDER BY route_id").fetchdf()["route_id"].tolist()
    print(f"Found {len(route_ids)} routes. Scanning...", flush=True)
    
    total_stops = 0
    blocked_routes = set()
    constraint_counts = Counter()
    severity_counts = Counter()
    affected_routes = {}
    
    for i, route_id in enumerate(route_ids):
        if i % 50 == 0:
            print(f"  ...processed {i}/{len(route_ids)} routes", flush=True)
        
        stops = get_stops_for_route(route_id)
        total_stops += len(stops)
        
        for stop in stops:
            for v in stop.violations:
                constraint_counts[v.constraint] += 1
                severity_counts[v.severity] += 1
                affected_routes.setdefault(v.constraint, set()).add(route_id)
                if v.severity == "block":
                    blocked_routes.add(route_id)
    
    print(f"\n=== Coverage ===", flush=True)
    print(f"  Routes scanned:  {len(route_ids)}")
    print(f"  Stops scanned:   {total_stops}")
    
    print(f"\n=== Violations by constraint ===", flush=True)
    for constraint, count in sorted(constraint_counts.items(), key=lambda x: -x[1]):
        n_routes = len(affected_routes.get(constraint, set()))
        print(f"  {constraint}: {count} stops across {n_routes} routes")
    
    print(f"\n=== Violations by severity ===", flush=True)
    for severity, count in sorted(severity_counts.items(), key=lambda x: -x[1]):
        print(f"  {severity}: {count}")
    
    print(f"\n=== Routes with at least one BLOCKED stop ===", flush=True)
    print(f"  {len(blocked_routes)} routes / {len(route_ids)} total")
    print(f"  Examples: {sorted(list(blocked_routes))[:10]}")


if __name__ == "__main__":
    main()