from datetime import datetime

from app.cisco_client import run_commands
from app.wan_incident import (
    WAN_EDGES,
    parse_interface_status,
    parse_bgp_neighbor_status,
)

ROUTERS = ["R1", "R2", "R3", "R4", "R5"]

ROUTER_INTERFACES = {
    "R1": [
        "GigabitEthernet1",
        "GigabitEthernet2",
        "GigabitEthernet3",
        "GigabitEthernet4",
    ],
    "R2": [
        "GigabitEthernet1",
        "GigabitEthernet2",
        "GigabitEthernet3",
    ],
    "R3": [
        "GigabitEthernet1",
        "GigabitEthernet2",
        "GigabitEthernet3",
        "GigabitEthernet4",
    ],
    "R4": [
        "GigabitEthernet1",
        "GigabitEthernet2",
    ],
    "R5": [
        "GigabitEthernet1",
        "GigabitEthernet2",
    ],
}

WAN_FORWARDING = {
    "R1": {
        "primary": {
            "interface": "GigabitEthernet1",
            "next_hop": "10.0.14.2",
        },
        "backup": {
            "interface": "GigabitEthernet3",
            "next_hop": "10.0.13.2",
        },
    },
    "R3": {
        "primary": {
            "interface": "GigabitEthernet3",
            "next_hop": "10.0.35.2",
        },
        "backup": {
            "interface": "GigabitEthernet2",
            "next_hop": "10.0.13.1",
        },
    },
}


def get_collection_commands(router):
    """
    Return the Cisco commands required to build the
    normalized network state for a router.
    """

    commands = [
        "show ip interface brief",
        "show ip ospf neighbor",
        "show ip route",
    ]

    if router in WAN_EDGES:
        commands.extend(
            [
                "show ip bgp summary",
                "show ip route 0.0.0.0",
            ]
        )

    return commands


def parse_interface_summary(router, output):
    """
    Parse show ip interface brief into structured interface state.
    """

    interfaces = {}

    expected_interfaces = ROUTER_INTERFACES.get(
        router,
        [],
    )

    for interface_name in expected_interfaces:
        interfaces[interface_name] = {
            "interface": interface_name,
            "status": "NOT_FOUND",
            "protocol": "NOT_FOUND",
        }

    if not output:
        return interfaces

    for interface_name in expected_interfaces:
        interfaces[interface_name] = parse_interface_status(
            output,
            interface_name,
        )

    return interfaces


def parse_ospf_state(output):
    """
    Parse basic OSPF neighbor state.
    """

    if not output:
        return {
            "status": "UNKNOWN",
            "neighbor_count": 0,
            "neighbors": [],
        }

    neighbors = []

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("Neighbor ID"):
            continue

        if line.startswith("Total number"):
            continue

        fields = line.split()

        if len(fields) < 6:
            continue

        neighbor_id = fields[0]

        if neighbor_id.count(".") != 3:
            continue

        state = "UNKNOWN"

        if "FULL" in line:
            state = "FULL"
        elif "2WAY" in line:
            state = "2WAY"
        elif "EXSTART" in line:
            state = "EXSTART"
        elif "EXCHANGE" in line:
            state = "EXCHANGE"
        elif "LOADING" in line:
            state = "LOADING"
        elif "DOWN" in line:
            state = "DOWN"

        neighbors.append(
            {
                "neighbor": neighbor_id,
                "state": state,
            }
        )

    if not neighbors:
        return {
            "status": "NO_NEIGHBORS",
            "neighbor_count": 0,
            "neighbors": [],
        }

    return {
        "status": "HEALTHY",
        "neighbor_count": len(neighbors),
        "neighbors": neighbors,
    }


def parse_bgp_state(router, output):
    """
    Parse the expected BGP neighbors for a WAN router.

    A numeric State/PfxRcd value means the BGP session
    is established. Zero received prefixes is still
    an established session.
    """

    if router not in WAN_EDGES:
        return {
            "status": "NOT_APPLICABLE",
            "neighbors": [],
        }

    if not output:
        return {
            "status": "UNKNOWN",
            "neighbors": [],
        }

    topology = WAN_EDGES[router]

    neighbors = []

    for path_name in ["primary", "backup"]:
        neighbor_ip = topology[path_name]["peer"]

        parsed = parse_bgp_neighbor_status(
            output,
            neighbor_ip,
        )

        parsed["role"] = path_name

        neighbors.append(parsed)

    established_count = sum(
        1
        for neighbor in neighbors
        if neighbor.get("state") == "ESTABLISHED"
    )

    return {
        "status": (
            "HEALTHY"
            if established_count > 0
            else "DEGRADED"
        ),
        "neighbors": neighbors,
    }


