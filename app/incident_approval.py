from datetime import datetime, timezone

from app.incident_store import (
    get_latest_approval,
    store_approval,
    store_audit_event,
)


def current_timestamp():
    return datetime.now(
        timezone.utc
    ).isoformat()


def validate_remediation_plan(
    incident
):
    """
    Validate that a deterministic remediation plan
    exists and is safe to present for engineer approval.

    This function does not execute configuration.
    """

    plan = incident.get(
        "remediation_plan",
        {}
    )

    if not isinstance(
        plan,
        dict
    ):
        return {
            "valid": False,
            "reason": (
                "Remediation plan is missing."
            ),
        }

    if plan.get(
        "status"
    ) != "READY_FOR_APPROVAL":

        return {
            "valid": False,
            "reason": (
                "Remediation plan is not ready "
                "for approval."
            ),
        }

    router = incident.get(
        "router",
        ""
    )

    if not router:

        return {
            "valid": False,
            "reason": (
                "Incident router is missing."
            ),
        }

    health = incident.get(
        "health",
        "UNKNOWN"
    )

    if health in [
        "OFFLINE",
        "UNKNOWN",
    ]:

        return {
            "valid": False,
            "reason": (
                "Router health is not confirmed "
                "operational."
            ),
        }

    commands = plan.get(
        "commands",
        []
    )

    if not isinstance(
        commands,
        list
    ):

        return {
            "valid": False,
            "reason": (
                "Remediation commands are invalid."
            ),
        }

    if not commands:

        return {
            "valid": False,
            "reason": (
                "Remediation plan contains no "
                "configuration commands."
            ),
        }

    for command in commands:

        if not isinstance(
            command,
            str
        ):

            return {
                "valid": False,
                "reason": (
                    "Remediation commands must "
                    "be strings."
                ),
            }

        if not command.strip():

            return {
                "valid": False,
                "reason": (
                    "Remediation plan contains "
                    "an empty command."
                ),
            }

    return {
        "valid": True,
        "reason": (
            "Remediation plan passed "
            "policy validation."
        ),
    }


def get_existing_approval(
    incident
):
    """
    Retrieve the latest persisted approval decision.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:

        return None

    return get_latest_approval(
        database_id
    )


def display_change_review(
    incident
):
    """
    Display the deterministic change plan
    before engineer approval.
    """

    plan = incident.get(
        "remediation_plan",
        {}
    )

    recommendation = incident.get(
        "recommendation",
        {}
    )

    print()
    print("========================================")
    print("NETPILOT ENGINEER CHANGE REVIEW")
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

    print("Engineering Decision:")

    print(
        recommendation.get(
            "decision",
            "UNKNOWN"
        )
    )

    print()

    print("Root Cause:")

    print(
        recommendation.get(
            "root_cause",
            "UNKNOWN"
        )
    )

    print()

    print("Risk:")

    print(
        recommendation.get(
            "risk",
            "UNKNOWN"
        )
    )

    print()

    print("Recommended Action:")

    print(
        recommendation.get(
            "action",
            "UNKNOWN"
        )
    )

    print()

    print("Remediation Plan:")

    print(
        "Plan Status: "
        + str(
            plan.get(
                "status",
                "UNKNOWN"
            )
        )
    )

    if plan.get(
        "interface"
    ):

        print(
            "Affected Interface: "
            + str(
                plan["interface"]
            )
        )

    if plan.get(
        "current"
    ):

        print()

        print("Current Configuration:")

        print(
            plan["current"]
        )

    if plan.get(
        "expected"
    ):

        print()

        print("Expected Configuration:")

        print(
            plan["expected"]
        )

    print()

    print("Proposed Cisco Configuration:")

    for command in plan.get(
        "commands",
        []
    ):

        print(
            "  "
            + command
        )

    print()

    print("Validation:")

    print(
        recommendation.get(
            "validation",
            "Engineer must verify post-change state."
        )
    )


def persist_approval(
    incident,
    status,
    engineer,
    decision,
    notes
):
    """
    Persist engineer approval decision and
    create an audit event.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:

        raise ValueError(
            "Incident database ID is missing."
        )

    approval_id = store_approval(
        database_id,
        status,
        engineer,
        decision,
        notes
    )

    store_audit_event(
        database_id,
        "ENGINEER_APPROVAL",
        engineer or "netpilot",
        {
            "approval_id":
                approval_id,

            "incident_id":
                incident.get(
                    "incident_id"
                ),

            "status":
                status,

            "decision":
                decision,

            "notes":
                notes,
        }
    )

    return approval_id


