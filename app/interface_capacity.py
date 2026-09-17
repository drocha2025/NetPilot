import re

from app.cisco_client import run_command
from app.database import get_connection


ROUTERS = ["R1", "R2", "R3", "R4", "R5"]


def parse_interface_capacity(output):
    interfaces = []
    current_interface = None

    for line in output.splitlines():
        interface_match = re.match(
            r"^(\S+) is (up|down|administratively down),",
            line
        )

        if interface_match:
            current_interface = interface_match.group(1)
            continue

        if current_interface is None:
            continue

        bandwidth_match = re.search(
            r"BW\s+(\d+)\s+Kbit/sec",
            line
        )

        if bandwidth_match:
            bandwidth_kbps = int(bandwidth_match.group(1))
            bandwidth_bps = bandwidth_kbps * 1000

            interfaces.append({
                "interface": current_interface,
                "bandwidth_bps": bandwidth_bps
            })

            current_interface = None

    return interfaces


def save_interface_capacity(router, interfaces):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            for interface in interfaces:
                cursor.execute(
                    """
                    INSERT INTO interface_capacity (
                        router,
                        interface_name,
                        bandwidth_bps,
                        source
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (router, interface_name)
                    DO UPDATE SET
                        bandwidth_bps = EXCLUDED.bandwidth_bps,
                        source = EXCLUDED.source,
                        collected_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        router,
                        interface["interface"],
                        interface["bandwidth_bps"],
                        "CISCO_SHOW_INTERFACES"
                    )
                )

        connection.commit()
        return True

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "Failed to save interface capacity for "
            + router
            + ": "
            + str(error)
        )

        return False

    finally:
        if connection is not None:
            connection.close()


def collect_router_capacity(router):
    print("Collecting interface capacity from " + router + "...")

    output = run_command(router, "show interfaces")

    if output is None:
        print("Unable to collect interface capacity from " + router + ".")
        return 0

    interfaces = parse_interface_capacity(output)

    if not interfaces:
        print("No interface capacity data found on " + router + ".")
        return 0

    if not save_interface_capacity(router, interfaces):
        return 0

    print(
        router
        + ": "
        + str(len(interfaces))
        + " interfaces stored."
    )

    return len(interfaces)


def display_summary(results):
    print()
    print("========================================")
    print("NETPILOT INTERFACE CAPACITY")
    print("========================================")
    print()

    total_interfaces = 0

    for router, count in results.items():
        print(
            router
            + " | Interfaces stored: "
            + str(count)
        )

        total_interfaces += count

    print()
    print(
        "Total interfaces stored: "
        + str(total_interfaces)
    )
    print()


def main():
    results = {}

    for router in ROUTERS:
        results[router] = collect_router_capacity(router)

    display_summary(results)


if __name__ == "__main__":
    main()