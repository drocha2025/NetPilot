from datetime import datetime, timezone

from app.monitoring import (
    collect_health_snapshot
)

from app.incident_manager import (
    process_health_snapshot
)

from app.ai_incident_persistence import (
    analyze_persisted_incident
)

from app.incident_recommendation import (
    build_recommendation
)

from app.remediation_planner import (
    create_remediation_plan
)

from app.incident_approval import (
    request_engineer_approval
)

from app.incident_remediation import (
    apply_approved_change
)


def current_timestamp():
    return datetime.now(
        timezone.utc
    ).isoformat()


def get_primary_wan_incident(
    incident_result
):
    """
    Find an active primary WAN incident.
    """

    for incident in incident_result.get(
        "active",
        []
    ):

        if incident.get(
            "incident_type"
        ) == "PRIMARY_WAN_FAILURE":

            return incident

    return None


def get_configuration_drift_incident(
    incident_result
):
    """
    Find an active configuration-drift incident.

    Configuration drift is currently the only
    incident type approved for the deterministic
    remediation planner.
    """

    for incident in incident_result.get(
        "active",
        []
    ):

        if incident.get(
            "incident_type"
        ) == "CONFIGURATION_DRIFT":

            return incident

    return None


def get_change_control_incident(
    incident_result
):
    """
    Select an incident eligible for the current
    persistent change-control workflow.

    WAN incidents are deliberately excluded.
    """

    incident = (
        get_configuration_drift_incident(
            incident_result
        )
    )

    if incident is not None:
        return incident

    return None


def run_incident_detection():
    """
    Collect current network health and
    process incidents.

    Incident persistence is handled by the
    PostgreSQL-backed incident manager.
    """

    snapshot = (
        collect_health_snapshot()
    )

    incident_result = (
        process_health_snapshot(
            snapshot
        )
    )

    return {
        "status":
            "COMPLETED",

        "collected":
            snapshot.get(
                "collected"
            ),

        "snapshot":
            snapshot,

        "incidents":
            incident_result,
    }


def run_ai_diagnosis(
    incident_result
):
    """
    Run PostgreSQL-aware AI diagnosis.

    Existing AI analysis is reused.

    New analysis is generated only when an
    active incident does not already have
    persisted AI analysis.

    The AI does not make network changes.
    """

    incident = (
        get_primary_wan_incident(
            incident_result
        )
    )

    if incident is None:

        incident = (
            get_configuration_drift_incident(
                incident_result
            )
        )

    if incident is None:

        return {
            "status":
                "NO_INCIDENT",

            "incident":
                None,

            "analysis":
                None,
        }

    result = (
        analyze_persisted_incident(
            incident
        )
    )

    incident["ai_analysis"] = (
        result.get(
            "analysis"
        )
    )

    return result


