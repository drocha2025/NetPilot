from datetime import datetime, timezone

from app.cisco_client import (
    run_config,
    run_command,
)

from app.incident_store import (
    get_latest_approval,
    store_remediation,
    get_latest_remediation,
    store_validation,
    get_latest_validation,
    store_audit_event,
    resolve_incident,
)


def current_timestamp():
    return datetime.now(
        timezone.utc
    ).isoformat()


def validate_remediation_plan(
    incident
):
    """
    Validate a deterministic remediation plan before
    any Cisco configuration is executed.

    This is an additional safety gate after planning
    and engineer approval.
    """

    plan = incident.get(
        "remediation_plan",
        {}
    )

    if plan.get(
        "status"
    ) != "READY_FOR_APPROVAL":

        return {
            "valid": False,
            "reason":
                "Remediation plan is not ready for approval.",
        }

    router = incident.get(
        "router",
        ""
    )

    if not router:

        return {
            "valid": False,
            "reason":
                "Incident router is missing.",
        }

    health = incident.get(
        "health"
    )

    if health in [
        "OFFLINE",
        "UNKNOWN",
    ]:

        return {
            "valid": False,
            "reason":
                "Router health is not confirmed operational.",
        }

    evidence = incident.get(
        "evidence",
        {}
    )

    router_evidence = evidence.get(
        "router_evidence",
        {}
    )

    connectivity = router_evidence.get(
        "connectivity"
    )

    if connectivity not in [
        None,
        "ONLINE",
    ]:

        return {
            "valid": False,
            "reason":
                "Verified router connectivity is not ONLINE.",
        }

    interface = plan.get(
        "interface",
        ""
    )

    expected = plan.get(
        "expected",
        ""
    )

    current = plan.get(
        "current",
        ""
    )

    commands = plan.get(
        "commands",
        []
    )

    if not interface:

        return {
            "valid": False,
            "reason":
                "Affected interface is missing.",
        }

    if not expected:

        return {
            "valid": False,
            "reason":
                "Expected configuration is missing.",
        }

    if not current:

        return {
            "valid": False,
            "reason":
                "Current configuration is missing.",
        }

    if not isinstance(
        commands,
        list
    ):

        return {
            "valid": False,
            "reason":
                "Remediation commands are invalid.",
        }

    if len(commands) != 2:

        return {
            "valid": False,
            "reason":
                "Unexpected number of Cisco configuration commands.",
        }

    expected_interface_command = (
        "interface " + interface
    )

    if commands[0] != (
        expected_interface_command
    ):

        return {
            "valid": False,
            "reason":
                (
                    "Interface command does not match "
                    "the verified affected interface."
                ),
        }

    if commands[1] != expected:

        return {
            "valid": False,
            "reason":
                (
                    "Configuration command does not "
                    "match the verified golden configuration."
                ),
        }

    if not expected.startswith(
        "description "
    ):

        return {
            "valid": False,
            "reason":
                (
                    "Remediation command is outside "
                    "the approved description-remediation policy."
                ),
        }

    return {
        "valid": True,
        "reason":
            "Remediation plan passed validation.",
    }


def get_persisted_approval(
    incident
):
    """
    Retrieve the latest approval from PostgreSQL.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:
        return None

    return get_latest_approval(
        database_id
    )


def get_persisted_remediation(
    incident
):
    """
    Retrieve the latest remediation record.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:
        return None

    return get_latest_remediation(
        database_id
    )


def get_persisted_validation(
    incident
):
    """
    Retrieve the latest validation record.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:
        return None

    return get_latest_validation(
        database_id
    )


def display_change_review(
    incident
):
    """
    Display the deterministic change that will be
    executed after all safety checks pass.
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

    print(
        "Affected Interface:"
    )

    print(
        plan.get(
            "interface",
            ""
        )
    )

    print()

    print(
        "CURRENT:"
    )

    print(
        plan.get(
            "current",
            ""
        )
    )

    print()

    print(
        "EXPECTED:"
    )

    print(
        plan.get(
            "expected",
            ""
        )
    )

    print()

    print(
        "PROPOSED CISCO CONFIGURATION:"
    )

    for command in plan.get(
        "commands",
        []
    ):

        print(
            "  "
            + command
        )

    print()

    print(
        "RISK:"
    )

    print(
        recommendation.get(
            "risk",
            "UNKNOWN"
        )
    )

    print()

    print(
        "VALIDATION:"
    )

    print(
        recommendation.get(
            "validation",
            "Engineer must verify post-change state."
        )
    )