def parse_default_route(output):
    """
    Parse the Cisco output from:

        show ip route 0.0.0.0

    Example:

        Routing entry for 0.0.0.0/0, supernet
          Known via "static", distance 1, metric 0,
          candidate default path
          Routing Descriptor Blocks:
          * 10.0.14.2
              Route metric is 0
    """

    if not output:
        return {
            "status": "NOT_INSTALLED",
            "next_hop": None,
            "interface": None,
            "route_type": None,
            "raw": "",
        }

    route_type = None

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if line.startswith('Known via "'):
            if '"static"' in line:
                route_type = "STATIC"
            elif '"ospf' in line.lower():
                route_type = "OSPF"
            elif '"bgp' in line.lower():
                route_type = "BGP"
            else:
                route_type = "DYNAMIC"

        if line.startswith("* "):
            next_hop = line[2:].strip()

            if "," in next_hop:
                next_hop = next_hop.split(",", 1)[0].strip()

            if next_hop:
                return {
                    "status": "INSTALLED",
                    "next_hop": next_hop,
                    "interface": None,
                    "route_type": route_type or "UNKNOWN",
                    "raw": line,
                }

    return {
        "status": "NOT_INSTALLED",
        "next_hop": None,
        "interface": None,
        "route_type": route_type,
        "raw": "",
    }


def determine_wan_path(router, default_route):
    """
    Determine the active forwarding path.

    IMPORTANT:
    BGP peer addresses and forwarding next-hop addresses
    are not necessarily the same address.

    Example R1:

        Primary BGP peer:
            10.0.14.2

        Backup BGP peer:
            3.3.3.3

        Backup forwarding next hop:
            10.0.13.2
    """

    if router not in WAN_FORWARDING:
        return {
            "active_path": "NOT_APPLICABLE",
            "reason": "Router is not a WAN edge.",
        }

    next_hop = default_route.get("next_hop")

    primary = WAN_FORWARDING[router]["primary"]
    backup = WAN_FORWARDING[router]["backup"]

    if next_hop == primary["next_hop"]:
        return {
            "active_path": "PRIMARY",
            "next_hop": next_hop,
            "interface": primary["interface"],
            "reason": "Default route uses the primary WAN forwarding next hop.",
        }

    if next_hop == backup["next_hop"]:
        return {
            "active_path": "BACKUP",
            "next_hop": next_hop,
            "interface": backup["interface"],
            "reason": "Default route uses the backup WAN forwarding next hop.",
        }

    return {
        "active_path": "UNKNOWN",
        "next_hop": next_hop,
        "interface": None,
        "reason": "Default route next hop does not match the known WAN forwarding paths.",
    }


