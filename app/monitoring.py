from datetime import datetime

from app.network_state import (
    ROUTERS,
    WAN_EDGES,
    collect_all_network_state,
)


def create_health_record(router, state):
    """
    Convert one router's network state into a normalized health record.
    """

    record = {
        "router": router,
        "status": state.get("status", "UNKNOWN"),
        "health": "UNKNOWN",
        "issues": [],
        "checked": datetime.now().isoformat(),
        "state": state,
    }

    if record["status"] == "OFFLINE":
        record["health"] = "CRITICAL"
        record["issues"].append("Device is offline.")
        return record

    if record["status"] != "ONLINE":
        record["health"] = "UNKNOWN"
        record["issues"].append("Device status is unknown.")
        return record

    if router not in WAN_EDGES:
        record["health"] = "HEALTHY"
        return record

    wan_state = state.get("wan_state", {})
    path_status = wan_state.get("path_status", {})

    active_path = path_status.get("active_path")
    primary_interface_up = path_status.get("primary_interface_up")
    backup_interface_up = path_status.get("backup_interface_up")
    primary_bgp_established = path_status.get("primary_bgp_established")
    backup_bgp_established = path_status.get("backup_bgp_established")

    default_route = wan_state.get("default_route", {})
    default_route_installed = (
        default_route.get("status") == "INSTALLED"
    )

    if not default_route_installed:
        record["issues"].append("No default route is installed.")

    if not primary_interface_up:
        record["issues"].append("Primary WAN interface is not operational.")

    if not primary_bgp_established:
        record["issues"].append("Primary WAN BGP session is not established.")

    if not backup_interface_up:
        record["issues"].append("Backup WAN interface is not operational.")

    if not backup_bgp_established:
        record["issues"].append("Backup WAN BGP session is not established.")

    if active_path == "PRIMARY":
        if primary_interface_up and primary_bgp_established:
            record["health"] = "HEALTHY"
        else:
            record["health"] = "DEGRADED"

    elif active_path == "BACKUP":
        if backup_interface_up and backup_bgp_established:
            record["health"] = "DEGRADED"
            record["issues"].append(
                "Traffic is using the backup WAN path."
            )
        else:
            record["health"] = "CRITICAL"

    else:
        record["health"] = "CRITICAL"
        record["issues"].append(
            "The active WAN path could not be determined."
        )

    return record


def collect_health_snapshot():
    """
    Collect and normalize the health of all routers.
    """

    network_states = collect_all_network_state()
    health_records = []

    for router in ROUTERS:
        state = network_states.get(
            router,
            {
                "router": router,
                "status": "UNKNOWN",
            },
        )

        health_records.append(
            create_health_record(router, state)
        )

    return {
        "collected": datetime.now().isoformat(),
        "routers": health_records,
    }


def display_health_snapshot(snapshot):
    """
    Display a concise health summary.
    """

    print()
    print("========================================")
    print("NETPILOT NETWORK HEALTH")
    print("========================================")
    print()

    print("Collected: " + snapshot["collected"])
    print()

    for record in snapshot["routers"]:
        print(
            record["router"]
            + " | "
            + record["status"]
            + " | "
            + record["health"]
        )

        for issue in record["issues"]:
            print("  - " + issue)

        print()


if __name__ == "__main__":
    snapshot = collect_health_snapshot()
    display_health_snapshot(snapshot)