from netmiko import ConnectHandler
import time


DEVICES = {
    "R1": {
        "device_type": "cisco_ios",
        "host": "192.168.1.201",
        "username": "netpilot",
        "password": "Cisco123!",
        "port": 22,
    },
    "R2": {
        "device_type": "cisco_ios",
        "host": "192.168.1.202",
        "username": "netpilot",
        "password": "Cisco123!",
        "port": 22,
    },
    "R3": {
        "device_type": "cisco_ios",
        "host": "192.168.1.203",
        "username": "netpilot",
        "password": "Cisco123!",
        "port": 22,
    },
    "R4": {
        "device_type": "cisco_ios",
        "host": "192.168.1.204",
        "username": "netpilot",
        "password": "Cisco123!",
        "port": 22,
    },
    "R5": {
        "device_type": "cisco_ios",
        "host": "192.168.1.205",
        "username": "netpilot",
        "password": "Cisco123!",
        "port": 22,
    },
}


def connect_to_router(device_name):
    """
    Establish an SSH connection to a Cisco device.

    Retries up to three times before returning None.
    """

    if device_name not in DEVICES:
        print(
            "Unknown device: "
            + device_name
        )
        return None

    device = DEVICES[device_name]

    print(
        "Connecting to "
        + device_name
        + "..."
    )

    for attempt in range(1, 4):

        try:

            connection = ConnectHandler(
                **device
            )

            print(
                device_name
                + " connected!"
            )

            return connection

        except Exception as error:

            print(
                device_name
                + " connection attempt "
                + str(attempt)
                + " failed."
            )

            if attempt < 3:

                time.sleep(2)

            else:

                print(
                    device_name
                    + " could not be reached."
                )

                print(error)

                return None


def run_command(device_name, command):
    """
    Run one command using one SSH session.
    """

    connection = connect_to_router(
        device_name
    )

    if connection is None:
        return None

    try:

        output = connection.send_command(
            command,
            read_timeout=30
        )

        return output

    except Exception as error:

        print(
            "Command failed on "
            + device_name
            + ": "
            + str(error)
        )

        return None

    finally:

        connection.disconnect()


def run_commands(device_name, commands):
    """
    Run multiple commands using one SSH session.

    Returns:

    {
        "command": "output"
    }

    If an individual command fails, the remaining
    commands continue to execute.
    """

    connection = connect_to_router(
        device_name
    )

    if connection is None:
        return None

    results = {}

    try:

        for command in commands:

            print(
                "Running "
                + command
                + "..."
            )

            try:

                results[command] = (
                    connection.send_command(
                        command,
                        read_timeout=30
                    )
                )

            except Exception as error:

                results[command] = (
                    "COMMAND_FAILED: "
                    + str(error)
                )

                print(
                    "Command failed: "
                    + command
                )

        return results

    finally:

        connection.disconnect()


def run_config(device_name, commands):
    """
    Apply configuration commands using one SSH session.
    """

    connection = connect_to_router(
        device_name
    )

    if connection is None:
        return None

    try:

        output = connection.send_config_set(
            commands
        )

        return output

    except Exception as error:

        print(
            "Configuration failed on "
            + device_name
            + ": "
            + str(error)
        )

        return None

    finally:

        connection.disconnect()