def build_wan_state(router, raw_results):
    """
    Build normalized WAN state for a WAN edge.
    """

    if router not in WAN_EDGES:
        return {
            "status": "NOT_APPLICABLE",
        }

    interface_output = raw_results.get(
        "show ip interface brief",
        "",
    )

    bgp_output = raw_results.get(
        "show ip bgp summary",
        "",
    )

    route_output = raw_results.get(
        "show ip route 0.0.0.0",
        "",
    )

    interfaces = parse_interface_summary(
        router,
        interface_output,
    )

    topology = WAN_EDGES[router]

    primary = topology["primary"]
    backup = topology["backup"]

    primary_interface = interfaces.get(
        primary["interface"],
        {},
    )

    backup_interface = interfaces.get(
        backup["interface"],
        {},
    )

    primary_bgp = parse_bgp_neighbor_status(
        bgp_output,
        primary["peer"],
    )

    backup_bgp = parse_bgp_neighbor_status(
        bgp_output,
        backup["peer"],
    )

    default_route = parse_default_route(
        route_output,
    )

    path = determine_wan_path(
        router,
        default_route,
    )

    primary_interface_up = (
        primary_interface.get("status") == "up"
        and primary_interface.get("protocol") == "up"
    )

    backup_interface_up = (
        backup_interface.get("status") == "up"
        and backup_interface.get("protocol") == "up"
    )

    primary_bgp_established = (
        primary_bgp.get("state") == "ESTABLISHED"
    )

    backup_bgp_established = (
        backup_bgp.get("state") == "ESTABLISHED"
    )

    if path["active_path"] == "PRIMARY":
        if primary_interface_up and primary_bgp_established:
            wan_status = "HEALTHY"
        else:
            wan_status = "DEGRADED"

    elif path["active_path"] == "BACKUP":
        if backup_interface_up and backup_bgp_established:
            wan_status = "DEGRADED"
        else:
            wan_status = "CRITICAL"

    else:
        wan_status = "CRITICAL"

    return {
        "status": wan_status,
        "primary": {
            "interface": primary_interface,
            "bgp": primary_bgp,
            "forwarding": WAN_FORWARDING[router]["primary"],
        },
        "backup": {
            "interface": backup_interface,
            "bgp": backup_bgp,
            "forwarding": WAN_FORWARDING[router]["backup"],
        },
        "default_route": default_route,
        "path_status": {
            "active_path": path["active_path"],
            "next_hop": path.get("next_hop"),
            "interface": path.get("interface"),
            "reason": path["reason"],
            "primary_interface_up": primary_interface_up,
            "backup_interface_up": backup_interface_up,
            "primary_bgp_established": primary_bgp_established,
            "backup_bgp_established": backup_bgp_established,
        },
    }


def build_network_state(router, raw_results):
    """
    Convert raw Cisco command results into one normalized
    network-state record.
    """

    if raw_results is None:
        return {
            "router": router,
            "status": "OFFLINE",
            "collected": datetime.now().isoformat(),
            "interfaces": {},
            "ospf": {
                "status": "UNKNOWN",
                "neighbor_count": 0,
                "neighbors": [],
            },
            "routes": "",
            "wan_state": {},
        }

    state = {
        "router": router,
        "status": "ONLINE",
        "collected": datetime.now().isoformat(),
        "interfaces": parse_interface_summary(
            router,
            raw_results.get(
                "show ip interface brief",
                "",
            ),
        ),
        "ospf": parse_ospf_state(
            raw_results.get(
                "show ip ospf neighbor",
                "",
            ),
        ),
        "routes": raw_results.get(
            "show ip route",
            "",
        ),
        "wan_state": {},
    }

    if router in WAN_EDGES:
        state["wan_state"] = build_wan_state(
            router,
            raw_results,
        )

    return state


def collect_network_state(router):
    """
    Collect one router's network state using one SSH session.
    """

    print()
    print("Collecting network state from " + router)

    commands = get_collection_commands(router)

    results = run_commands(
        router,
        commands,
    )

    return build_network_state(
        router,
        results,
    )


def collect_all_network_state():
    """
    Collect network state from all routers.
    """

    network_states = {}

    for router in ROUTERS:
        network_states[router] = collect_network_state(
            router
        )

    return network_states


