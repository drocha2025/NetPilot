from app.incident_manager import (
    ACTIVE_INCIDENTS,
    process_health_snapshot,
)


def print_result(title, result):
    print()
    print("========================================")
    print(title)
    print("========================================")
    print()

    print(
        "Active incidents: "
        + str(len(result["active_incidents"]))
    )

    print(
        "Tracked incidents: "
        + str(len(result["all_incidents"]))
    )

    for incident in result["all_incidents"]:
        print(
            incident["router"]
            + " | "
            + incident["incident_type"]
            + " | "
            + incident["status"]
        )


healthy_snapshot = {
    "collected": "TEST-1",
    "routers": [
        {
            "router": "R1",
            "status": "ONLINE",
            "health": "HEALTHY",
            "issues": [],
            "state": {},
        }
    ],
}

failed_snapshot = {
    "collected": "TEST-2",
    "routers": [
        {
            "router": "R1",
            "status": "ONLINE",
            "health": "DEGRADED",
            "issues": [
                "Primary WAN interface is not operational.",
                "Primary WAN BGP session is not established.",
                "Traffic is using the backup WAN path.",
            ],
            "state": {},
        }
    ],
}

ACTIVE_INCIDENTS.clear()

result = process_health_snapshot(healthy_snapshot)
print_result("HEALTHY BASELINE", result)

result = process_health_snapshot(failed_snapshot)
print_result("FAILURE DETECTED", result)

result = process_health_snapshot(failed_snapshot)
print_result("FAILURE CONTINUES", result)

result = process_health_snapshot(healthy_snapshot)
print_result("FAILURE RESOLVED", result)