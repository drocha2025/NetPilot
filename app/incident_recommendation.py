def determine_action(analysis, incident):
    """
    Determine whether NetPilot should recommend remediation
    or additional investigation.

    AI remains advisory. This function applies deterministic
    NetPilot policy to the verified incident and AI analysis.
    """

    router = incident.get(
        "router",
        "UNKNOWN"
    )

    availability = incident.get(
        "health"
    )

    confidence = str(
        analysis.get(
            "confidence",
            ""
        )
    ).upper()

    risk = str(
        analysis.get(
            "risk",
            ""
        )
    ).upper()

    if availability in [
        "OFFLINE",
        "UNKNOWN",
    ]:

        return {
            "decision": "INVESTIGATE",

            "reason": (
                router
                + " is not confirmed operational. "
                "Configuration remediation must not "
                "be attempted until device health is "
                "verified."
            ),

            "approval_required": False,

            "action": (
                "Restore or verify Cisco device "
                "connectivity and collect additional "
                "operational evidence."
            ),
        }

    if risk == "HIGH":

        return {
            "decision": "INVESTIGATE",

            "reason": (
                "The AI classified the recommended "
                "action as high risk."
            ),

            "approval_required": True,

            "action": (
                "Perform additional engineering "
                "investigation before making "
                "configuration changes."
            ),
        }

    if confidence == "LOW":

        return {
            "decision": "INVESTIGATE",

            "reason": (
                "AI confidence is low. Additional "
                "verified evidence is required."
            ),

            "approval_required": False,

            "action": (
                "Collect additional Cisco operational "
                "evidence before considering remediation."
            ),
        }

    recommended_action = analysis.get(
        "recommended_action",
        ""
    )

    if not recommended_action:

        return {
            "decision": "INVESTIGATE",

            "reason": (
                "The AI analysis did not provide a "
                "recommended engineering action."
            ),

            "approval_required": False,

            "action": (
                "Collect additional evidence and "
                "perform engineering investigation."
            ),
        }

    return {
        "decision": "REVIEW",

        "reason": (
            "The incident has sufficient verified "
            "evidence and AI confidence for engineer "
            "review."
        ),

        "approval_required": True,

        "action": recommended_action,
    }


def build_recommendation(
    incident,
    analysis=None
):
    """
    Build a structured NetPilot engineering
    recommendation from the persisted AI analysis.

    The recommendation does not generate Cisco
    configuration commands.
    """

    if analysis is None:

        analysis = incident.get(
            "ai_analysis"
        )

    if not isinstance(
        analysis,
        dict
    ):

        return {
            **incident,
            "recommendation": {
                "incident_id":
                    incident.get(
                        "incident_id"
                    ),

                "router":
                    incident.get(
                        "router",
                        "UNKNOWN"
                    ),

                "decision":
                    "INVESTIGATE",

                "reason":
                    "No structured AI analysis is available.",

                "action":
                    "Collect additional evidence.",

                "approval_required":
                    False,

                "root_cause":
                    "",

                "confidence":
                    "",

                "impact":
                    "",

                "risk":
                    "",

                "validation":
                    "",

                "customer_summary":
                    "",
            },

            "status":
                "RECOMMENDATION_BLOCKED",
        }

    decision = determine_action(
        analysis,
        incident
    )

    recommendation = {
        "incident_id":
            incident.get(
                "incident_id"
            ),

        "router":
            incident.get(
                "router",
                "UNKNOWN"
            ),

        "decision":
            decision["decision"],

        "reason":
            decision["reason"],

        "action":
            decision["action"],

        "approval_required":
            decision["approval_required"],

        "root_cause":
            analysis.get(
                "root_cause",
                ""
            ),

        "confidence":
            analysis.get(
                "confidence",
                ""
            ),

        "impact":
            analysis.get(
                "customer_impact",
                ""
            ),

        "risk":
            analysis.get(
                "risk",
                ""
            ),

        "validation":
            analysis.get(
                "validation",
                ""
            ),

        "customer_summary":
            analysis.get(
                "customer_impact",
                ""
            ),
    }

    updated_incident = dict(
        incident
    )

    updated_incident[
        "recommendation"
    ] = recommendation

    updated_incident[
        "status"
    ] = "RECOMMENDATION_READY"

    return updated_incident


def display_recommendation(
    incident
):
    """
    Display the engineering recommendation.
    """

    recommendation = incident.get(
        "recommendation",
        {}
    )

    print()
    print("========================================")
    print("NETPILOT ENGINEERING RECOMMENDATION")
    print("========================================")

    print()

    print(
        "Incident ID: "
        + str(
            recommendation.get(
                "incident_id",
                incident.get(
                    "incident_id",
                    "UNKNOWN"
                )
            )
        )
    )

    print(
        "Router: "
        + recommendation.get(
            "router",
            "UNKNOWN"
        )
    )

    print()

    print(
        "Decision: "
        + recommendation.get(
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

    print("Confidence:")

    print(
        recommendation.get(
            "confidence",
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

    print("Reason:")

    print(
        recommendation.get(
            "reason",
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

    print(
        "Approval Required: "
        + str(
            recommendation.get(
                "approval_required",
                False
            )
        )
    )

    print()

    print("Validation:")

    print(
        recommendation.get(
            "validation",
            "UNKNOWN"
        )
    )

    print()

    print("Customer Impact:")

    print(
        recommendation.get(
            "customer_summary",
            "UNKNOWN"
        )
    )

    print()


if __name__ == "__main__":

    print(
        "This module is designed to operate on "
        "the current PostgreSQL-backed incident "
        "and structured AI analysis model."
    )