def display_network_state(router):
    """
    Display detailed normalized state for one router.
    """

    state = collect_network_state(router)

    print()
    print("========================================")
    print("NETPILOT NETWORK STATE")
    print("========================================")
    print()

    print("Router: " + state["router"])
    print("Status: " + state["status"])
    print("Collected: " + state["collected"])
    print()

    print("INTERFACES")
    print("----------------------------------------")

    for interface_name, interface in state[
        "interfaces"
    ].items():
        print(
            interface_name
            + " | "
            + interface.get("status", "UNKNOWN")
            + " | "
            + interface.get("protocol", "UNKNOWN")
        )

    print()

    print("OSPF")
    print("----------------------------------------")

    ospf = state["ospf"]

    print(
        "Status: "
        + ospf.get("status", "UNKNOWN")
    )

    print(
        "Neighbors: "
        + str(
            ospf.get(
                "neighbor_count",
                0,
            )
        )
    )

    for neighbor in ospf.get("neighbors", []):
        print(
            neighbor["neighbor"]
            + " | "
            + neighbor["state"]
        )

    if state["wan_state"]:
        wan = state["wan_state"]

        print()
        print("WAN")
        print("----------------------------------------")

        print(
            "WAN Health: "
            + wan.get(
                "status",
                "UNKNOWN",
            )
        )

        path = wan.get(
            "path_status",
            {},
        )

        print(
            "Active Path: "
            + path.get(
                "active_path",
                "UNKNOWN",
            )
        )

        print(
            "Forwarding Interface: "
            + str(
                path.get(
                    "interface",
                    "UNKNOWN",
                )
            )
        )

        print(
            "Forwarding Next Hop: "
            + str(
                path.get(
                    "next_hop",
                    "UNKNOWN",
                )
            )
        )

        print()

        primary = wan.get(
            "primary",
            {},
        )

        print("Primary WAN:")

        primary_interface = primary.get(
            "interface",
            {},
        )

        primary_bgp = primary.get(
            "bgp",
            {}
        )

        print(
            "  Interface: "
            + primary_interface.get(
                "interface",
                "UNKNOWN",
            )
        )

        print(
            "  State: "
            + primary_interface.get(
                "status",
                "UNKNOWN",
            )
            + "/"
            + primary_interface.get(
                "protocol",
                "UNKNOWN",
            )
        )

        print(
            "  BGP: "
            + primary_bgp.get(
                "state",
                "UNKNOWN",
            )
        )

        print(
            "  Forwarding Next Hop: "
            + WAN_FORWARDING[router]["primary"]["next_hop"]
        )

        print()

        backup = wan.get(
            "backup",
            {},
        )

        print("Backup WAN:")

        backup_interface = backup.get(
            "interface",
            {},
        )

        backup_bgp = backup.get(
            "bgp",
            {}
        )

        print(
            "  Interface: "
            + backup_interface.get(
                "interface",
                "UNKNOWN",
            )
        )

        print(
            "  State: "
            + backup_interface.get(
                "status",
                "UNKNOWN",
            )
            + "/"
            + backup_interface.get(
                "protocol",
                "UNKNOWN",
            )
        )

        print(
            "  BGP: "
            + backup_bgp.get(
                "state",
                "UNKNOWN",
            )
        )

        print(
            "  Forwarding Next Hop: "
            + WAN_FORWARDING[router]["backup"]["next_hop"]
        )

        print()

        default_route = wan.get(
            "default_route",
            {},
        )

        print("Default Route:")

        print(
            "  Status: "
            + default_route.get(
                "status",
                "UNKNOWN",
            )
        )

        print(
            "  Next Hop: "
            + str(
                default_route.get(
                    "next_hop",
                    "UNKNOWN",
                )
            )
        )

        print(
            "  Route Type: "
            + str(
                default_route.get(
                    "route_type",
                    "UNKNOWN",
                )
            )
        )

    print()


def display_all_network_state():
    """
    Display a concise unified state for all routers.
    """

    states = collect_all_network_state()

    print()
    print("========================================")
    print("NETPILOT UNIFIED NETWORK STATE")
    print("========================================")
    print()

    for router in ROUTERS:
        state = states[router]

        print(
            router
            + " | "
            + state.get(
                "status",
                "UNKNOWN",
            )
        )

        ospf = state.get(
            "ospf",
            {},
        )

        print(
            "  OSPF: "
            + ospf.get(
                "status",
                "UNKNOWN",
            )
            + " | Neighbors: "
            + str(
                ospf.get(
                    "neighbor_count",
                    0,
                )
            )
        )

        if router in WAN_EDGES:
            wan = state.get(
                "wan_state",
                {},
            )

            path = wan.get(
                "path_status",
                {},
            )

            default_route = wan.get(
                "default_route",
                {},
            )

            print(
                "  WAN: "
                + wan.get(
                    "status",
                    "UNKNOWN",
                )
            )

            print(
                "  Active Path: "
                + path.get(
                    "active_path",
                    "UNKNOWN",
                )
            )

            print(
                "  Forwarding Next Hop: "
                + str(
                    path.get(
                        "next_hop",
                        "UNKNOWN",
                    )
                )
            )

            print(
                "  Default Route: "
                + default_route.get(
                    "status",
                    "UNKNOWN",
                )
                + " | Next Hop: "
                + str(
                    default_route.get(
                        "next_hop",
                        "UNKNOWN",
                    )
                )
            )

        print()


if __name__ == "__main__":
    display_all_network_state()