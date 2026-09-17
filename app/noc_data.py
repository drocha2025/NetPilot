from app.database import get_connection


def get_telemetry_anomalies(limit=20):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    router,
                    interface_name,
                    severity,
                    anomaly_type,
                    message,
                    detected_at,
                    status,
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    resolved_at
                FROM telemetry_anomalies
                ORDER BY last_detected_at DESC
                LIMIT %s;
                """,
                (limit,)
            )

            rows = cursor.fetchall()

        anomalies = []

        for row in rows:
            anomalies.append(
                {
                    "id": row[0],
                    "router": row[1],
                    "interface_name": row[2],
                    "severity": row[3],
                    "anomaly_type": row[4],
                    "message": row[5],
                    "detected_at": row[6],
                    "status": row[7],
                    "first_detected_at": row[8],
                    "last_detected_at": row[9],
                    "occurrence_count": row[10],
                    "resolved_at": row[11]
                }
            )

        return anomalies

    except Exception as error:
        print(
            "Failed to retrieve telemetry anomalies: "
            + str(error)
        )
        return []

    finally:
        if connection is not None:
            connection.close()


def get_telemetry_correlations(limit=20):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    router,
                    interface_name,
                    correlation_type,
                    severity,
                    summary,
                    source_anomaly_ids,
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    status,
                    resolved_at
                FROM telemetry_correlations
                ORDER BY last_detected_at DESC
                LIMIT %s;
                """,
                (limit,)
            )

            rows = cursor.fetchall()

        correlations = []

        for row in rows:
            correlations.append(
                {
                    "id": row[0],
                    "router": row[1],
                    "interface_name": row[2],
                    "correlation_type": row[3],
                    "severity": row[4],
                    "summary": row[5],
                    "source_anomaly_ids": row[6],
                    "first_detected_at": row[7],
                    "last_detected_at": row[8],
                    "occurrence_count": row[9],
                    "status": row[10],
                    "resolved_at": row[11]
                }
            )

        return correlations

    except Exception as error:
        print(
            "Failed to retrieve telemetry correlations: "
            + str(error)
        )
        return []

    finally:
        if connection is not None:
            connection.close()


def get_telemetry_ai_assessments(limit=20):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ai.id,
                    ai.correlation_id,
                    ai.status,
                    ai.assessment,
                    ai.likely_explanation,
                    ai.customer_impact,
                    ai.risk,
                    ai.confidence,
                    ai.observed_evidence,
                    ai.recommended_investigation,
                    ai.assumptions,
                    ai.created_at,
                    c.router,
                    c.interface_name,
                    c.correlation_type,
                    c.severity,
                    c.status
                FROM telemetry_ai_analysis ai
                JOIN telemetry_correlations c
                    ON ai.correlation_id = c.id
                ORDER BY ai.created_at DESC
                LIMIT %s;
                """,
                (limit,)
            )

            rows = cursor.fetchall()

        assessments = []

        for row in rows:
            assessments.append(
                {
                    "id": row[0],
                    "correlation_id": row[1],
                    "status": row[2],
                    "assessment": row[3],
                    "likely_explanation": row[4],
                    "customer_impact": row[5],
                    "risk": row[6],
                    "confidence": row[7],
                    "observed_evidence": row[8],
                    "recommended_investigation": row[9],
                    "assumptions": row[10],
                    "created_at": row[11],
                    "router": row[12],
                    "interface_name": row[13],
                    "correlation_type": row[14],
                    "severity": row[15],
                    "correlation_status": row[16]
                }
            )

        return assessments

    except Exception as error:
        print(
            "Failed to retrieve telemetry AI assessments: "
            + str(error)
        )
        return []

    finally:
        if connection is not None:
            connection.close()


def get_telemetry_incidents(limit=20):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    incident_id,
                    router,
                    incident_type,
                    status,
                    health,
                    description,
                    impact,
                    source_type,
                    source_id,
                    created_at,
                    updated_at,
                    resolved_at
                FROM incidents
                WHERE source_type = 'TELEMETRY_CORRELATION'
                ORDER BY updated_at DESC
                LIMIT %s;
                """,
                (limit,)
            )

            rows = cursor.fetchall()

        incidents = []

        for row in rows:
            incidents.append(
                {
                    "database_id": row[0],
                    "incident_id": row[1],
                    "router": row[2],
                    "incident_type": row[3],
                    "status": row[4],
                    "health": row[5],
                    "description": row[6],
                    "impact": row[7],
                    "source_type": row[8],
                    "source_id": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                    "resolved_at": row[12]
                }
            )

        return incidents

    except Exception as error:
        print(
            "Failed to retrieve telemetry incidents: "
            + str(error)
        )
        return []

    finally:
        if connection is not None:
            connection.close()


