from datetime import datetime
import json

from app.cisco_client import run_commands


WAN_EDGES = {
    "R1": {
        "primary": {
            "interface": "GigabitEthernet1",
            "peer": "10.0.14.2",
            "role": "PRIMARY_ISP",
        },
        "backup": {
            "interface": "GigabitEthernet3",
            "peer": "3.3.3.3",
            "role": "BACKUP_IBGP",
        },
    },
    "R3": {
        "primary": {
            "interface": "GigabitEthernet3",
            "peer": "10.0.35.2",
            "role": "PRIMARY_BACKUP_ISP",
        },
        "backup": {
            "interface": "GigabitEthernet2",
            "peer": "1.1.1.1",
            "role": "BACKUP_IBGP",
        },
    },
}


def parse_interface_status(interface_output, interface_name):
    """
    Find the operational status of a specific interface
    from show ip interface brief.

    Cisco may report interface state as:

        up up
        down down
        administratively down down

    The parser explicitly handles all three cases.
    """

    for raw_line in interface_output.splitlines():

        line = raw_line.strip()

        if not line.startswith(interface_name):
            continue

        fields = line.split()

        if len(fields) < 6:

            return {
                "interface": interface_name,
                "status": "UNKNOWN",
                "protocol": "UNKNOWN",
            }

        protocol = fields[-1]

        if (
            len(fields) >= 7
            and fields[-3] == "administratively"
            and fields[-2] == "down"
        ):

            status = "administratively down"

        else:

            status = fields[-2]

        return {
            "interface": interface_name,
            "status": status,
            "protocol": protocol,
        }

    return {
        "interface": interface_name,
        "status": "NOT_FOUND",
        "protocol": "NOT_FOUND",
    }


def parse_bgp_neighbor_status(bgp_summary, neighbor_ip):
    """
    Determine the BGP state for a specific neighbor.

    An established BGP session normally has a numeric
    prefix count in the final column.
    """

    for raw_line in bgp_summary.splitlines():

        line = raw_line.strip()

        if not line.startswith(neighbor_ip):
            continue

        fields = line.split()

        if len(fields) < 3:

            return {
                "neighbor": neighbor_ip,
                "state": "UNKNOWN",
                "prefixes_received": None,
            }

        last_field = fields[-1]

        if last_field.isdigit():

            return {
                "neighbor": neighbor_ip,
                "state": "ESTABLISHED",
                "prefixes_received": int(last_field),
            }

        return {
            "neighbor": neighbor_ip,
            "state": last_field,
            "prefixes_received": None,
        }

    return {
        "neighbor": neighbor_ip,
        "state": "NOT_FOUND",
        "prefixes_received": None,
    }


def parse_default_route(route_output):
    """
    Determine the currently installed default route.

    Supports static routes such as:

        * 10.0.14.2

    and dynamic routes such as:

        * 10.0.13.2, from 3.3.3.3, via GigabitEthernet3
    """

    for raw_line in route_output.splitlines():

        line = raw_line.strip()

        if not line.startswith("*"):
            continue

        if "via" in line:

            fields = line.split()

            next_hop = None
            interface = None

            if "via" in fields:

                via_index = fields.index("via")

                if via_index + 1 < len(fields):

                    interface = fields[
                        via_index + 1
                    ]

            route_text = line[1:].strip()

            if "," in route_text:

                route_text = route_text.split(
                    ",",
                    1,
                )[0].strip()

            if route_text:

                next_hop = route_text

            return {
                "status": "INSTALLED",
                "next_hop": next_hop,
                "interface": interface,
                "route_type": "DYNAMIC",
                "raw": line,
            }

        route_text = line[1:].strip()

        if route_text:

            if "," in route_text:

                route_text = route_text.split(
                    ",",
                    1,
                )[0].strip()

            if route_text:

                return {
                    "status": "INSTALLED",
                    "next_hop": route_text,
                    "interface": None,
                    "route_type": "STATIC_OR_DIRECT",
                    "raw": line,
                }

    return {
        "status": "NOT_INSTALLED",
        "next_hop": None,
        "interface": None,
        "route_type": None,
        "raw": "",
    }


def determine_path_status(router, evidence):
    """
    Determine whether the primary or backup WAN path
    is currently being used.
    """

    topology = WAN_EDGES[router]

    primary = topology["primary"]
    backup = topology["backup"]

    interfaces = evidence.get(
        "interfaces",
        {},
    )

    bgp = evidence.get(
        "bgp",
        {},
    )

    default_route = evidence.get(
        "default_route",
        {},
    )

    primary_interface = interfaces.get(
        primary["interface"],
        {},
    )

    backup_interface = interfaces.get(
        backup["interface"],
        {},
    )

    primary_bgp = bgp.get(
        primary["peer"],
        {},
    )

    backup_bgp = bgp.get(
        backup["peer"],
        {},
    )

    next_hop = default_route.get(
        "next_hop"
    )

    if next_hop == primary["peer"]:

        active_path = "PRIMARY"

    elif next_hop == backup["peer"]:

        active_path = "BACKUP"

    else:

        active_path = "UNKNOWN"

    return {
        "active_path": active_path,

        "primary_interface_up": (
            primary_interface.get("status") == "up"
            and primary_interface.get("protocol") == "up"
        ),

        "backup_interface_up": (
            backup_interface.get("status") == "up"
            and backup_interface.get("protocol") == "up"
        ),

        "primary_bgp_established": (
            primary_bgp.get("state")
            == "ESTABLISHED"
        ),

        "backup_bgp_established": (
            backup_bgp.get("state")
            == "ESTABLISHED"
        ),
    }