def request_engineer_approval(
    incident,
    interactive=True
):
    """
    Process engineer approval using PostgreSQL
    as the system of record.

    If an approval already exists, it is reused.

    No Cisco configuration is executed here.
    """

    existing = get_existing_approval(
        incident
    )

    if existing is not None:

        print()
        print("========================================")
        print("NETPILOT EXISTING APPROVAL")
        print("========================================")

        print()

        print(
            "Approval ID: "
            + str(
                existing["id"]
            )
        )

        print(
            "Status: "
            + str(
                existing["status"]
            )
        )

        print(
            "Engineer: "
            + str(
                existing.get(
                    "engineer",
                    ""
                )
            )
        )

        print(
            "Decision: "
            + str(
                existing.get(
                    "decision",
                    ""
                )
            )
        )

        if existing.get(
            "notes"
        ):

            print(
                "Notes: "
                + str(
                    existing["notes"]
                )
            )

        print()

        updated = dict(
            incident
        )

        updated[
            "approval"
        ] = existing

        if existing["status"] == "APPROVED":

            updated[
                "status"
            ] = "APPROVED"

        elif existing["status"] == "REJECTED":

            updated[
                "status"
            ] = "CHANGE_REJECTED"

        else:

            updated[
                "status"
            ] = "REMEDIATION_BLOCKED"

        return updated

    policy = validate_remediation_plan(
        incident
    )

    print()
    print("========================================")
    print("NETPILOT POLICY VALIDATION")
    print("========================================")

    print()

    print(
        "Result: "
        + (
            "PASSED"
            if policy["valid"]
            else "FAILED"
        )
    )

    print(
        "Reason: "
        + policy["reason"]
    )

    if not policy["valid"]:

        database_id = incident.get(
            "database_id"
        )

        if database_id is not None:

            approval_id = persist_approval(
                incident,
                "BLOCKED",
                "",
                "BLOCK",
                policy["reason"]
            )

            approval = {
                "id":
                    approval_id,

                "status":
                    "BLOCKED",

                "engineer":
                    "",

                "decision":
                    "BLOCK",

                "notes":
                    policy["reason"],

                "approved_at":
                    None,
            }

        else:

            approval = {
                "id":
                    None,

                "status":
                    "BLOCKED",

                "engineer":
                    "",

                "decision":
                    "BLOCK",

                "notes":
                    policy["reason"],

                "approved_at":
                    None,
            }

        updated = dict(
            incident
        )

        updated[
            "approval"
        ] = approval

        updated[
            "status"
        ] = "REMEDIATION_BLOCKED"

        return updated

    display_change_review(
        incident
    )

    if not interactive:

        return {
            **incident,
            "approval": {
                "status":
                    "PENDING",

                "engineer":
                    "",

                "decision":
                    "PENDING",

                "notes":
                    "Interactive approval not requested.",

                "approved_at":
                    None,
            },

            "status":
                "AWAITING_APPROVAL",
        }

    print()

    engineer = input(
        "Engineer name: "
    ).strip()

    if not engineer:

        reason = (
            "Engineer name not provided."
        )

        approval_id = persist_approval(
            incident,
            "REJECTED",
            "",
            "REJECT",
            reason
        )

        approval = {
            "id":
                approval_id,

            "status":
                "REJECTED",

            "engineer":
                "",

            "decision":
                "REJECT",

            "notes":
                reason,

            "approved_at":
                None,
        }

        updated = dict(
            incident
        )

        updated[
            "approval"
        ] = approval

        updated[
            "status"
        ] = "CHANGE_REJECTED"

        return updated

    print()

    approval = input(
        "Approve this Cisco change? (yes/no): "
    ).strip().lower()

    if approval != "yes":

        reason = (
            "Engineer rejected the change."
        )

        approval_id = persist_approval(
            incident,
            "REJECTED",
            engineer,
            "REJECT",
            reason
        )

        approval_record = {
            "id":
                approval_id,

            "status":
                "REJECTED",

            "engineer":
                engineer,

            "decision":
                "REJECT",

            "notes":
                reason,

            "approved_at":
                None,
        }

        updated = dict(
            incident
        )

        updated[
            "approval"
        ] = approval_record

        updated[
            "status"
        ] = "CHANGE_REJECTED"

        print()
        print(
            "Change rejected."
        )

        return updated

    notes = (
        "Engineer approved the change."
    )

    approval_id = persist_approval(
        incident,
        "APPROVED",
        engineer,
        "APPROVE",
        notes
    )

    approval_record = {
        "id":
            approval_id,

        "status":
            "APPROVED",

        "engineer":
            engineer,

        "decision":
            "APPROVE",

        "notes":
            notes,

        "approved_at":
            current_timestamp(),
    }

    updated = dict(
        incident
    )

    updated[
        "approval"
    ] = approval_record

    updated[
        "status"
    ] = "APPROVED"

    print()

    print(
        "Change approved by "
        + engineer
        + "."
    )

    return updated


if __name__ == "__main__":

    print()
    print("========================================")
    print("NETPILOT PERSISTENT APPROVAL CONTROLLER")
    print("========================================")
    print()
    print(
        "This module requires a persisted incident "
        "and deterministic remediation plan."
    )
    print(
        "No Cisco configuration is executed by "
        "this module."
    )
    print()