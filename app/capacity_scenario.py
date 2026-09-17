import sys
from datetime import datetime, timedelta, timezone

from app.database import get_connection


SCENARIO_ROUTER = "R1"

SCENARIO_INTERFACE = "GigabitEthernet1"

SCENARIO_CAPACITY_BPS = 1000000000

NUMBER_OF_SAMPLES = 11

HISTORICAL_DAYS = 30

START_UTILIZATION_PERCENT = 50.0

END_UTILIZATION_PERCENT = 62.5


def generate_scenario_samples():
    """
    Generate a controlled 30-day capacity-growth scenario.

    The scenario represents a 1 Gbps interface increasing
    from 50% utilization to 62.5% utilization.

    This is synthetic lab data.

    No Cisco configuration is changed.
    """

    samples = []

    now = datetime.now(
        timezone.utc
    )

    interval_days = (
        HISTORICAL_DAYS
        / (
            NUMBER_OF_SAMPLES
            - 1
        )
    )

    utilization_step = (
        END_UTILIZATION_PERCENT
        - START_UTILIZATION_PERCENT
    ) / (
        NUMBER_OF_SAMPLES
        - 1
    )

    for index in range(
        NUMBER_OF_SAMPLES
    ):

        days_ago = (
            HISTORICAL_DAYS
            - (
                index
                * interval_days
            )
        )

        collected_at = (
            now
            - timedelta(
                days=days_ago
            )
        )

        utilization_percent = (
            START_UTILIZATION_PERCENT
            + (
                index
                * utilization_step
            )
        )

        utilization_bps = int(
            SCENARIO_CAPACITY_BPS
            * (
                utilization_percent
                / 100.0
            )
        )

        samples.append(
            {
                "router":
                    SCENARIO_ROUTER,

                "interface":
                    SCENARIO_INTERFACE,

                "input_rate_bps":
                    utilization_bps,

                "output_rate_bps":
                    utilization_bps,

                "collected_at":
                    collected_at
            }
        )

    return samples


def clear_interface_history():
    """
    Remove all telemetry history for the scenario interface.

    This is intentionally limited to R1 GigabitEthernet1.

    The purpose is to create an isolated dataset for the
    controlled capacity-growth test.

    Other routers and interfaces are not modified.
    """

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM interface_telemetry
                WHERE router = %s
                  AND interface_name = %s;
                """,
                (
                    SCENARIO_ROUTER,
                    SCENARIO_INTERFACE
                )
            )

            deleted_rows = cursor.rowcount

        connection.commit()

        print(
            "Existing telemetry history removed for "
            + SCENARIO_ROUTER
            + " "
            + SCENARIO_INTERFACE
            + ": "
            + str(
                deleted_rows
            )
        )

        return True

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "Failed to clear interface history: "
            + str(error)
        )

        return False

    finally:

        if connection is not None:
            connection.close()


def apply_scenario():
    """
    Replace the R1 GigabitEthernet1 telemetry history
    with the controlled capacity-growth scenario.
    """

    print()
    print(
        "Preparing isolated capacity scenario..."
    )

    if not clear_interface_history():

        return False

    samples = generate_scenario_samples()

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            for sample in samples:

                cursor.execute(
                    """
                    INSERT INTO interface_telemetry (
                        router,
                        interface_name,
                        interface_status,
                        protocol_status,
                        input_rate_bps,
                        output_rate_bps,
                        input_packets,
                        output_packets,
                        input_errors,
                        output_errors,
                        collected_at
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
                        %s,
                        %s,
                        %s
                    );
                    """,
                    (
                        sample["router"],
                        sample["interface"],
                        "up",
                        "up",
                        sample[
                            "input_rate_bps"
                        ],
                        sample[
                            "output_rate_bps"
                        ],
                        0,
                        0,
                        0,
                        0,
                        sample[
                            "collected_at"
                        ]
                    )
                )

        connection.commit()

        print()
        print(
            "========================================"
        )

        print(
            "CAPACITY GROWTH SCENARIO APPLIED"
        )

        print(
            "========================================"
        )

        print()

        print(
            "Router: "
            + SCENARIO_ROUTER
        )

        print(
            "Interface: "
            + SCENARIO_INTERFACE
        )

        print(
            "Capacity: 1000 Mbps"
        )

        print(
            "Historical Window: "
            + str(
                HISTORICAL_DAYS
            )
            + " days"
        )

        print(
            "Starting Utilization: "
            + str(
                START_UTILIZATION_PERCENT
            )
            + "%"
        )

        print(
            "Ending Utilization: "
            + str(
                END_UTILIZATION_PERCENT
            )
            + "%"
        )

        print(
            "Samples Inserted: "
            + str(
                len(samples)
            )
        )

        print()

        return True

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "Failed to apply capacity scenario: "
            + str(error)
        )

        return False

    finally:

        if connection is not None:
            connection.close()


def display_scenario_data():
    """
    Display the isolated scenario dataset.
    """

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    router,
                    interface_name,
                    input_rate_bps,
                    output_rate_bps,
                    collected_at
                FROM interface_telemetry
                WHERE router = %s
                  AND interface_name = %s
                ORDER BY collected_at;
                """,
                (
                    SCENARIO_ROUTER,
                    SCENARIO_INTERFACE
                )
            )

            rows = cursor.fetchall()

        print()
        print(
            "========================================"
        )

        print(
            "CAPACITY GROWTH SCENARIO DATA"
        )

        print(
            "========================================"
        )

        print()

        if not rows:

            print(
                "No scenario data found."
            )

            print()

            return

        print(
            "Samples: "
            + str(
                len(rows)
            )
        )

        print()

        for row in rows:

            (
                router,
                interface_name,
                input_rate_bps,
                output_rate_bps,
                collected_at
            ) = row

            input_utilization = (
                input_rate_bps
                / SCENARIO_CAPACITY_BPS
                * 100.0
            )

            output_utilization = (
                output_rate_bps
                / SCENARIO_CAPACITY_BPS
                * 100.0
            )

            print(
                str(
                    collected_at
                )
            )

            print(
                "  "
                + router
                + " "
                + interface_name
            )

            print(
                "  Input: "
                + str(
                    round(
                        input_utilization,
                        2
                    )
                )
                + "%"
            )

            print(
                "  Output: "
                + str(
                    round(
                        output_utilization,
                        2
                    )
                )
                + "%"
            )

            print()

    except Exception as error:

        print(
            "Failed to display scenario data: "
            + str(error)
        )

    finally:

        if connection is not None:
            connection.close()


def clear_scenario():
    """
    Remove the scenario interface telemetry.

    The regular telemetry workflow can then repopulate
    R1 GigabitEthernet1 with real Cisco telemetry.
    """

    return clear_interface_history()


def main():
    """
    Run the requested scenario operation.

    Supported commands:

        apply
        show
        clear
    """

    if len(sys.argv) < 2:

        print()
        print(
            "Usage:"
        )

        print(
            "  python -m app.capacity_scenario apply"
        )

        print(
            "  python -m app.capacity_scenario show"
        )

        print(
            "  python -m app.capacity_scenario clear"
        )

        print()

        return

    command = sys.argv[1].lower()

    if command == "apply":

        apply_scenario()

    elif command == "show":

        display_scenario_data()

    elif command == "clear":

        if clear_scenario():

            print(
                "Scenario telemetry cleared."
            )

        print()

    else:

        print(
            "Unknown command: "
            + command
        )

        print()

        print(
            "Valid commands: apply, show, clear"
        )

        print()


if __name__ == "__main__":

    main()
