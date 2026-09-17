from collections import defaultdict

from app.database import get_connection


PACKET_RATE_CHANGE_THRESHOLD = 3.0
ERROR_THRESHOLD = 1


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


def calculate_packet_rate(previous, current):
    elapsed_seconds = (
        current["collected_at"] -
        previous["collected_at"]
    ).total_seconds()

    if elapsed_seconds <= 0:
        return None, None, elapsed_seconds

    input_delta = (
        current["input_packets"] -
        previous["input_packets"]
    )

    output_delta = (
        current["output_packets"] -
        previous["output_packets"]
    )

    if input_delta < 0 or output_delta < 0:
        return None, None, elapsed_seconds

    input_rate = input_delta / elapsed_seconds
    output_rate = output_delta / elapsed_seconds

    return input_rate, output_rate, elapsed_seconds


def calculate_error_delta(previous, current):
    input_error_delta = (
        current["input_errors"] -
        previous["input_errors"]
    )

    output_error_delta = (
        current["output_errors"] -
        previous["output_errors"]
    )

    return input_error_delta, output_error_delta


def analyze_interface(router, interface_name, records):
    findings = []

    if len(records) < 2:
        return findings

    packet_rates = []

    previous = None

    for current in records:
        if previous is None:
            previous = current
            continue

        input_rate, output_rate, elapsed_seconds = (
            calculate_packet_rate(previous, current)
        )

        input_error_delta, output_error_delta = (
            calculate_error_delta(previous, current)
        )

        if input_rate is None or output_rate is None:
            findings.append({
                "router": router,
                "interface": interface_name,
                "severity": "WARNING",
                "type": "COUNTER_RESET",
                "message": "Packet counter decreased between samples.",
                "timestamp": current["collected_at"]
            })

            previous = current
            continue

        packet_rates.append({
            "input_rate": input_rate,
            "output_rate": output_rate,
            "timestamp": current["collected_at"]
        })

        if (
            input_error_delta >= ERROR_THRESHOLD
            or output_error_delta >= ERROR_THRESHOLD
        ):
            findings.append({
                "router": router,
                "interface": interface_name,
                "severity": "CRITICAL",
                "type": "INTERFACE_ERRORS",
                "message": (
                    "New interface errors detected. "
                    "Input errors: "
                    + str(input_error_delta)
                    + ", Output errors: "
                    + str(output_error_delta)
                ),
                "timestamp": current["collected_at"]
            })

        previous = current

    if len(packet_rates) < 2:
        return findings

    baseline_input = sum(
        sample["input_rate"]
        for sample in packet_rates[:-1]
    ) / len(packet_rates[:-1])

    baseline_output = sum(
        sample["output_rate"]
        for sample in packet_rates[:-1]
    ) / len(packet_rates[:-1])

    latest = packet_rates[-1]

    if baseline_input > 0:
        input_ratio = latest["input_rate"] / baseline_input

        if input_ratio >= PACKET_RATE_CHANGE_THRESHOLD:
            findings.append({
                "router": router,
                "interface": interface_name,
                "severity": "WARNING",
                "type": "INPUT_RATE_ANOMALY",
                "message": (
                    "Input packet rate is "
                    + format(input_ratio, ".2f")
                    + "x the historical baseline."
                ),
                "timestamp": latest["timestamp"]
            })

    if baseline_output > 0:
        output_ratio = latest["output_rate"] / baseline_output

        if output_ratio >= PACKET_RATE_CHANGE_THRESHOLD:
            findings.append({
                "router": router,
                "interface": interface_name,
                "severity": "WARNING",
                "type": "OUTPUT_RATE_ANOMALY",
                "message": (
                    "Output packet rate is "
                    + format(output_ratio, ".2f")
                    + "x the historical baseline."
                ),
                "timestamp": latest["timestamp"]
            })

    return findings


def analyze_all_interfaces(samples):
    findings = []

    for device, records in samples.items():
        router = device[0]
        interface_name = device[1]

        interface_findings = analyze_interface(
            router,
            interface_name,
            records
        )

        findings.extend(interface_findings)

    return findings


def display_findings(findings):
    print()
    print("========================================")
    print("NETPILOT TELEMETRY ANOMALY DETECTION")
    print("========================================")
    print()

    if not findings:
        print("No anomalies detected.")
        print()
        return

    print("Anomalies detected: " + str(len(findings)))
    print()

    for finding in findings:
        print(
            finding["severity"]
            + " | "
            + finding["router"]
            + " "
            + finding["interface"]
        )

        print("Type: " + finding["type"])
        print("Message: " + finding["message"])
        print("Time: " + str(finding["timestamp"]))
        print()


def main():
    rows = get_telemetry()

    if not rows:
        print("No telemetry records found.")
        return

    samples = group_samples(rows)

    findings = analyze_all_interfaces(samples)

    display_findings(findings)


if __name__ == "__main__":
    main()