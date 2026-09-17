import json
import uuid

from app.database import get_connection
from app.telemetry_correlation import get_open_correlations
from app.telemetry_ai import get_existing_ai_analysis


def generate_incident_id():
    return (
        "TEL-"
        + uuid.uuid4().hex[:12].upper()
    )


def find_existing_incident(
    correlation_id
):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    incident_id,
                    status
                FROM incidents
                WHERE source_type = 'TELEMETRY_CORRELATION'
                  AND source_id = %s
                ORDER BY id DESC
                LIMIT 1;
                """,
                (correlation_id,)
            )

            return cursor.fetchone()

    except Exception as error:
        print(
            "Failed to find telemetry incident: "
            + str(error)
        )
        return None

    finally:
        if connection is not None:
            connection.close()


def create_incident(
    correlation,
    ai_analysis
):
    connection = None

    correlation_id = correlation[0]
    router = correlation[1]
    interface_name = correlation[2]
    correlation_type = correlation[3]
    severity = correlation[4]
    summary = correlation[5]

    incident_id = generate_incident_id()

    description = (
        "Telemetry correlation detected on "
        + router
        + " "
        + interface_name
        + ". "
        + summary
    )

    impact = ai_analysis[4]

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO incidents (
                    incident_id,
                    router,
                    incident_type,
                    status,
                    description,
                    impact,
                    health,
                    active_path,
                    default_next_hop,
                    source_type,
                    source_id
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    'OPEN',
                    %s,
                    %s,
                    'DEGRADED',
                    NULL,
                    NULL,
                    'TELEMETRY_CORRELATION',
                    %s
                )
                RETURNING id;
                """,
                (
                    incident_id,
                    router,
                    correlation_type,
                    description,
                    impact,
                    correlation_id
                )
            )

            incident_database_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO incident_evidence (
                    incident_id,
                    evidence_type,
                    evidence
                )
                VALUES (
                    %s,
                    'TELEMETRY_CORRELATION',
                    %s::jsonb
                );
                """,
                (
                    incident_database_id,
                    json.dumps(
                        {
                            "correlation_id": correlation_id,
                            "router": router,
                            "interface": interface_name,
                            "correlation_type": correlation_type,
                            "severity": severity,
                            "summary": summary
                        }
                    )
                )
            )

            cursor.execute(
                """
                INSERT INTO incident_evidence (
                    incident_id,
                    evidence_type,
                    evidence
                )
                VALUES (
                    %s,
                    'AI_TELEMETRY_ASSESSMENT',
                    %s::jsonb
                );
                """,
                (
                    incident_database_id,
                    json.dumps(
                        {
                            "analysis_id": ai_analysis[0],
                            "status": ai_analysis[1],
                            "assessment": ai_analysis[2],
                            "likely_explanation": ai_analysis[3],
                            "customer_impact": ai_analysis[4],
                            "risk": ai_analysis[5],
                            "confidence": ai_analysis[6],
                            "observed_evidence": ai_analysis[7],
                            "recommended_investigation": ai_analysis[8],
                            "assumptions": ai_analysis[9]
                        }
                    )
                )
            )

            cursor.execute(
                """
                INSERT INTO audit_events (
                    incident_id,
                    event_type,
                    actor,
                    details
                )
                VALUES (
                    %s,
                    'TELEMETRY_INCIDENT_CREATED',
                    'NETPILOT',
                    %s::jsonb
                );
                """,
                (
                    incident_database_id,
                    json.dumps(
                        {
                            "correlation_id": correlation_id,
                            "router": router,
                            "interface": interface_name,
                            "incident_type": correlation_type
                        }
                    )
                )
            )

        connection.commit()

        return {
            "action": "CREATED",
            "incident_id": incident_id,
            "database_id": incident_database_id
        }

    except Exception as error:
        connection.rollback()

        print(
            "Failed to create telemetry incident: "
            + str(error)
        )

        return None

    finally:
        connection.close()


def get_ai_analysis_for_correlation(
    correlation_id
):
    return get_existing_ai_analysis(
        correlation_id
    )


def process_correlation(correlation):
    correlation_id = correlation[0]

    existing = find_existing_incident(
        correlation_id
    )

    if existing is not None:
        return {
            "action": "EXISTS",
            "incident_id": existing[1],
            "database_id": existing[0],
            "status": existing[2]
        }

    ai_analysis = get_ai_analysis_for_correlation(
        correlation_id
    )

    if ai_analysis is None:
        print(
            "No persisted AI analysis exists for "
            "correlation "
            + str(correlation_id)
        )

        return {
            "action": "WAITING_FOR_AI",
            "correlation_id": correlation_id
        }

    return create_incident(
        correlation,
        ai_analysis
    )


def display_result(result):
    print()

    if result["action"] == "CREATED":
        print(
            "Incident created: "
            + result["incident_id"]
        )

        print(
            "Database ID: "
            + str(result["database_id"])
        )

    elif result["action"] == "EXISTS":
        print(
            "Incident already exists: "
            + result["incident_id"]
        )

        print(
            "Status: "
            + result["status"]
        )

    elif result["action"] == "WAITING_FOR_AI":
        print(
            "Waiting for AI analysis for correlation "
            + str(result["correlation_id"])
        )

    print()


def main():
    correlations = get_open_correlations()

    print()
    print("========================================")
    print("NETPILOT TELEMETRY INCIDENT INTEGRATION")
    print("========================================")
    print()

    print(
        "Open correlations: "
        + str(len(correlations))
    )

    created = 0
    existing = 0
    waiting = 0

    for correlation in correlations:
        print(
            "Processing correlation "
            + str(correlation[0])
        )

        result = process_correlation(
            correlation
        )

        if result is None:
            continue

        if result["action"] == "CREATED":
            created += 1

        elif result["action"] == "EXISTS":
            existing += 1

        elif result["action"] == "WAITING_FOR_AI":
            waiting += 1

        display_result(result)

    print("========================================")
    print("INTEGRATION SUMMARY")
    print("========================================")
    print()

    print(
        "Incidents created: "
        + str(created)
    )

    print(
        "Existing incidents: "
        + str(existing)
    )

    print(
        "Waiting for AI: "
        + str(waiting)
    )

    print()


if __name__ == "__main__":
    main()