def get_recent_audit_events(limit=30):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    incident_id,
                    event_type,
                    actor,
                    details,
                    created_at
                FROM audit_events
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (limit,)
            )

            rows = cursor.fetchall()

        events = []

        for row in rows:
            events.append(
                {
                    "id": row[0],
                    "incident_id": row[1],
                    "event_type": row[2],
                    "actor": row[3],
                    "details": row[4],
                    "created_at": row[5]
                }
            )

        return events

    except Exception as error:
        print(
            "Failed to retrieve audit events: "
            + str(error)
        )
        return []

    finally:
        if connection is not None:
            connection.close()


def get_noc_data():
    return {
        "telemetry_anomalies": get_telemetry_anomalies(),
        "telemetry_correlations": get_telemetry_correlations(),
        "telemetry_ai_assessments": get_telemetry_ai_assessments(),
        "telemetry_incidents": get_telemetry_incidents(),
        "recent_audit_events": get_recent_audit_events()
    }


def display_noc_data(data):
    print()
    print("========================================")
    print("NETPILOT NOC DATABASE STATE")
    print("========================================")
    print()

    anomalies = data.get(
        "telemetry_anomalies",
        []
    )

    correlations = data.get(
        "telemetry_correlations",
        []
    )

    ai_assessments = data.get(
        "telemetry_ai_assessments",
        []
    )

    incidents = data.get(
        "telemetry_incidents",
        []
    )

    audit_events = data.get(
        "recent_audit_events",
        []
    )

    print(
        "Telemetry Anomalies: "
        + str(len(anomalies))
    )

    print(
        "Telemetry Correlations: "
        + str(len(correlations))
    )

    print(
        "Telemetry AI Assessments: "
        + str(len(ai_assessments))
    )

    print(
        "Telemetry Incidents: "
        + str(len(incidents))
    )

    print(
        "Recent Audit Events: "
        + str(len(audit_events))
    )

    print()

    print("Telemetry Anomalies")
    print("----------------------------------------")

    for anomaly in anomalies:
        print(
            str(anomaly.get("router", "UNKNOWN"))
            + " | "
            + str(anomaly.get("interface_name", "UNKNOWN"))
            + " | "
            + str(anomaly.get("anomaly_type", "UNKNOWN"))
            + " | "
            + str(anomaly.get("severity", "UNKNOWN"))
            + " | "
            + str(anomaly.get("status", "UNKNOWN"))
        )

    print()

    print("Telemetry Correlations")
    print("----------------------------------------")

    for correlation in correlations:
        print(
            str(correlation.get("router", "UNKNOWN"))
            + " | "
            + str(correlation.get("interface_name", "UNKNOWN"))
            + " | "
            + str(correlation.get("correlation_type", "UNKNOWN"))
            + " | "
            + str(correlation.get("severity", "UNKNOWN"))
            + " | "
            + str(correlation.get("status", "UNKNOWN"))
        )

    print()

    print("Telemetry Incidents")
    print("----------------------------------------")

    for incident in incidents:
        print(
            str(incident.get("incident_id", "UNKNOWN"))
            + " | "
            + str(incident.get("router", "UNKNOWN"))
            + " | "
            + str(incident.get("incident_type", "UNKNOWN"))
            + " | "
            + str(incident.get("status", "UNKNOWN"))
        )

    print()

    print("Recent Audit Events")
    print("----------------------------------------")

    for event in audit_events:
        print(
            str(event.get("event_type", "UNKNOWN"))
            + " | incident="
            + str(event.get("incident_id", "N/A"))
            + " | actor="
            + str(event.get("actor", "UNKNOWN"))
        )

    print()


if __name__ == "__main__":
    data = get_noc_data()
    display_noc_data(data)