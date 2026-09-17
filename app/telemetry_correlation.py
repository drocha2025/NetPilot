import json

from app.telemetry_anomaly_store import get_open_anomalies
from app.database import get_connection


def find_rate_correlations(anomalies):
    grouped = {}

    for anomaly in anomalies:
        anomaly_id = anomaly[0]
        router = anomaly[1]
        interface_name = anomaly[2]
        anomaly_type = anomaly[4]

        key = (router, interface_name)

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(
            {
                "id": anomaly_id,
                "type": anomaly_type
            }
        )

    correlations = []

    for key, findings in grouped.items():
        router = key[0]
        interface_name = key[1]

        has_input = False
        has_output = False
        anomaly_ids = []

        for finding in findings:
            if finding["type"] == "INPUT_RATE_ANOMALY":
                has_input = True
                anomaly_ids.append(finding["id"])

            elif finding["type"] == "OUTPUT_RATE_ANOMALY":
                has_output = True
                anomaly_ids.append(finding["id"])

        if has_input and has_output:
            correlations.append(
                {
                    "router": router,
                    "interface": interface_name,
                    "type": "TRAFFIC_RATE_ANOMALY",
                    "severity": "WARNING",
                    "summary": (
                        "Both input and output packet rates are "
                        "significantly above the historical baseline."
                    ),
                    "source_anomaly_ids": anomaly_ids
                }
            )

    return correlations


def find_existing_correlation(
    router,
    interface_name,
    correlation_type
):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    occurrence_count,
                    first_detected_at,
                    last_detected_at,
                    status
                FROM telemetry_correlations
                WHERE router = %s
                  AND interface_name = %s
                  AND correlation_type = %s
                ORDER BY id DESC
                LIMIT 1
                FOR UPDATE;
                """,
                (
                    router,
                    interface_name,
                    correlation_type
                )
            )

            return cursor.fetchone()

    except Exception as error:
        print(
            "Failed to find telemetry correlation: "
            + str(error)
        )

        return None

    finally:
        if connection is not None:
            connection.close()


def save_or_update_correlation(correlation):
    connection = None

    try:
        connection = get_connection()

        existing = find_existing_correlation(
            correlation["router"],
            correlation["interface"],
            correlation["type"]
        )

        source_anomaly_ids_json = json.dumps(
            correlation["source_anomaly_ids"]
        )

        with connection.cursor() as cursor:
            if existing is not None:
                correlation_id = existing[0]
                occurrence_count = existing[1] + 1
                previous_status = existing[4]

                if previous_status == "RESOLVED":
                    action = "REOPENED"
                else:
                    action = "UPDATED"

                cursor.execute(
                    """
                    UPDATE telemetry_correlations
                    SET
                        severity = %s,
                        summary = %s,
                        source_anomaly_ids = %s::jsonb,
                        last_detected_at = CURRENT_TIMESTAMP,
                        occurrence_count = %s,
                        status = 'ONGOING',
                        resolved_at = NULL
                    WHERE id = %s;
                    """,
                    (
                        correlation["severity"],
                        correlation["summary"],
                        source_anomaly_ids_json,
                        occurrence_count,
                        correlation_id
                    )
                )

                connection.commit()

                return {
                    "id": correlation_id,
                    "action": action,
                    "occurrence_count": occurrence_count
                }

            cursor.execute(
                """
                INSERT INTO telemetry_correlations (
                    router,
                    interface_name,
                    correlation_type,
                    severity,
                    summary,
                    source_anomaly_ids,
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    status
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::jsonb,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    1,
                    'OPEN'
                )
                RETURNING id;
                """,
                (
                    correlation["router"],
                    correlation["interface"],
                    correlation["type"],
                    correlation["severity"],
                    correlation["summary"],
                    source_anomaly_ids_json
                )
            )

            correlation_id = cursor.fetchone()[0]

        connection.commit()

        return {
            "id": correlation_id,
            "action": "CREATED",
            "occurrence_count": 1
        }

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "Failed to save telemetry correlation: "
            + str(error)
        )

        return None

    finally:
        if connection is not None:
            connection.close()


def resolve_missing_correlations(active_correlations):
    connection = None

    active_keys = set()

    for correlation in active_correlations:
        active_keys.add(
            (
                correlation["router"],
                correlation["interface"],
                correlation["type"]
            )
        )

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    router,
                    interface_name,
                    correlation_type
                FROM telemetry_correlations
                WHERE status IN ('OPEN', 'ONGOING');
                """
            )

            open_correlations = cursor.fetchall()

            resolved = 0

            for correlation in open_correlations:
                correlation_id = correlation[0]

                key = (
                    correlation[1],
                    correlation[2],
                    correlation[3]
                )

                if key not in active_keys:
                    cursor.execute(
                        """
                        UPDATE telemetry_correlations
                        SET
                            status = 'RESOLVED',
                            resolved_at = CURRENT_TIMESTAMP
                        WHERE id = %s;
                        """,
                        (correlation_id,)
                    )

                    resolved += 1

        connection.commit()

        return resolved

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "Failed to resolve telemetry correlations: "
            + str(error)
        )

        return 0

    finally:
        if connection is not None:
            connection.close()


def get_open_correlations():
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
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    status
                FROM telemetry_correlations
                WHERE status IN ('OPEN', 'ONGOING')
                ORDER BY last_detected_at DESC;
                """
            )

            return cursor.fetchall()

    except Exception as error:
        print(
            "Failed to retrieve telemetry correlations: "
            + str(error)
        )

        return []

    finally:
        if connection is not None:
            connection.close()


def display_correlations(correlations):
    print()
    print("========================================")
    print("NETPILOT TELEMETRY CORRELATIONS")
    print("========================================")
    print()

    if not correlations:
        print("No open telemetry correlations.")
        print()
        return

    print(
        "Open correlations: "
        + str(len(correlations))
    )

    print()

    for correlation in correlations:
        print("ID: " + str(correlation[0]))

        print(
            "Device: "
            + correlation[1]
            + " "
            + correlation[2]
        )

        print("Type: " + correlation[3])
        print("Severity: " + correlation[4])
        print("Summary: " + correlation[5])

        print(
            "First detected: "
            + str(correlation[6])
        )

        print(
            "Last detected: "
            + str(correlation[7])
        )

        print(
            "Occurrences: "
            + str(correlation[8])
        )

        print("Status: " + correlation[9])
        print()


def main():
    anomalies = get_open_anomalies()

    correlations = find_rate_correlations(
        anomalies
    )

    created = 0
    updated = 0
    reopened = 0

    for correlation in correlations:
        result = save_or_update_correlation(
            correlation
        )

        if result is None:
            continue

        if result["action"] == "CREATED":
            created += 1

        elif result["action"] == "UPDATED":
            updated += 1

        elif result["action"] == "REOPENED":
            reopened += 1

    resolved = resolve_missing_correlations(
        correlations
    )

    print()
    print("========================================")
    print("NETPILOT CORRELATION ENGINE")
    print("========================================")
    print()

    print(
        "Open anomalies examined: "
        + str(len(anomalies))
    )

    print(
        "Correlations detected: "
        + str(len(correlations))
    )

    print(
        "New correlations: "
        + str(created)
    )

    print(
        "Existing correlations updated: "
        + str(updated)
    )

    print(
        "Correlations reopened: "
        + str(reopened)
    )

    print(
        "Correlations resolved: "
        + str(resolved)
    )

    print()

    display_correlations(
        get_open_correlations()
    )


if __name__ == "__main__":
    main()