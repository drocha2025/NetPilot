from collections import defaultdict

from app.database import get_connection


def get_telemetry():
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    router,
                    interface_name,
                    input_packets,
                    output_packets,
                    input_errors,
                    output_errors,
                    collected_at
                FROM interface_telemetry
                ORDER BY router, interface_name, collected_at;
            """)

            return cursor.fetchall()

    except Exception as error:
        print("Telemetry database query failed: " + str(error))
        return []

    finally:
        if connection is not None:
            connection.close()


def group_samples(rows):
    samples = defaultdict(list)

    for row in rows:
        router = row[0]
        interface_name = row[1]

        samples[(router, interface_name)].append({
            "input_packets": row[2],
            "output_packets": row[3],
            "input_errors": row[4],
            "output_errors": row[5],
            "collected_at": row[6]
        })

    return samples


def calculate_deltas(samples):
    results = []

    for device, records in samples.items():
        router = device[0]
        interface_name = device[1]

        previous = None

        for current in records:
            if previous is None:
                previous = current
                continue

            elapsed_seconds = (
                current["collected_at"] - previous["collected_at"]
            ).total_seconds()

            input_delta = (
                current["input_packets"] -
                previous["input_packets"]
            )

            output_delta = (
                current["output_packets"] -
                previous["output_packets"]
            )

            input_error_delta = (
                current["input_errors"] -
                previous["input_errors"]
            )

            output_error_delta = (
                current["output_errors"] -
                previous["output_errors"]
            )

            counter_reset = (
                input_delta < 0
                or output_delta < 0
                or input_error_delta < 0
                or output_error_delta < 0
            )

            if counter_reset:
                input_delta = None
                output_delta = None
                input_packets_per_second = None
                output_packets_per_second = None
                input_error_delta = None
                output_error_delta = None
            elif elapsed_seconds > 0:
                input_packets_per_second = (
                    input_delta / elapsed_seconds
                )

                output_packets_per_second = (
                    output_delta / elapsed_seconds
                )
            else:
                input_packets_per_second = None
                output_packets_per_second = None

            results.append({
                "router": router,
                "interface_name": interface_name,
                "previous_time": previous["collected_at"],
                "current_time": current["collected_at"],
                "elapsed_seconds": elapsed_seconds,
                "input_delta": input_delta,
                "output_delta": output_delta,
                "input_packets_per_second": input_packets_per_second,
                "output_packets_per_second": output_packets_per_second,
                "input_error_delta": input_error_delta,
                "output_error_delta": output_error_delta,
                "counter_reset": counter_reset
            })

            previous = current

    return results


def display_results(results):
    print()
    print("========================================")
    print("NETPILOT TELEMETRY DELTA ANALYSIS")
    print("========================================")
    print()

    if not results:
        print("No telemetry history available.")
        print()
        return

    for result in results:
        print(
            result["router"]
            + " "
            + result["interface_name"]
        )

        print(
            "  Time: "
            + str(result["previous_time"])
            + " -> "
            + str(result["current_time"])
        )

        print(
            "  Elapsed seconds: "
            + format(result["elapsed_seconds"], ".2f")
        )

        if result["counter_reset"]:
            print("  Counter reset detected")
        else:
            print(
                "  Input packet delta: "
                + str(result["input_delta"])
            )

            print(
                "  Output packet delta: "
                + str(result["output_delta"])
            )

            print(
                "  Input packets/sec: "
                + format(
                    result["input_packets_per_second"],
                    ".2f"
                )
            )

            print(
                "  Output packets/sec: "
                + format(
                    result["output_packets_per_second"],
                    ".2f"
                )
            )

            print(
                "  Input error delta: "
                + str(result["input_error_delta"])
            )

            print(
                "  Output error delta: "
                + str(result["output_error_delta"])
            )

        print()


def main():
    rows = get_telemetry()

    if not rows:
        print("No telemetry records found.")
        return

    samples = group_samples(rows)
    results = calculate_deltas(samples)

    display_results(results)


if __name__ == "__main__":
    main()