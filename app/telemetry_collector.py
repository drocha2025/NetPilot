import re

from app.cisco_client import run_command
from app.database import get_connection


TELEMETRY_INTERFACES = {
    "R1": [
        "GigabitEthernet1",
        "GigabitEthernet3",
    ],
    "R2": [
        "GigabitEthernet1",
        "GigabitEthernet2",
    ],
    "R3": [
        "GigabitEthernet2",
        "GigabitEthernet3",
    ],
}


def parse_rate(value):
    if not value:
        return None

    value = value.lower().replace(",", "").strip()

    match = re.search(
        r"(\d+)\s+(bits/sec|bytes/sec)",
        value
    )

    if not match:
        return None

    number = int(match.group(1))
    unit = match.group(2)

    if unit == "bytes/sec":
        return number * 8

    return number


def parse_counter(output, pattern):
    match = re.search(
        pattern,
        output,
        re.IGNORECASE
    )

    if not match:
        return None

    return int(match.group(1).replace(",", ""))


def parse_interface_telemetry(output):
    first_line = output.splitlines()[0] if output else ""

    status_match = re.search(
        r"is\s+(\w+),\s+line protocol is\s+(\w+)",
        first_line,
        re.IGNORECASE
    )

    interface_status = None
    protocol_status = None

    if status_match:
        interface_status = status_match.group(1)
        protocol_status = status_match.group(2)

    input_rate_match = re.search(
        r"input rate\s+(.+)",
        output,
        re.IGNORECASE
    )

    output_rate_match = re.search(
        r"output rate\s+(.+)",
        output,
        re.IGNORECASE
    )

    input_rate = None
    output_rate = None

    if input_rate_match:
        input_rate = parse_rate(
            input_rate_match.group(1)
        )

    if output_rate_match:
        output_rate = parse_rate(
            output_rate_match.group(1)
        )

    return {
        "interface_status": interface_status,
        "protocol_status": protocol_status,
        "input_rate_bps": input_rate,
        "output_rate_bps": output_rate,
        "input_packets": parse_counter(
            output,
            r"(\d[\d,]*)\s+packets input"
        ),
        "output_packets": parse_counter(
            output,
            r"(\d[\d,]*)\s+packets output"
        ),
        "input_errors": parse_counter(
            output,
            r"(\d[\d,]*)\s+input errors"
        ),
        "output_errors": parse_counter(
            output,
            r"(\d[\d,]*)\s+output errors"
        ),
    }


def collect_interface_telemetry(router, interface_name):
    command = (
        "show interfaces "
        + interface_name
    )

    output = run_command(
        router,
        command
    )

    if output is None:
        return {
            "status": "OFFLINE",
            "router": router,
            "interface_name": interface_name,
        }

    telemetry = parse_interface_telemetry(output)

    telemetry["status"] = "COLLECTED"
    telemetry["router"] = router
    telemetry["interface_name"] = interface_name

    return telemetry


def store_interface_telemetry(telemetry):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
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
                    output_errors
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    telemetry["router"],
                    telemetry["interface_name"],
                    telemetry.get("interface_status"),
                    telemetry.get("protocol_status"),
                    telemetry.get("input_rate_bps"),
                    telemetry.get("output_rate_bps"),
                    telemetry.get("input_packets"),
                    telemetry.get("output_packets"),
                    telemetry.get("input_errors"),
                    telemetry.get("output_errors"),
                )
            )

        connection.commit()

        return {
            "status": "STORED"
        }

    except Exception as error:
        if connection is not None:
            connection.rollback()

        return {
            "status": "FAILED",
            "error": str(error)
        }

    finally:
        if connection is not None:
            connection.close()


def collect_all_telemetry():
    results = []

    for router, interfaces in TELEMETRY_INTERFACES.items():
        for interface_name in interfaces:
            print()
            print(
                "Collecting telemetry from "
                + router
                + " "
                + interface_name
            )

            telemetry = collect_interface_telemetry(
                router,
                interface_name
            )

            if telemetry["status"] == "COLLECTED":
                result = store_interface_telemetry(
                    telemetry
                )

                print(
                    "Storage status: "
                    + result["status"]
                )

            else:
                result = telemetry
                print("Collection failed.")

            results.append(result)

    return results


if __name__ == "__main__":
    results = collect_all_telemetry()

    print()
    print("========================================")
    print("NETPILOT TELEMETRY COLLECTION")
    print("========================================")
    print()

    print(
        "Records processed: "
        + str(len(results))
    )