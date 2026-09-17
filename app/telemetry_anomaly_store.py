from app.database import get_connection


def find_open_anomaly(
    router,
    interface_name,
    anomaly_type
):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    occurrence_count
                FROM telemetry_anomalies
                WHERE router = %s
                  AND interface_name = %s
                  AND anomaly_type = %s
                  AND status IN ('OPEN', 'ONGOING')
                ORDER BY id DESC
                LIMIT 1;
                """,
                (
                    router,
                    interface_name,
                    anomaly_type
                )
            )

            return cursor.fetchone()

    except Exception as error:
        print(
            "Failed to find telemetry anomaly: "
            + str(error)
        )
        return None

    finally:
        if connection is not None:
            connection.close()


def save_or_update_anomaly(
    router,
    interface_name,
    severity,
    anomaly_type,
    message,
    detected_at
):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:

            # Find the existing lifecycle record regardless
            # of whether the anomaly is currently open or resolved.
            #
            # This prevents repeated detections of the same
            # anomaly from creating unnecessary historical rows.
            cursor.execute(
                """
                SELECT
                    id,
                    occurrence_count,
                    first_detected_at,
                    last_detected_at,
                    status
                FROM telemetry_anomalies
                WHERE router = %s
                  AND interface_name = %s
                  AND anomaly_type = %s
                ORDER BY id DESC
                LIMIT 1
                FOR UPDATE;
                """,
                (
                    router,
                    interface_name,
                    anomaly_type
                )
            )

            existing = cursor.fetchone()

            if existing is not None:
                anomaly_id = existing[0]
                occurrence_count = existing[1]
                first_detected_at = existing[2]
                last_detected_at = existing[3]
                previous_status = existing[4]

                occurrence_count += 1

                # Keep the earliest timestamp as first_detected_at.
                if (
                    first_detected_at is None
                    or detected_at < first_detected_at
                ):
                    new_first_detected_at = detected_at
                else:
                    new_first_detected_at = first_detected_at

                # Keep the latest timestamp as last_detected_at.
                if (
                    last_detected_at is None
                    or detected_at > last_detected_at
                ):
                    new_last_detected_at = detected_at
                else:
                    new_last_detected_at = last_detected_at

                cursor.execute(
                    """
                    UPDATE telemetry_anomalies
                    SET
                        severity = %s,
                        message = %s,
                        first_detected_at = %s,
                        last_detected_at = %s,
                        occurrence_count = %s,
                        status = 'ONGOING',
                        resolved_at = NULL
                    WHERE id = %s;
                    """,
                    (
                        severity,
                        message,
                        new_first_detected_at,
                        new_last_detected_at,
                        occurrence_count,
                        anomaly_id
                    )
                )

                connection.commit()

                if previous_status == "RESOLVED":
                    action = "REOPENED"
                else:
                    action = "UPDATED"

                return {
                    "id": anomaly_id,
                    "action": action,
                    "occurrence_count": occurrence_count
                }

            # No previous lifecycle record exists.
            cursor.execute(
                """
                INSERT INTO telemetry_anomalies (
                    router,
                    interface_name,
                    severity,
                    anomaly_type,
                    message,
                    detected_at,
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    status,
                    resolved_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    1,
                    'OPEN',
                    NULL
                )
                RETURNING id;
                """,
                (
                    router,
                    interface_name,
                    severity,
                    anomaly_type,
                    message,
                    detected_at,
                    detected_at,
                    detected_at
                )
            )

            anomaly_id = cursor.fetchone()[0]

        connection.commit()

        return {
            "id": anomaly_id,
            "action": "CREATED",
            "occurrence_count": 1
        }

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "Failed to save telemetry anomaly: "
            + str(error)
        )
        return None

    finally:
        if connection is not None:
            connection.close()


def resolve_missing_anomalies(active_findings):
    connection = None

    active_keys = set()

    for finding in active_findings:
        active_keys.add(
            (
                finding["router"],
                finding["interface"],
                finding["type"]
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
                    anomaly_type
                FROM telemetry_anomalies
                WHERE status IN ('OPEN', 'ONGOING');
                """
            )

            open_anomalies = cursor.fetchall()

            resolved = 0

            for anomaly in open_anomalies:
                anomaly_id = anomaly[0]
                router = anomaly[1]
                interface_name = anomaly[2]
                anomaly_type = anomaly[3]

                key = (
                    router,
                    interface_name,
                    anomaly_type
                )

                if key not in active_keys:
                    cursor.execute(
                        """
                        UPDATE telemetry_anomalies
                        SET
                            status = 'RESOLVED',
                            resolved_at = CURRENT_TIMESTAMP
                        WHERE id = %s;
                        """,
                        (anomaly_id,)
                    )

                    resolved += 1

        connection.commit()

        return resolved

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "Failed to resolve telemetry anomalies: "
            + str(error)
        )
        return 0

    finally:
        if connection is not None:
            connection.close()


def get_open_anomalies():
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
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    status
                FROM telemetry_anomalies
                WHERE status IN ('OPEN', 'ONGOING')
                ORDER BY last_detected_at DESC;
                """
            )

            return cursor.fetchall()

    except Exception as error:
        print(
            "Failed to retrieve telemetry anomalies: "
            + str(error)
        )
        return []

    finally:
        if connection is not None:
            connection.close()


def display_open_anomalies(anomalies):
    print()
    print("========================================")
    print("NETPILOT OPEN TELEMETRY ANOMALIES")
    print("========================================")
    print()

    if not anomalies:
        print("No open telemetry anomalies.")
        print()
        return

    print(
        "Open anomalies: "
        + str(len(anomalies))
    )
    print()

    for anomaly in anomalies:
        print(
            "ID: "
            + str(anomaly[0])
        )

        print(
            "Device: "
            + anomaly[1]
            + " "
            + anomaly[2]
        )

        print(
            "Severity: "
            + anomaly[3]
        )

        print(
            "Type: "
            + anomaly[4]
        )

        print(
            "Message: "
            + anomaly[5]
        )

        print(
            "First detected: "
            + str(anomaly[6])
        )

        print(
            "Last detected: "
            + str(anomaly[7])
        )

        print(
            "Occurrences: "
            + str(anomaly[8])
        )

        print(
            "Status: "
            + anomaly[9]
        )

        print()


if __name__ == "__main__":
    anomalies = get_open_anomalies()
    display_open_anomalies(anomalies)