def revalidate_live_state(
    incident
):
    """
    Revalidate the live Cisco configuration immediately
    before applying an approved change.

    The state collected during investigation must still
    match the state reviewed by the engineer.
    """

    plan = incident.get(
        "remediation_plan",
        {}
    )

    router = incident.get(
        "router",
        ""
    )

    interface = plan.get(
        "interface",
        ""
    )

    expected = plan.get(
        "expected",
        ""
    )

    planned_current = plan.get(
        "current",
        ""
    )

    print()
    print("========================================")
    print("NETPILOT PRE-CHANGE STATE REVALIDATION")
    print("========================================")

    print()

    print(
        "Router: "
        + router
    )

    print(
        "Interface: "
        + interface
    )

    print()

    print(
        "Previously Verified State:"
    )

    print(
        planned_current
    )

    print()

    print(
        "Expected Golden State:"
    )

    print(
        expected
    )

    print()

    print(
        "Reading live configuration from Cisco device..."
    )

    verification = run_command(
        router,
        "show running-config interface "
        + interface
    )

    if verification is None:

        reason = (
            "Unable to revalidate live configuration."
        )

        print()
        print(
            "PRE-CHANGE VALIDATION FAILED."
        )

        return {
            "valid": False,
            "reason": reason,
            "live_configuration": "",
            "validated_at":
                current_timestamp(),
        }

    print()
    print(
        "Live Configuration:"
    )

    print(
        verification
    )

    if planned_current not in verification:

        reason = (
            "Live configuration changed after evidence "
            "collection and does not match the "
            "engineer-reviewed state."
        )

        print()
        print(
            "PRE-CHANGE VALIDATION FAILED."
        )

        print()
        print(
            "NetPilot will NOT apply the change."
        )

        return {
            "valid": False,
            "reason": reason,
            "live_configuration":
                verification,
            "validated_at":
                current_timestamp(),
        }

    if expected in verification:

        reason = (
            "Live configuration already matches the "
            "expected golden configuration."
        )

        print()
        print(
            "PRE-CHANGE VALIDATION RESULT: "
            "NO CHANGE REQUIRED."
        )

        return {
            "valid": False,
            "reason": reason,
            "live_configuration":
                verification,
            "validated_at":
                current_timestamp(),
        }

    print()
    print(
        "PRE-CHANGE VALIDATION PASSED."
    )

    print()
    print(
        "Live configuration matches the "
        "engineer-reviewed state."
    )

    return {
        "valid": True,
        "reason":
            "Live state matches the approved change plan.",
        "live_configuration":
            verification,
        "validated_at":
            current_timestamp(),
    }


def persist_remediation(
    incident,
    status,
    plan
):
    """
    Persist remediation state in PostgreSQL.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:

        raise ValueError(
            "Incident database ID is missing."
        )

    remediation_id = store_remediation(
        database_id,
        status,
        plan
    )

    store_audit_event(
        database_id,
        "REMEDIATION_STATE",
        "netpilot",
        {
            "remediation_id":
                remediation_id,

            "incident_id":
                incident.get(
                    "incident_id"
                ),

            "status":
                status,
        }
    )

    return remediation_id


def persist_validation(
    incident,
    status,
    result
):
    """
    Persist validation state in PostgreSQL.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:

        raise ValueError(
            "Incident database ID is missing."
        )

    validation_id = store_validation(
        database_id,
        status,
        result
    )

    store_audit_event(
        database_id,
        "VALIDATION",
        "netpilot",
        {
            "validation_id":
                validation_id,

            "incident_id":
                incident.get(
                    "incident_id"
                ),

            "status":
                status,
        }
    )

    return validation_id