def run_change_control(
    incident,
    interactive=False,
    execute=False
):
    """
    Execute the persistent configuration-drift
    change-control workflow.

    This function deliberately refuses WAN incidents.

    Workflow:

    1. Verify incident type
    2. Build engineering recommendation
    3. Build deterministic remediation plan
    4. Request persistent engineer approval
    5. Execute only when explicitly authorized
    6. Perform pre-change validation
    7. Execute Cisco configuration
    8. Perform post-change validation
    9. Resolve incident after successful validation

    execute=False is the safe default.

    When execute=False, NetPilot performs planning
    and approval evaluation but does not change Cisco.
    """

    if incident is None:

        return {
            "status":
                "NO_INCIDENT",

            "incident":
                None,

            "recommendation":
                None,

            "remediation_plan":
                None,

            "approval":
                None,
        }

    incident_type = incident.get(
        "incident_type",
        ""
    )

    if incident_type != (
        "CONFIGURATION_DRIFT"
    ):

        return {
            "status":
                "NOT_SUPPORTED",

            "incident":
                incident,

            "recommendation":
                None,

            "remediation_plan":
                None,

            "approval":
                None,

            "reason":
                (
                    "The current persistent configuration "
                    "remediation workflow only supports "
                    "CONFIGURATION_DRIFT incidents. WAN "
                    "incidents require the dedicated WAN "
                    "remediation engine."
                ),
        }

    working_incident = dict(
        incident
    )

    analysis = (
        working_incident.get(
            "ai_analysis"
        )
    )

    if not isinstance(
        analysis,
        dict
    ):

        return {
            "status":
                "BLOCKED",

            "incident":
                working_incident,

            "recommendation":
                None,

            "remediation_plan":
                None,

            "approval":
                None,

            "reason":
                (
                    "No structured persisted AI analysis "
                    "is available for this incident."
                ),
        }

    working_incident = (
        build_recommendation(
            working_incident,
            analysis
        )
    )

    working_incident = (
        create_remediation_plan(
            working_incident
        )
    )

    plan = working_incident.get(
        "remediation_plan",
        {}
    )

    if plan.get(
        "status"
    ) != "READY_FOR_APPROVAL":

        return {
            "status":
                "REMEDIATION_BLOCKED",

            "incident":
                working_incident,

            "recommendation":
                working_incident.get(
                    "recommendation"
                ),

            "remediation_plan":
                plan,

            "approval":
                None,

            "reason":
                plan.get(
                    "reason",
                    "Remediation plan is not ready.",
                ),
        }

    approval_result = (
        request_engineer_approval(
            working_incident,
            interactive=interactive
        )
    )

    working_incident = (
        approval_result
    )

    approval = (
        working_incident.get(
            "approval"
        )
    )

    if not execute:

        return {
            "status":
                "APPROVAL_REVIEW",

            "incident":
                working_incident,

            "recommendation":
                working_incident.get(
                    "recommendation"
                ),

            "remediation_plan":
                working_incident.get(
                    "remediation_plan"
                ),

            "approval":
                approval,

            "reason":
                (
                    "Change execution is disabled. "
                    "No Cisco configuration was applied."
                ),
        }

    if working_incident.get(
        "status"
    ) != "APPROVED":

        return {
            "status":
                "BLOCKED",

            "incident":
                working_incident,

            "recommendation":
                working_incident.get(
                    "recommendation"
                ),

            "remediation_plan":
                working_incident.get(
                    "remediation_plan"
                ),

            "approval":
                approval,

            "reason":
                (
                    "Cisco configuration cannot execute "
                    "because the persisted approval state "
                    "is not APPROVED."
                ),
        }

    remediation_result = (
        apply_approved_change(
            working_incident
        )
    )

    return {
        "status":
            remediation_result.get(
                "status",
                "UNKNOWN"
            ),

        "incident":
            remediation_result,

        "recommendation":
            remediation_result.get(
                "recommendation"
            ),

        "remediation_plan":
            remediation_result.get(
                "remediation_plan"
            ),

        "approval":
            remediation_result.get(
                "approval"
            ),

        "pre_change_validation":
            remediation_result.get(
                "pre_change_validation"
            ),

        "post_change_validation":
            remediation_result.get(
                "post_change_validation"
            ),
    }


def run_incident_workflow(
    run_ai=True,
    run_change_control=False,
    interactive=False,
    execute=False
):
    """
    Execute the unified persistent NetPilot workflow.

    Default behavior is READ-ONLY.

    Workflow:

    1. Collect network state
    2. Detect incidents
    3. Persist incident and evidence
    4. Analyze with Ollama when required
    5. Build engineering recommendation
    6. Build deterministic remediation plan
    7. Evaluate persistent approval
    8. Optionally execute approved change
    9. Validate and resolve

    Important:

    execute=False is the default and prevents
    Cisco configuration changes.
    """

    started = current_timestamp()

    workflow = {
        "workflow_id":
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y%m%d%H%M%S%f"
            ),

        "started":
            started,

        "status":
            "STARTED",

        "detection":
            None,

        "ai":
            None,

        "change_control":
            None,

        "incidents":
            None,
    }

    detection = (
        run_incident_detection()
    )

    workflow[
        "detection"
    ] = detection

    workflow[
        "incidents"
    ] = detection.get(
        "incidents"
    )

    if run_ai:

        ai_result = (
            run_ai_diagnosis(
                detection.get(
                    "incidents",
                    {}
                )
            )
        )

        workflow[
            "ai"
        ] = ai_result

    if run_change_control:

        change_incident = (
            get_change_control_incident(
                detection.get(
                    "incidents",
                    {}
                )
            )
        )

        workflow[
            "change_control"
        ] = run_change_control(
            change_incident,
            interactive=interactive,
            execute=execute
        )

    else:

        workflow[
            "change_control"
        ] = {
            "status":
                "NOT_RUN",

            "reason":
                (
                    "Change control was not requested."
                ),
        }

    workflow[
        "status"
    ] = "COMPLETED"

    workflow[
        "completed"
    ] = current_timestamp()

    return workflow


