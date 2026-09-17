from app.database import get_connection


INCIDENT_ID = "20260904125411222763"


def get_incident():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    incident_id,
                    router,
                    incident_type,
                    status,
                    description,
                    impact,
                    health,
                    active_path,
                    default_next_hop,
                    created_at,
                    updated_at,
                    resolved_at
                FROM incidents
                WHERE incident_id = %s
                """,
                (INCIDENT_ID,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "database_id": row[0],
                "incident_id": row[1],
                "router": row[2],
                "incident_type": row[3],
                "status": row[4],
                "description": row[5],
                "impact": row[6],
                "health": row[7],
                "active_path": row[8],
                "default_next_hop": row[9],
                "created_at": row[10],
                "updated_at": row[11],
                "resolved_at": row[12],
            }

    finally:
        connection.close()


def get_evidence(database_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    evidence_type,
                    evidence,
                    collected_at
                FROM incident_evidence
                WHERE incident_id = %s
                ORDER BY collected_at ASC, id ASC
                """,
                (database_id,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "evidence_type": row[1],
                    "evidence": row[2],
                    "collected_at": row[3],
                }
                for row in rows
            ]

    finally:
        connection.close()


def get_ai_analysis(database_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    root_cause,
                    confidence,
                    risk,
                    analysis,
                    created_at
                FROM ai_analysis
                WHERE incident_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (database_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "status": row[1],
                "root_cause": row[2],
                "confidence": row[3],
                "risk": row[4],
                "analysis": row[5],
                "created_at": row[6],
            }

    finally:
        connection.close()


def get_approvals(database_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    engineer,
                    decision,
                    notes,
                    approved_at
                FROM approvals
                WHERE incident_id = %s
                ORDER BY id ASC
                """,
                (database_id,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "status": row[1],
                    "engineer": row[2],
                    "decision": row[3],
                    "notes": row[4],
                    "approved_at": row[5],
                }
                for row in rows
            ]

    finally:
        connection.close()


def get_remediation(database_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    plan,
                    executed_at
                FROM remediation
                WHERE incident_id = %s
                ORDER BY id ASC
                """,
                (database_id,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "status": row[1],
                    "plan": row[2],
                    "executed_at": row[3],
                }
                for row in rows
            ]

    finally:
        connection.close()


def get_validation(database_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    result,
                    validated_at
                FROM validation
                WHERE incident_id = %s
                ORDER BY id ASC
                """,
                (database_id,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "status": row[1],
                    "result": row[2],
                    "validated_at": row[3],
                }
                for row in rows
            ]

    finally:
        connection.close()


def get_audit_events(database_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    event_type,
                    actor,
                    details,
                    created_at
                FROM audit_events
                WHERE incident_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (database_id,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "event_type": row[1],
                    "actor": row[2],
                    "details": row[3],
                    "created_at": row[4],
                }
                for row in rows
            ]

    finally:
        connection.close()


def display_section(title):
    print()
    print("========================================")
    print(title)
    print("========================================")


def main():
    print()
    print("========================================")
    print("NETPILOT INCIDENT PERSISTENCE VALIDATION")
    print("========================================")
    print()
    print("Incident ID: " + INCIDENT_ID)

    incident = get_incident()

    if incident is None:
        print()
        print("Incident not found.")
        return

    display_section("INCIDENT")

    print("Database ID: " + str(incident["database_id"]))
    print("Incident ID: " + incident["incident_id"])
    print("Router: " + incident["router"])
    print("Type: " + incident["incident_type"])
    print("Status: " + incident["status"])
    print("Health: " + str(incident["health"]))
    print("Active Path: " + str(incident["active_path"]))
    print("Default Next Hop: " + str(incident["default_next_hop"]))

    evidence = get_evidence(
        incident["database_id"]
    )

    display_section("EVIDENCE")

    print("Evidence records: " + str(len(evidence)))

    for item in evidence:
        print()
        print(
            "Evidence ID: "
            + str(item["id"])
        )
        print(
            "Type: "
            + str(item["evidence_type"])
        )
        print(
            "Collected: "
            + str(item["collected_at"])
        )
        print(
            "Evidence: "
            + str(item["evidence"])
        )

    ai_analysis = get_ai_analysis(
        incident["database_id"]
    )

    display_section("AI ANALYSIS")

    if ai_analysis is None:
        print("AI analysis: NOT FOUND")
    else:
        print(
            "Analysis ID: "
            + str(ai_analysis["id"])
        )
        print(
            "Status: "
            + str(ai_analysis["status"])
        )
        print(
            "Root Cause: "
            + str(ai_analysis["root_cause"])
        )
        print(
            "Confidence: "
            + str(ai_analysis["confidence"])
        )
        print(
            "Risk: "
            + str(ai_analysis["risk"])
        )
        print(
            "Created: "
            + str(ai_analysis["created_at"])
        )

    approvals = get_approvals(
        incident["database_id"]
    )

    display_section("APPROVALS")

    print(
        "Approval records: "
        + str(len(approvals))
    )

    for item in approvals:
        print()
        print("Approval ID: " + str(item["id"]))
        print("Status: " + str(item["status"]))
        print("Engineer: " + str(item["engineer"]))
        print("Decision: " + str(item["decision"]))
        print("Notes: " + str(item["notes"]))
        print("Approved: " + str(item["approved_at"]))

    remediation = get_remediation(
        incident["database_id"]
    )

    display_section("REMEDIATION")

    print(
        "Remediation records: "
        + str(len(remediation))
    )

    for item in remediation:
        print()
        print("Remediation ID: " + str(item["id"]))
        print("Status: " + str(item["status"]))
        print("Plan: " + str(item["plan"]))
        print("Executed: " + str(item["executed_at"]))

    validation = get_validation(
        incident["database_id"]
    )

    display_section("VALIDATION")

    print(
        "Validation records: "
        + str(len(validation))
    )

    for item in validation:
        print()
        print("Validation ID: " + str(item["id"]))
        print("Status: " + str(item["status"]))
        print("Result: " + str(item["result"]))
        print("Validated: " + str(item["validated_at"]))

    audit_events = get_audit_events(
        incident["database_id"]
    )

    display_section("AUDIT EVENTS")

    print(
        "Audit events: "
        + str(len(audit_events))
    )

    for item in audit_events:
        print()
        print("Event ID: " + str(item["id"]))
        print("Event Type: " + str(item["event_type"]))
        print("Actor: " + str(item["actor"]))
        print("Details: " + str(item["details"]))
        print("Created: " + str(item["created_at"]))

    display_section("PERSISTENCE SUMMARY")

    checks = {
        "Incident persisted": incident is not None,
        "Evidence persisted": len(evidence) > 0,
        "AI analysis persisted": ai_analysis is not None,
        "Audit events persisted": len(audit_events) > 0,
    }

    for check, passed in checks.items():
        status = "PASS" if passed else "NOT PRESENT"
        print(status + " - " + check)

    print()

    if all(
        [
            checks["Incident persisted"],
            checks["Evidence persisted"],
            checks["AI analysis persisted"],
        ]
    ):
        print("Core persistence chain: PASS")
    else:
        print("Core persistence chain: INCOMPLETE")

    print()


if __name__ == "__main__":
    main()