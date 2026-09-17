from pathlib import Path

from app.cisco_client import run_command
from app.ai_drift import analyze_drift


ROUTERS = ["R1", "R2", "R3", "R4", "R5"]


def parse_interface_descriptions(configuration):
    """
    Extract interface descriptions from Cisco configuration.

    Returns:

    {
        "GigabitEthernet1": "description TO_ISP1",
        "GigabitEthernet2": "description TO_R2"
    }
    """

    interfaces = {}

    current_interface = None

    for raw_line in configuration.splitlines():

        line = raw_line.strip()

        if line.startswith("interface "):

            current_interface = line[len("interface "):].strip()

            interfaces[current_interface] = None

            continue

        if (
            current_interface
            and line.startswith("description ")
        ):

            interfaces[current_interface] = line

    return interfaces


def check_router(router):
    """
    Check one router against its golden configuration.
    """

    print()
    print("Checking " + router)

    golden_file = Path(
        f"data/golden/{router}.cfg"
    )

    if not golden_file.exists():

        return {
            "status": "UNKNOWN",
            "interface": "",
            "expected": "",
            "current": "",
            "diagnosis": ""
        }

    golden = golden_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    live = run_command(
        router,
        "show running-config"
    )

    if live is None:

        return {
            "status": "UNKNOWN",
            "interface": "",
            "expected": "",
            "current": "",
            "diagnosis": ""
        }

    golden_interfaces = parse_interface_descriptions(
        golden
    )

    live_interfaces = parse_interface_descriptions(
        live
    )

    all_interfaces = sorted(
        set(golden_interfaces)
        |
        set(live_interfaces)
    )

    for interface in all_interfaces:

        expected = golden_interfaces.get(interface)

        current = live_interfaces.get(interface)

        if expected != current:

            missing = []

            added = []

            if expected:
                missing.append(expected)

            if current:
                added.append(current)

            print(
                "Configuration drift detected."
            )

            print(
                "Detected interface: "
                + interface
            )

            print(
                "Expected: "
                + str(expected)
            )

            print(
                "Current: "
                + str(current)
            )

            try:

                diagnosis = analyze_drift(
                    router,
                    missing,
                    added
                )

            except Exception as error:

                diagnosis = (
                    "AI analysis unavailable: "
                    + str(error)
                )

            return {
                "status": "DRIFT",
                "interface": interface,
                "expected": expected or "",
                "current": current or "",
                "diagnosis": diagnosis
            }

    print(
        router + " is compliant"
    )

    return {
        "status": "COMPLIANT",
        "interface": "",
        "expected": "",
        "current": "",
        "diagnosis": ""
    }


def get_drift_status(router):
    """
    Public function used by the web dashboard.

    The dashboard should use this function instead
    of implementing its own drift detection.
    """

    return check_router(router)


if __name__ == "__main__":

    for router in ROUTERS:

        check_router(router)