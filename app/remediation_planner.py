from datetime import datetime, timezone


def current_timestamp():
    return datetime.now(
        timezone.utc
    ).isoformat()


def build_remediation_plan(incident):
    """
    Build a deterministic Cisco remediation plan from
    verified NetPilot configuration-drift information.

    AI recommendations are advisory only.

    NetPilot obtains the affected interface and expected
    configuration from verified drift evidence and the
    golden configuration.

    This planner is intentionally limited to interface
    description remediation.
    """

    drift = (
        incident
        .get("evidence", {})
        .get("drift_evidence", {})
    )

    if not isinstance(
        drift,
        dict
    ):
        drift = {}

    status = drift.get(
        "status",
        "UNKNOWN"
    )

    interface = drift.get(
        "interface",
        ""
    )

    expected = drift.get(
        "expected",
        ""
    )

    current = drift.get(
        "current",
        ""
    )

    timestamp = current_timestamp()

    if status != "DRIFT":

        return {
            "status":
                "NO_REMEDIATION",

            "reason":
                "No active configuration drift was detected.",

            "interface":
                interface,

            "current":
                current,

            "expected":
                expected,

            "commands":
                [],

            "created":
                timestamp,
        }

    if not interface:

        return {
            "status":
                "BLOCKED",

            "reason": (
                "Drift was detected but NetPilot could "
                "not identify the affected interface."
            ),

            "interface":
                "",

            "current":
                current,

            "expected":
                expected,

            "commands":
                [],

            "created":
                timestamp,
        }

    if not expected:

        return {
            "status":
                "BLOCKED",

            "reason": (
                "Drift was detected but NetPilot could "
                "not determine the expected configuration."
            ),

            "interface":
                interface,

            "current":
                current,

            "expected":
                "",

            "commands":
                [],

            "created":
                timestamp,
        }

    if not current:

        return {
            "status":
                "BLOCKED",

            "reason": (
                "Drift was detected but NetPilot could "
                "not determine the verified current "
                "configuration."
            ),

            "interface":
                interface,

            "current":
                "",

            "expected":
                expected,

            "commands":
                [],

            "created":
                timestamp,
        }

    if not expected.startswith(
        "description "
    ):

        return {
            "status":
                "BLOCKED",

            "reason": (
                "The detected drift is outside the "
                "currently approved description-remediation "
                "policy."
            ),

            "interface":
                interface,

            "current":
                current,

            "expected":
                expected,

            "commands":
                [],

            "created":
                timestamp,
        }

    commands = [
        "interface " + interface,
        expected,
    ]

    return {
        "status":
            "READY_FOR_APPROVAL",

        "reason": (
            "NetPilot identified a verified interface "
            "description drift and generated a deterministic "
            "remediation plan from the golden configuration."
        ),

        "interface":
            interface,

        "current":
            current,

        "expected":
            expected,

        "commands":
            commands,

        "created":
            timestamp,
    }


def display_remediation_plan(
    incident
):
    """
    Display the deterministic remediation plan
    for engineer review.
    """

    plan = incident.get(
        "remediation_plan",
        {}
    )

    print()
    print("========================================")
    print("NETPILOT REMEDIATION PLAN")
    print("========================================")

    print()

    print(
        "Incident ID: "
        + str(
            incident.get(
                "incident_id",
                "UNKNOWN"
            )
        )
    )

    print(
        "Router: "
        + incident.get(
            "router",
            "UNKNOWN"
        )
    )

    print(
        "Incident Type: "
        + incident.get(
            "incident_type",
            "UNKNOWN"
        )
    )

    print()

    print(
        "Status: "
        + plan.get(
            "status",
            "UNKNOWN"
        )
    )

    print()

    print(
        "Interface: "
        + plan.get(
            "interface",
            ""
        )
    )

    print()

    print(
        "Current Configuration:"
    )

    print(
        plan.get(
            "current",
            ""
        )
    )

    print()

    print(
        "Expected Configuration:"
    )

    print(
        plan.get(
            "expected",
            ""
        )
    )

    print()

    print(
        "Reason:"
    )

    print(
        plan.get(
            "reason",
            ""
        )
    )

    commands = plan.get(
        "commands",
        []
    )

    if commands:

        print()

        print(
            "Cisco Configuration:"
        )

        for command in commands:

            print(
                "  "
                + command
            )

    print()


def create_remediation_plan(
    incident
):
    """
    Create and attach a deterministic remediation plan.

    The plan is not executed by this function.
    """

    updated_incident = dict(
        incident
    )

    plan = build_remediation_plan(
        updated_incident
    )

    updated_incident[
        "remediation_plan"
    ] = plan

    if plan["status"] == (
        "READY_FOR_APPROVAL"
    ):

        updated_incident[
            "status"
        ] = "REMEDIATION_READY"

    elif plan["status"] == "BLOCKED":

        updated_incident[
            "status"
        ] = "REMEDIATION_BLOCKED"

    else:

        updated_incident[
            "status"
        ] = "NO_REMEDIATION_REQUIRED"

    return updated_incident


if __name__ == "__main__":

    print()
    print("========================================")
    print("NETPILOT REMEDIATION PLANNER")
    print("========================================")
    print()

    print(
        "This module creates deterministic "
        "configuration-drift remediation plans."
    )

    print(
        "It does not execute Cisco configuration."
    )

    print()

    print(
        "WAN incidents use a separate remediation "
        "engine."
    )

    print()