def apply_approved_change(
    incident
):
    """
    Execute an approved deterministic Cisco change.

    Safety sequence:

    1. Verify approval
    2. Validate remediation plan
    3. Revalidate live Cisco state
    4. Persist PRE_CHANGE validation
    5. Persist EXECUTING state
    6. Apply configuration
    7. Collect post-change state
    8. Persist POST_CHANGE validation
    9. Resolve incident only after successful validation
    10. Record audit events

    The LLM is never used to generate the Cisco commands.
    """

    database_id = incident.get(
        "database_id"
    )

    if database_id is None:

        raise ValueError(
            "Incident database ID is missing."
        )

    approval = (
        get_persisted_approval(
            incident
        )
    )

    if approval is None:

        reason = (
            "No persisted engineer approval exists."
        )

        store_audit_event(
            database_id,
            "REMEDIATION_BLOCKED",
            "netpilot",
            {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),
                "reason":
                    reason,
            }
        )

        incident["status"] = (
            "REMEDIATION_BLOCKED"
        )

        return incident

    if approval.get(
        "status"
    ) != "APPROVED":

        reason = (
            "Persisted engineer approval is not APPROVED."
        )

        store_audit_event(
            database_id,
            "REMEDIATION_BLOCKED",
            "netpilot",
            {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),
                "reason":
                    reason,
                "approval_status":
                    approval.get(
                        "status"
                    ),
            }
        )

        incident["status"] = (
            "REMEDIATION_BLOCKED"
        )

        return incident

    plan_validation = (
        validate_remediation_plan(
            incident
        )
    )

    print()
    print("========================================")
    print("NETPILOT REMEDIATION POLICY")
    print("========================================")

    print()

    print(
        "Result: "
        + (
            "PASSED"
            if plan_validation["valid"]
            else "FAILED"
        )
    )

    print(
        "Reason: "
        + plan_validation["reason"]
    )

    if not plan_validation["valid"]:

        persist_remediation(
            incident,
            "BLOCKED",
            incident.get(
                "remediation_plan",
                {}
            )
        )

        store_audit_event(
            database_id,
            "REMEDIATION_BLOCKED",
            "netpilot",
            {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),

                "reason":
                    plan_validation[
                        "reason"
                    ],
            }
        )

        incident["status"] = (
            "REMEDIATION_BLOCKED"
        )

        return incident

    display_change_review(
        incident
    )

    revalidation = (
        revalidate_live_state(
            incident
        )
    )

    incident[
        "pre_change_validation"
    ] = revalidation

    pre_validation_id = (
        persist_validation(
            incident,
            (
                "PASSED"
                if revalidation["valid"]
                else "FAILED"
            ),
            revalidation
        )
    )

    incident[
        "pre_change_validation_id"
    ] = pre_validation_id

    if not revalidation["valid"]:

        persist_remediation(
            incident,
            "BLOCKED",
            incident.get(
                "remediation_plan",
                {}
            )
        )

        store_audit_event(
            database_id,
            "PRE_CHANGE_BLOCKED",
            "netpilot",
            {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),

                "reason":
                    revalidation[
                        "reason"
                    ],
            }
        )

        incident["status"] = (
            "CHANGE_BLOCKED"
        )

        print()
        print("========================================")
        print("NETPILOT CHANGE BLOCKED")
        print("========================================")

        print()

        print(
            "Reason:"
        )

        print(
            revalidation[
                "reason"
            ]
        )

        return incident

    plan = incident[
        "remediation_plan"
    ]

    router = incident[
        "router"
    ]

    interface = plan[
        "interface"
    ]

    current = plan[
        "current"
    ]

    expected = plan[
        "expected"
    ]

    commands = plan[
        "commands"
    ]

    persist_remediation(
        incident,
        "EXECUTING",
        plan
    )

    store_audit_event(
        database_id,
        "REMEDIATION_EXECUTION_STARTED",
        "netpilot",
        {
            "incident_id":
                incident.get(
                    "incident_id"
                ),

            "router":
                router,

            "interface":
                interface,

            "commands":
                commands,
        }
    )

    incident["status"] = (
        "REMEDIATION_EXECUTING"
    )

    print()
    print("========================================")
    print("NETPILOT REMEDIATION")
    print("========================================")

    print()

    print(
        "Router: "
        + router
    )

    print(
        "Interface: "
        + interface
    )

    print()

    print(
        "Applying approved deterministic configuration..."
    )

    output = run_config(
        router,
        commands
    )

    if output is None:

        reason = (
            "Cisco configuration application failed."
        )

        persist_remediation(
            incident,
            "FAILED",
            {
                **plan,
                "execution_result":
                    reason,
            }
        )

        store_audit_event(
            database_id,
            "REMEDIATION_FAILED",
            "netpilot",
            {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),

                "router":
                    router,

                "interface":
                    interface,

                "reason":
                    reason,
            }
        )

        incident["status"] = (
            "REMEDIATION_FAILED"
        )

        print()
        print(
            "Configuration application failed."
        )

        return incident

    print()
    print(
        "Cisco configuration applied."
    )

    post_change = run_command(
        router,
        "show running-config interface "
        + interface
    )

    if post_change is None:

        result = {
            "valid": False,
            "reason":
                (
                    "Configuration was applied, but "
                    "post-change verification could "
                    "not be collected."
                ),
            "verification":
                "",
            "validated_at":
                current_timestamp(),
        }

        validation_status = (
            "FAILED"
        )

    elif expected in post_change:

        result = {
            "valid": True,
            "reason":
                (
                    "Post-change configuration matches "
                    "the expected golden configuration."
                ),
            "verification":
                post_change,
            "validated_at":
                current_timestamp(),
        }

        validation_status = (
            "PASSED"
        )

    else:

        result = {
            "valid": False,
            "reason":
                (
                    "Post-change configuration does not "
                    "match the expected golden configuration."
                ),
            "verification":
                post_change,
            "validated_at":
                current_timestamp(),
        }

        validation_status = (
            "FAILED"
        )

    validation_id = persist_validation(
        incident,
        validation_status,
        result
    )

    incident[
        "post_change_validation"
    ] = result

    incident[
        "post_change_validation_id"
    ] = validation_id

    print()
    print("========================================")
    print("NETPILOT POST-CHANGE VALIDATION")
    print("========================================")

    print()

    print(
        "Result: "
        + validation_status
    )

    print()

    print(
        "Reason:"
    )

    print(
        result[
            "reason"
        ]
    )

    print()

    print(
        "Verification Output:"
    )

    print(
        result.get(
            "verification",
            "UNAVAILABLE"
        )
    )

    if validation_status == "PASSED":

        persist_remediation(
            incident,
            "SUCCESS",
            {
                **plan,
                "execution_output":
                    output,
                "post_change_validation":
                    result,
            }
        )

        store_audit_event(
            database_id,
            "REMEDIATION_SUCCESS",
            "netpilot",
            {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),

                "router":
                    router,

                "interface":
                    interface,

                "validation_id":
                    validation_id,
            }
        )

        resolve_incident(
            incident.get(
                "incident_id"
            )
        )

        incident["status"] = (
            "RESOLVED"
        )

        print()
        print(
            "NETPILOT INCIDENT RESOLVED."
        )

    else:

        persist_remediation(
            incident,
            "VERIFICATION_FAILED",
            {
                **plan,
                "execution_output":
                    output,
                "post_change_validation":
                    result,
            }
        )

        store_audit_event(
            database_id,
            "REMEDIATION_VERIFICATION_FAILED",
            "netpilot",
            {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),

                "router":
                    router,

                "interface":
                    interface,

                "validation_id":
                    validation_id,
            }
        )

        incident["status"] = (
            "REMEDIATION_FAILED"
        )

        print()
        print(
            "NETPILOT REMEDIATION FAILED "
            "POST-CHANGE VALIDATION."
        )

    return incident


if __name__ == "__main__":

    print()
    print("========================================")
    print("NETPILOT PERSISTENT REMEDIATION CONTROLLER")
    print("========================================")
    print()

    print(
        "This module executes only deterministic "
        "engineer-approved Cisco configuration."
    )

    print()

    print(
        "The PostgreSQL incident database is the "
        "system of record."
    )

    print()

    print(
        "No interactive change will be executed "
        "from this standalone module."
    )

    print()