from netmiko import ConnectHandler


DEVICES = {
    "R1": {
        "device_type": "cisco_ios",
        "host": "192.168.1.201",
        "username": "netpilot",
        "password": "NetPilotLab2026!",
    },
    "R2": {
        "device_type": "cisco_ios",
        "host": "192.168.1.202",
        "username": "netpilot",
        "password": "NetPilotLab2026!",
    },
    "R3": {
        "device_type": "cisco_ios",
        "host": "192.168.1.203",
        "username": "netpilot",
        "password": "NetPilotLab2026!",
    },
}


def run_command(device_name, command):
    # Connects to a router and runs a show command.

    device = DEVICES[device_name]
    # Gets the connection information for the router.

    connection = ConnectHandler(**device)
    # Opens an SSH connection.

    try:
        output = connection.send_command(command)
        # Runs the requested show command.

        return output
        # Sends the output back to the program.

    finally:
        connection.disconnect()
        # Closes the SSH connection.


def send_config(device_name, commands):
    # Connects to a router and sends configuration commands.

    device = DEVICES[device_name]
    # Gets the connection information for the selected router.

    connection = ConnectHandler(**device)
    # Opens an SSH connection to the router.

    try:
        output = connection.send_config_set(commands)
        # Sends the configuration commands to the router.

        return output
        # Returns the router's response.

    finally:
        connection.disconnect()
        # Closes the SSH connection.