def display_incident_workflow(
    workflow
):
    """
    Display the unified persistent
    incident workflow.
    """

    print()
    print("========================================")
    print("NETPILOT INCIDENT ORCHESTRATOR")
    print("========================================")
    print()

    print(
        "Workflow ID: "
        + workflow.get(
            "workflow_id",
            "UNKNOWN"
        )
    )

    print(
        "Status: "
        + workflow.get(
            "status",
            "UNKNOWN"
        )
    )

    print()

    incidents = workflow.get(
        "incidents",
        {}
    )

    print(
        "ACTIVE INCIDENTS: "
        + str(
            incidents.get(
                "active_count",
                0
            )
        )
    )

    for incident in incidents.get(
        "active",
        []
    ):

        print()

        print(
            "Incident: "
            + incident.get(
                "incident_type",
                "UNKNOWN"
            )
        )

        print(
            "Incident ID: "
            + incident.get(
                "incident_id",
                "UNKNOWN"
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
            "Status: "
            + incident.get(
                "status",
                "UNKNOWN"
            )
        )

        print(
            "Impact: "
            + incident.get(
                "impact",
                "UNKNOWN"
            )
        )

        print(
            "Database ID: "
            + str(
                incident.get(
                    "database_id",
                    "UNKNOWN"
                )
            )
        )

        symptoms = (
            incident.get(
                "correlation",
                {}
            ).get(
                "symptoms",
                []
            )
        )

        if symptoms:

            print(
                "Correlated symptoms:"
            )

            for symptom in symptoms:

                print(
                    "  - "
                    + symptom
                )

    print()

    ai_result = workflow.get(
        "ai"
    )

    if ai_result is None:

        print(
            "AI: NOT_RUN"
        )

    else:

        print(
            "AI STATUS: "
            + ai_result.get(
                "status",
                "UNKNOWN"
            )
        )

        if ai_result.get(
            "analysis_id"
        ) is not None:

            print(
                "AI ANALYSIS ID: "
                + str(
                    ai_result[
                        "analysis_id"
                    ]
                )
            )

        analysis = (
            ai_result.get(
                "analysis"
            )
        )

        if analysis:

            print()
            print(
                "AI ROOT CAUSE:"
            )

            print(
                analysis.get(
                    "root_cause",
                    "NOT_AVAILABLE"
                )
            )

            print()
            print(
                "AI CONFIDENCE:"
            )

            print(
                analysis.get(
                    "confidence",
                    "NOT_AVAILABLE"
                )
            )

            print()
            print(
                "AI RISK:"
            )

            print(
                analysis.get(
                    "risk",
                    "NOT_AVAILABLE"
                )
            )

            print()
            print(
                "AI RECOMMENDED ACTION:"
            )

            print(
                analysis.get(
                    "recommended_action",
                    "NOT_AVAILABLE"
                )
            )

        if ai_result.get(
            "error"
        ):

            print()
            print(
                "AI ERROR:"
            )

            print(
                str(
                    ai_result[
                        "error"
                    ]
                )
            )

    change_control = workflow.get(
        "change_control"
    )

    print()
    print("========================================")
    print("CHANGE CONTROL")
    print("========================================")
    print()

    if not change_control:

        print(
            "Status: NOT_RUN"
        )

        print()
        return

    print(
        "Status: "
        + change_control.get(
            "status",
            "UNKNOWN"
        )
    )

    if change_control.get(
        "reason"
    ):

        print()

        print(
            "Reason:"
        )

        print(
            change_control[
                "reason"
            ]
        )

    recommendation = (
        change_control.get(
            "recommendation"
        )
    )

    if recommendation:

        print()

        print(
            "Engineering Decision: "
            + recommendation.get(
                "decision",
                "UNKNOWN"
            )
        )

        print(
            "Engineering Action: "
            + recommendation.get(
                "action",
                "UNKNOWN"
            )
        )

    plan = (
        change_control.get(
            "remediation_plan"
        )
    )

    if plan:

        print()

        print(
            "Remediation Plan Status: "
            + plan.get(
                "status",
                "UNKNOWN"
            )
        )

        if plan.get(
            "interface"
        ):

            print(
                "Affected Interface: "
                + plan[
                    "interface"
                ]
            )

        commands = plan.get(
            "commands",
            []
        )

        if commands:

            print()

            print(
                "Proposed Cisco Configuration:"
            )

            for command in commands:

                print(
                    "  "
                    + command
                )

    approval = (
        change_control.get(
            "approval"
        )
    )

    if approval:

        print()

        print(
            "Approval Status: "
            + str(
                approval.get(
                    "status",
                    "UNKNOWN"
                )
            )
        )

        print(
            "Engineer: "
            + str(
                approval.get(
                    "engineer",
                    ""
                )
            )
        )

        print(
            "Decision: "
            + str(
                approval.get(
                    "decision",
                    ""
                )
            )
        )

    if change_control.get(
        "pre_change_validation"
    ):

        print()

        print(
            "Pre-Change Validation: "
            + (
                "PASSED"
                if change_control[
                    "pre_change_validation"
                ].get(
                    "valid"
                )
                else "FAILED"
            )
        )

    if change_control.get(
        "post_change_validation"
    ):

        print()

        print(
            "Post-Change Validation: "
            + (
                "PASSED"
                if change_control[
                    "post_change_validation"
                ].get(
                    "valid"
                )
                else "FAILED"
            )
        )

    print()


if __name__ == "__main__":

    workflow = (
        run_incident_workflow(
            run_ai=True,
            run_change_control=False,
            interactive=False,
            execute=False
        )
    )

    display_incident_workflow(
        workflow
    )