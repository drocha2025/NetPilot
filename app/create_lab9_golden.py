from pathlib import Path

from app.cisco_client import run_command


ROUTERS = ["R1", "R2", "R3", "R4", "R5"]


def create_golden_configuration(router):
    print()
    print("Creating golden configuration for " + router)

    output = run_command(
        router,
        "show running-config"
    )

    if output is None:
        print(
            "Could not retrieve configuration from "
            + router
        )
        return False

    golden_directory = Path("data/golden")
    golden_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    golden_file = golden_directory / (
        router + ".cfg"
    )

    golden_file.write_text(
        output,
        encoding="utf-8"
    )

    print(
        "Golden configuration saved: "
        + str(golden_file)
    )

    return True


def main():
    print()
    print("========================================")
    print("NETPILOT LAB 9 GOLDEN CONFIGURATION")
    print("========================================")

    success = 0

    for router in ROUTERS:

        if create_golden_configuration(router):
            success += 1

    print()
    print("Golden configurations created: "
          + str(success)
          + "/"
          + str(len(ROUTERS)))

    print()


if __name__ == "__main__":
    main()