def build_structured_wan_state(router, raw_results):
    """
    Convert raw Cisco command output into structured
    network facts for NetPilot and Ollama.
    """

    topology = WAN_EDGES[router]

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

    primary = topology["primary"]
    backup = topology["backup"]

    interfaces = {
        primary["interface"]: parse_interface_status(
            interface_output,
            primary["interface"],
        ),

        backup["interface"]: parse_interface_status(
            interface_output,
            backup["interface"],
        ),
    }

    bgp = {
        primary["peer"]: parse_bgp_neighbor_status(
            bgp_output,
            primary["peer"],
        ),

        backup["peer"]: parse_bgp_neighbor_status(
            bgp_output,
            backup["peer"],
        ),
    }

    default_route = parse_default_route(
        route_output
    )

    structured = {
        "router": router,

        "primary_wan": {
            "interface": primary["interface"],
            "peer": primary["peer"],
            "role": primary["role"],
            "interface_state": interfaces[
                primary["interface"]
            ],
            "bgp_state": bgp[
                primary["peer"]
            ],
        },

        "backup_wan": {
            "interface": backup["interface"],
            "peer": backup["peer"],
            "role": backup["role"],
            "interface_state": interfaces[
                backup["interface"]
            ],
            "bgp_state": bgp[
                backup["peer"]
            ],
        },

        "default_route": default_route,
    }

    structured["path_status"] = determine_path_status(
        router,
        {
            "interfaces": interfaces,
            "bgp": bgp,
            "default_route": default_route,
        },
    )

    return structured


def analyze_bgp_neighbors(router, bgp_summary):
    """
    Compare expected BGP neighbors against live
    BGP summary output.
    """

    topology = WAN_EDGES[router]

    neighbors = []

    for path_name in [
        "primary",
        "backup",
    ]:

        neighbor = topology[path_name]["peer"]

        result = parse_bgp_neighbor_status(
            bgp_summary,
            neighbor,
        )

        result["role"] = path_name

        neighbors.append(
            result
        )

    return neighbors


def collect_wan_evidence(router):
    """
    Collect targeted WAN evidence from a WAN edge.

    Commands are executed through one SSH session.
    """

    if router not in WAN_EDGES:

        return {
            "router": router,
            "status": "UNSUPPORTED",
            "evidence": {},
        }

    print()
    print(
        "Collecting WAN evidence from "
        + router
    )

    commands = [
        "show ip interface brief",
        "show ip bgp summary",
        "show ip route 0.0.0.0",
    ]

    results = run_commands(
        router,
        commands,
    )

    if results is None:

        return {
            "router": router,
            "status": "OFFLINE",
            "evidence": {},
        }

    structured_state = build_structured_wan_state(
        router,
        results,
    )

    evidence = {
        "raw": {
            "interfaces": results.get(
                "show ip interface brief",
                "",
            ),

            "bgp_summary": results.get(
                "show ip bgp summary",
                "",
            ),

            "default_route": results.get(
                "show ip route 0.0.0.0",
                "",
            ),
        },

        "wan_state": structured_state,

        "bgp_health": {
            "router": router,
            "status": "ONLINE",
            "neighbors": analyze_bgp_neighbors(
                router,
                results.get(
                    "show ip bgp summary",
                    "",
                ),
            ),
        },
    }

    return {
        "router": router,
        "status": "COLLECTED",
        "collected": datetime.now().isoformat(),
        "evidence": evidence,
    }


def display_wan_evidence(router):
    """
    Display structured WAN evidence.
    """

    result = collect_wan_evidence(
        router
    )

    print()
    print("========================================")
    print("NETPILOT WAN EVIDENCE")
    print("========================================")
    print()

    print(
        "Router: "
        + result["router"]
    )

    print(
        "Status: "
        + result["status"]
    )

    print()

    evidence = result.get(
        "evidence",
        {},
    )

    print("STRUCTURED WAN STATE")
    print("----------------------------------------")

    print(
        json.dumps(
            evidence.get(
                "wan_state",
                {},
            ),
            indent=2,
        )
    )

    print()

    print("BGP HEALTH")
    print("----------------------------------------")

    print(
        json.dumps(
            evidence.get(
                "bgp_health",
                {},
            ),
            indent=2,
        )
    )

    print()

    print("RAW DEFAULT ROUTE")
    print("----------------------------------------")

    raw = evidence.get(
        "raw",
        {}
    )

    print(
        raw.get(
            "default_route",
            "",
        )
    )

    print()


if __name__ == "__main__":

    display_wan_evidence(
        "R1"
    )