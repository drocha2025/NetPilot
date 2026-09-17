from app.cisco_client import run_command


BGP_DEVICES = {
    "R1": {
        "neighbors": ["10.0.14.2", "3.3.3.3"]
    },
    "R3": {
        "neighbors": ["10.0.35.2", "1.1.1.1"]
    },
}


def get_bgp_summary(router):
    if router not in BGP_DEVICES:
        return {
            "router": router,
            "status": "UNSUPPORTED",
            "output": "",
            "neighbors": [],
        }

    output = run_command(router, "show ip bgp summary")

    if output is None:
        return {
            "router": router,
            "status": "OFFLINE",
            "output": "",
            "neighbors": [],
        }

    neighbors = []

    for neighbor in BGP_DEVICES[router]["neighbors"]:
        if neighbor in output:
            neighbors.append({
                "neighbor": neighbor,
                "status": "PRESENT",
            })
        else:
            neighbors.append({
                "neighbor": neighbor,
                "status": "NOT_FOUND",
            })

    return {
        "router": router,
        "status": "ONLINE",
        "output": output,
        "neighbors": neighbors,
    }


def display_bgp_health(router):
    result = get_bgp_summary(router)

    print()
    print("========================================")
    print("NETPILOT BGP HEALTH")
    print("========================================")
    print()
    print("Router: " + result["router"])
    print("Status: " + result["status"])
    print()

    for neighbor in result["neighbors"]:
        print(
            "Neighbor: "
            + neighbor["neighbor"]
            + " | "
            + neighbor["status"]
        )

    print()


if __name__ == "__main__":
    display_bgp_health("R1")
    display_bgp_health("R3")