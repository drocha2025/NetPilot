from app.database import get_connection
from app.telemetry_correlation import get_open_correlations


def get_telemetry_incidents():
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
                    source_type,
                    source_id
                FROM incidents
                WHERE source_type = 'TELEMETRY_CORRELATION'
                ORDER BY id;
                """
            )

            return cursor.fetchall()

    except Exception as error:
        print(
            "Failed to retrieve telemetry incidents: "
            + str(error)
        )

        return []

    finally:
        if connection is not None:
            connection.close()


def get_incident_by_correlation(
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
                    router,
                    incident_type,
                    status,
                    health,
                    source_type,
                    source_id
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
            "Failed to retrieve telemetry incident: "
            + str(error)
        )

        return None

    finally:
        if connection is not None:
            connection.close()


def update_active_incident(
    incident,
    correlation
):
    connection = None

    incident_database_id = incident[0]

    router = correlation[1]
    interface_name = correlation[2]
    correlation_type = correlation[3]
    severity = correlation[4]
    summary = correlation[5]

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE incidents
                SET
                    status = 'OPEN',
                    health = 'DEGRADED',
                    description = %s,
                    updated_at = CURRENT_TIMESTAMP,
                    resolved_at = NULL
                WHERE id = %s
                  AND status <> 'RESOLVED';
                """,
                (
                    (
                        "Telemetry correlation remains active on "
                        + router
                        + " "
                        + interface_name
                        + ". "
                        + summary
                    ),
                    incident_database_id
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
                    'TELEMETRY_INCIDENT_UPDATED',
                    'NETPILOT',
                    %s::jsonb
                );
                """,
                (
                    incident_database_id,
                    (
                        '{"correlation_id": '
                        + str(correlation[0])
                        + ', "router": "'
                        + router
                        + '", "interface": "'
                        + interface_name
                        + '", "severity": "'
                        + severity
                        + '", "correlation_type": "'
                        + correlation_type
                        + '"}'
                    )
                )
            )

        connection.commit()

        return True

    except Exception as error:
        connection.rollback()

        print(
            "Failed to update telemetry incident: "
            + str(error)
        )

        return False

    finally:
        connection.close()


def resolve_incident(
    incident,
    correlation_id
):
    connection = None

    incident_database_id = incident[0]
    incident_id = incident[1]

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE incidents
                SET
                    status = 'RESOLVED',
                    health = 'HEALTHY',
                    resolved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status <> 'RESOLVED';
                """,
                (incident_database_id,)
            )

            if cursor.rowcount == 0:
                connection.commit()

                return {
                    "action": "ALREADY_RESOLVED",
                    "incident_id": incident_id
                }

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
                    'TELEMETRY_INCIDENT_RESOLVED',
                    'NETPILOT',
                    %s::jsonb
                );
                """,
                (
                    incident_database_id,
                    (
                        '{"correlation_id": '
                        + str(correlation_id)
                        + ', "resolution_reason": '
                        + '"telemetry correlation resolved"}'
                    )
                )
            )

        connection.commit()

        return {
            "action": "RESOLVED",
            "incident_id": incident_id
        }

    except Exception as error:
        connection.rollback()

        print(
            "Failed to resolve telemetry incident: "
            + str(error)
        )

        return None

    finally:
        connection.close()


def synchronize_incidents():
    open_correlations = get_open_correlations()

    active_correlation_ids = set()

    for correlation in open_correlations:
        active_correlation_ids.add(
            correlation[0]
        )

    incidents = get_telemetry_incidents()

    updated = 0
    resolved = 0
    already_resolved = 0
    skipped = 0

    for incident in incidents:
        correlation_id = incident[7]

        if correlation_id in active_correlation_ids:
            correlation = None

            for open_correlation in open_correlations:
                if open_correlation[0] == correlation_id:
                    correlation = open_correlation
                    break

            if correlation is None:
                skipped += 1
                continue

            result = update_active_incident(
                incident,
                correlation
            )

            if result:
                updated += 1

        else:
            result = resolve_incident(
                incident,
                correlation_id
            )

            if result is None:
                continue

            if result["action"] == "RESOLVED":
                resolved += 1

            elif result["action"] == "ALREADY_RESOLVED":
                already_resolved += 1

    return {
        "open_correlations": len(
            open_correlations
        ),
        "telemetry_incidents": len(
            incidents
        ),
        "updated": updated,
        "resolved": resolved,
        "already_resolved": already_resolved,
        "skipped": skipped
    }


def display_summary(result):
    print()
    print("========================================")
    print("NETPILOT TELEMETRY INCIDENT SYNC")
    print("========================================")
    print()

    print(
        "Open correlations: "
        + str(result["open_correlations"])
    )

    print(
        "Telemetry incidents: "
        + str(result["telemetry_incidents"])
    )

    print(
        "Incidents updated: "
        + str(result["updated"])
    )

    print(
        "Incidents resolved: "
        + str(result["resolved"])
    )

    print(
        "Already resolved: "
        + str(result["already_resolved"])
    )

    print(
        "Skipped: "
        + str(result["skipped"])
    )

    print()


def main():
    result = synchronize_incidents()

    display_summary(result)


if __name__ == "__main__":
    main()