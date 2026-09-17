from datetime import datetime
import time

from app.cisco_client import run_commands, run_config
from app.wan_incident import (
    WAN_EDGES,
    parse_interface_status,
    parse_bgp_neighbor_status,
    parse_default_route,
)


VALIDATION_ATTEMPTS = 6
VALIDATION_WAIT_SECONDS = 5


def collect_remediation_state(router):
    """
    Collect the minimum Cisco evidence required
    before WAN remediation.

    The remediation decision is based on verified
    Cisco state rather than LLM-generated commands.
    """

    if router not in WAN_EDGES:

        return {
            "router": router,
            "status": "UNSUPPORTED",
            "state": {},
        }

    topology = WAN_EDGES[router]

    primary = topology["primary"]
    backup = topology["backup"]

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
            "state": {},
        }

    interface_output = results.get(
        "show ip interface brief",
        "",
    )

    bgp_output = results.get(
        "show ip bgp summary",
        "",
    )

    route_output = results.get(
        "show ip route 0.0.0.0",
        "",
    )

    primary_interface = parse_interface_status(
        interface_output,
        primary["interface"],
    )

    backup_interface = parse_interface_status(
        interface_output,
        backup["interface"],
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

    return {
        "router": router,
        "status": "COLLECTED",
        "state": {
            "primary": {
                "interface": primary["interface"],
                "peer": primary["peer"],
                "interface_state": primary_interface,
                "bgp_state": primary_bgp,
            },

            "backup": {
                "interface": backup["interface"],
                "peer": backup["peer"],
                "interface_state": backup_interface,
                "bgp_state": backup_bgp,
            },

            "default_route": default_route,
        },
    }


def validate_remediation_safety(router, state):
    """
    Perform deterministic safety checks.

    NetPilot will only recommend the specific
    primary-interface remediation when the live
    Cisco state supports it.
    """

    if router not in WAN_EDGES:

        return {
            "approved": False,
            "reason": "Unsupported WAN router.",
        }

    topology = WAN_EDGES[router]

    primary = topology["primary"]

    primary_state = state.get(
        "primary",
        {},
    )

    interface_state = primary_state.get(
        "interface_state",
        {},
    )

    bgp_state = primary_state.get(
        "bgp_state",
        {},
    )

    expected_interface = primary["interface"]

    expected_peer = primary["peer"]

    actual_interface = interface_state.get(
        "interface"
    )

    actual_status = interface_state.get(
        "status"
    )

    actual_protocol = interface_state.get(
        "protocol"
    )

    actual_peer = bgp_state.get(
        "neighbor"
    )

    if actual_interface != expected_interface:

        return {
            "approved": False,
            "reason": (
                "Primary interface verification failed. "
                "Expected "
                + expected_interface
                + " but found "
                + str(actual_interface)
                + "."
            ),
        }

    if actual_peer != expected_peer:

        return {
            "approved": False,
            "reason": (
                "Primary BGP peer verification failed. "
                "Expected "
                + expected_peer
                + " but found "
                + str(actual_peer)
                + "."
            ),
        }

    if actual_status != "administratively down":

        if actual_status == "down":

            return {
                "approved": False,
                "reason": (
                    "Primary interface is operationally down "
                    "but not administratively down. "
                    "Do not automatically remove the shutdown state."
                ),
            }

        return {
            "approved": False,
            "reason": (
                "Primary interface is not administratively down. "
                "Current state: "
                + str(actual_status)
                + "/"
                + str(actual_protocol)
                + "."
            ),
        }

    return {
        "approved": True,
        "reason": (
            "Verified primary WAN interface "
            + expected_interface
            + " is administratively down and is associated "
            "with expected primary peer "
            + expected_peer
            + "."
        ),
    }


def build_remediation_plan(router, safety_result):
    """
    Build the Cisco remediation command from
    verified topology data.

    Ollama does not supply the command.
    """

    if not safety_result.get("approved"):

        return {
            "status": "BLOCKED",
            "commands": [],
            "reason": safety_result.get(
                "reason",
                "Safety validation failed.",
            ),
        }

    topology = WAN_EDGES[router]

    interface_name = topology["primary"]["interface"]

    commands = [
        "interface " + interface_name,
        "no shutdown",
    ]

    return {
        "status": "READY",
        "router": router,
        "interface": interface_name,
        "action": "RESTORE_PRIMARY_WAN",
        "commands": commands,
        "reason": safety_result.get(
            "reason",
            "",
        ),
    }


def request_engineer_approval(plan):
    """
    Require explicit human approval before
    making a network configuration change.
    """

    if plan.get("status") != "READY":

        return False

    print()
    print("========================================")
    print("NETPILOT ENGINEER APPROVAL")
    print("========================================")
    print()

    print(
        "Router: "
        + plan["router"]
    )

    print(
        "Interface: "
        + plan["interface"]
    )

    print(
        "Action: "
        + plan["action"]
    )

    print()

    print("Cisco commands to be applied:")

    for command in plan["commands"]:

        print(
            "  "
            + command
        )

    print()

    print(
        "Safety assessment: "
        + plan["reason"]
    )

    print()

    approval = input(
        "Approve this change? Type YES to continue: "
    )

    if approval.strip().upper() == "YES":

        print()
        print(
            "Engineer approval received."
        )

        return True

    print()
    print(
        "Engineer approval not received."
    )

    return False


def apply_remediation(router, plan):
    """
    Apply the approved Cisco configuration.
    """

    if plan.get("status") != "READY":

        return {
            "status": "BLOCKED",
            "output": "",
        }

    commands = plan.get(
        "commands",
        [],
    )

    if not commands:

        return {
            "status": "BLOCKED",
            "output": "",
        }

    print()
    print("========================================")
    print("NETPILOT WAN REMEDIATION")
    print("========================================")
    print()

    print(
        "Applying approved remediation to "
        + router
        + "..."
    )

    output = run_config(
        router,
        commands,
    )

    if output is None:

        return {
            "status": "FAILED",
            "output": "",
        }

    print()
    print("Configuration applied.")

    return {
        "status": "APPLIED",
        "output": output,
    }


def evaluate_validation_state(router, state):
    """
    Evaluate whether the WAN has converged after
    the approved remediation.

    All required conditions must be healthy:

        1. Primary interface is up/up.
        2. Primary BGP neighbor is established.
        3. Default route uses the primary peer.
    """

    topology = WAN_EDGES[router]

    primary = topology["primary"]

    primary_interface = state[
        "primary"
    ]["interface_state"]

    primary_bgp = state[
        "primary"
    ]["bgp_state"]

    default_route = state[
        "default_route"
    ]

    interface_healthy = (
        primary_interface.get("status") == "up"
        and primary_interface.get("protocol") == "up"
    )

    bgp_healthy = (
        primary_bgp.get("state")
        == "ESTABLISHED"
    )

    default_route_uses_primary = (
        default_route.get("next_hop")
        == primary["peer"]
    )

    checks = {
        "interface_up": interface_healthy,
        "bgp_established": bgp_healthy,
        "primary_default_route": (
            default_route_uses_primary
        ),
    }

    return checks


def validate_remediation(router):
    """
    Perform bounded post-change convergence validation.

    NetPilot allows the network control plane time
    to converge before declaring the remediation
    successful or failed.

    No configuration changes are made during
    validation.
    """

    print()
    print("========================================")
    print("NETPILOT POST-CHANGE VALIDATION")
    print("========================================")
    print()

    total_wait = (
        (VALIDATION_ATTEMPTS - 1)
        * VALIDATION_WAIT_SECONDS
    )

    print(
        "Validation policy: "
        + str(VALIDATION_ATTEMPTS)
        + " attempts, "
        + str(VALIDATION_WAIT_SECONDS)
        + " seconds between attempts."
    )

    print(
        "Maximum convergence window: "
        + str(total_wait)
        + " seconds."
    )

    print()

    attempts = []

    for attempt in range(
        1,
        VALIDATION_ATTEMPTS + 1,
    ):

        print(
            "Validation attempt "
            + str(attempt)
            + " of "
            + str(VALIDATION_ATTEMPTS)
        )

        result = collect_remediation_state(
            router
        )

        if result["status"] != "COLLECTED":

            attempt_result = {
                "attempt": attempt,
                "status": "COLLECTION_FAILED",
                "checks": {},
                "state": {},
                "reason": (
                    "Unable to collect Cisco state."
                ),
            }

            attempts.append(
                attempt_result
            )

        else:

            state = result["state"]

            checks = evaluate_validation_state(
                router,
                state,
            )

            all_checks_passed = all(
                checks.values()
            )

            if all_checks_passed:

                attempt_result = {
                    "attempt": attempt,
                    "status": "SUCCESS",
                    "checks": checks,
                    "state": state,
                    "reason": (
                        "All post-change validation "
                        "checks passed."
                    ),
                }

                attempts.append(
                    attempt_result
                )

                print()
                print(
                    "Validation successful on attempt "
                    + str(attempt)
                    + "."
                )

                return {
                    "status": "SUCCESS",
                    "reason": (
                        "Primary WAN interface, BGP session, "
                        "and default route converged successfully."
                    ),
                    "checks": checks,
                    "attempts": attempts,
                    "state": state,
                }

            attempt_result = {
                "attempt": attempt,
                "status": "NOT_CONVERGED",
                "checks": checks,
                "state": state,
                "reason": (
                    "WAN state has not fully converged."
                ),
            }

            attempts.append(
                attempt_result
            )

            print()

            print("Validation checks:")

            for name, value in checks.items():

                print(
                    "  "
                    + name
                    + ": "
                    + str(value)
                )

        if attempt < VALIDATION_ATTEMPTS:

            print()

            print(
                "Network has not fully converged."
            )

            print(
                "Waiting "
                + str(VALIDATION_WAIT_SECONDS)
                + " seconds before next validation attempt..."
            )

            time.sleep(
                VALIDATION_WAIT_SECONDS
            )

            print()

    final_attempt = attempts[-1]

    return {
        "status": "FAILED",
        "reason": (
            "WAN did not fully converge within the "
            "configured validation window of "
            + str(total_wait)
            + " seconds."
        ),
        "checks": final_attempt.get(
            "checks",
            {},
        ),
        "attempts": attempts,
        "state": final_attempt.get(
            "state",
            {},
        ),
    }


def display_validation_history(attempts):
    """
    Display the complete post-change validation
    history for operational visibility.
    """

    print()
    print("========================================")
    print("NETPILOT VALIDATION HISTORY")
    print("========================================")
    print()

    for attempt in attempts:

        print(
            "Attempt "
            + str(attempt["attempt"])
            + ": "
            + attempt["status"]
        )

        checks = attempt.get(
            "checks",
            {},
        )

        for name, value in checks.items():

            print(
                "  "
                + name
                + ": "
                + str(value)
            )

        print()


def remediate_primary_wan(router):
    """
    Complete controlled WAN remediation workflow.

    Discovery
        ↓
    Safety validation
        ↓
    Remediation plan
        ↓
    Engineer approval
        ↓
    Configuration
        ↓
    Bounded convergence validation
        ↓
    Resolution / Validation Failure
    """

    incident_id = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    print()
    print("========================================")
    print("NETPILOT CONTROLLED WAN REMEDIATION")
    print("========================================")
    print()

    print(
        "Incident ID: "
        + incident_id
    )

    print(
        "Router: "
        + router
    )

    print()

    print("Collecting pre-change state...")

    evidence = collect_remediation_state(
        router
    )

    if evidence["status"] != "COLLECTED":

        print()
        print(
            "REMEDIATION BLOCKED: "
            + evidence["status"]
        )

        return {
            "incident_id": incident_id,
            "status": "BLOCKED",
            "reason": (
                "Unable to collect pre-change state."
            ),
        }

    state = evidence["state"]

    print()
    print("Primary interface:")
    print(
        state["primary"]["interface_state"]
    )

    print()
    print("Primary BGP:")
    print(
        state["primary"]["bgp_state"]
    )

    print()
    print("Default route:")
    print(
        state["default_route"]
    )

    safety_result = validate_remediation_safety(
        router,
        state,
    )

    print()
    print("Safety validation:")
    print(
        safety_result["reason"]
    )

    if not safety_result["approved"]:

        print()
        print(
            "REMEDIATION BLOCKED."
        )

        return {
            "incident_id": incident_id,
            "status": "BLOCKED",
            "reason": safety_result["reason"],
        }

    plan = build_remediation_plan(
        router,
        safety_result,
    )

    if plan["status"] != "READY":

        print()
        print(
            "REMEDIATION BLOCKED."
        )

        return {
            "incident_id": incident_id,
            "status": "BLOCKED",
            "reason": plan.get(
                "reason",
                "",
            ),
        }

    approved = request_engineer_approval(
        plan
    )

    if not approved:

        print()
        print(
            "REMEDIATION CANCELLED."
        )

        return {
            "incident_id": incident_id,
            "status": "CANCELLED",
            "reason": (
                "Engineer did not approve the change."
            ),
        }

    remediation_result = apply_remediation(
        router,
        plan,
    )

    if remediation_result["status"] != "APPLIED":

        print()
        print(
            "REMEDIATION FAILED."
        )

        return {
            "incident_id": incident_id,
            "status": "FAILED",
            "reason": (
                "Cisco configuration could not be applied."
            ),
        }

    validation = validate_remediation(
        router
    )

    display_validation_history(
        validation.get(
            "attempts",
            [],
        )
    )

    print()

    if validation["status"] == "SUCCESS":

        print(
            "========================================"
        )

        print(
            "WAN REMEDIATION SUCCESSFUL"
        )

        print(
            "========================================"
        )

        print()

        print(
            "Incident ID: "
            + incident_id
        )

        print(
            "Status: RESOLVED"
        )

        print(
            "Reason: "
            + validation["reason"]
        )

        print()

        return {
            "incident_id": incident_id,
            "status": "RESOLVED",
            "validation": validation,
        }

    print(
        "========================================"
    )

    print(
        "WAN REMEDIATION VALIDATION FAILED"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Incident ID: "
        + incident_id
    )

    print(
        "Status: VALIDATION_FAILED"
    )

    print(
        "Reason: "
        + validation["reason"]
    )

    print()

    return {
        "incident_id": incident_id,
        "status": "VALIDATION_FAILED",
        "validation": validation,
    }


if __name__ == "__main__":

    result = remediate_primary_wan(
        "R1"
    )

    print()
    print("FINAL RESULT")
    print("----------------------------------------")
    print(result)
