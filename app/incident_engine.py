from datetime import datetime

from app.cisco_client import run_command
from app.drift_detector import get_drift_status
from app.bgp_health import get_bgp_summary


def create_incident(router, incident_type, description):
    return {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "router": router,
        "incident_type": incident_type,
        "description": description,
        "created": datetime.now().isoformat(),
        "status": "CREATED",
        "evidence": {},
    }


def test_router_connectivity(router):
    output = run_command(router, "show clock")

    if output is None:
        return False

    return True


def collect_router_evidence(router):
    commands = {
        "interfaces": "show ip interface brief",
        "ospf_neighbors": "show ip ospf neighbor",
        "ospf_interfaces": "show ip ospf interface brief",
        "routes": "show ip route",
        "running_config": "show running-config",
        "interfaces_detail": "show interfaces",
    }

    evidence = {}

    for name, command in commands.items():
        output = run_command(router, command)

        if output is None:
            evidence[name] = "UNAVAILABLE"
        else:
            evidence[name] = output

    return evidence


def collect_drift_evidence(router):
    try:
        return get_drift_status(router)
    except Exception as error:
        return {
            "status": "UNKNOWN",
            "reason": str(error),
        }


def collect_bgp_evidence(router):
    try:
        return get_bgp_summary(router)
    except Exception as error:
        return {
            "router": router,
            "status": "UNKNOWN",
            "output": "",
            "neighbors": [],
            "reason": str(error),
        }


def collect_incident_evidence(router, incident_type):
    connectivity = test_router_connectivity(router)

    evidence = {
        "connectivity": connectivity
    }

    if not connectivity:
        evidence["router_evidence"] = {
            "status": "UNAVAILABLE",
            "reason": "Router is unreachable through the NetPilot management connection."
        }

        evidence["drift_evidence"] = {
            "status": "UNKNOWN",
            "reason": "Drift could not be evaluated because the router is offline."
        }

        evidence["bgp_evidence"] = {
            "status": "UNAVAILABLE",
            "reason": "BGP evidence could not be collected because the router is offline."
        }

        return evidence

    evidence["router_evidence"] = collect_router_evidence(router)
    evidence["drift_evidence"] = collect_drift_evidence(router)

    if incident_type in [
        "BGP_FAILURE",
        "WAN_FAILURE",
        "ROUTING_FAILURE",
    ]:
        evidence["bgp_evidence"] = collect_bgp_evidence(router)

    return evidence


def summarize_evidence(evidence):
    summary = {
        "connectivity": evidence.get("connectivity"),
        "drift_status": evidence.get(
            "drift_evidence", {}
        ).get("status", "UNKNOWN"),
        "bgp_status": evidence.get(
            "bgp_evidence", {}
        ).get("status", "NOT_COLLECTED"),
    }

    return summary


def investigate_incident(router, incident_type, description):
    incident = create_incident(
        router=router,
        incident_type=incident_type,
        description=description,
    )

    incident["status"] = "INVESTIGATING"

    evidence = collect_incident_evidence(
        router=router,
        incident_type=incident_type,
    )

    incident["evidence"] = evidence
    incident["evidence_summary"] = summarize_evidence(evidence)

    if evidence.get("connectivity") is False:
        incident["status"] = "INVESTIGATED"
    else:
        incident["status"] = "INVESTIGATED"

    return incident


if __name__ == "__main__":
    incident = investigate_incident(
        router="R1",
        incident_type="BGP_FAILURE",
        description="Customer reports a possible WAN routing problem.",
    )

    print()
    print("========================================")
    print("NETPILOT INCIDENT INVESTIGATION")
    print("========================================")
    print()
    print("Incident ID: " + incident["id"])
    print("Router: " + incident["router"])
    print("Type: " + incident["incident_type"])
    print("Status: " + incident["status"])
    print()

    print("Evidence Summary:")
    print(incident["evidence_summary"])

    print()
    print("BGP Evidence:")
    print(incident["evidence"].get("bgp_evidence", {}))