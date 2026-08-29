from netmiko import ConnectHandler
# Imports Netmiko so Python can connect to Cisco routers.


DEVICES = {
    "R1": {
        "device_type": "cisco_ios",
        "host": "192.168.1.201",
        "username": "netpilot",
        "password": "NetPilotLab2026!",
        "port": 22,
    },

    "R2": {
        "device_type": "cisco_ios",
        "host": "192.168.1.202",
        "username": "netpilot",
        "password": "NetPilotLab2026!",
        "port": 22,
    },

    "R3": {
        "device_type": "cisco_ios",
        "host": "192.168.1.203",
        "username": "netpilot",
        "password": "NetPilotLab2026!",
        "port": 22,
    },
}
# Stores the connection information for all three routers.


def run_command(device_name, command):
    # Connects to a router and runs a Cisco command.

    device = DEVICES[device_name]
    # Looks up the router information using its name.


    print(f"Connecting to {device_name}...")
    # Shows which router NetPilot is trying to reach.


    for attempt in range(1, 4):
        # Gives NetPilot three chances to connect.


        try:
            connection = ConnectHandler(**device)
            # Attempts to establish the SSH connection.


            print(f"{device_name} connected!")
            # Tells us the connection was successful.


            try:
                output = connection.send_command(command)
                # Sends the requested Cisco command to the router.

                return output
                # Sends the command output back to the calling script.


            finally:
                connection.disconnect()
                # Closes the SSH connection when finished.


        except Exception as error:
            # Catches a connection error instead of crashing NetPilot.


            print(
                f"{device_name} connection attempt {attempt} failed."
            )
            # Tells us which attempt failed.


            if attempt == 3:
                # Checks whether this was the final attempt.


                print(
                    f"{device_name} is unreachable."
                )
                # Reports that NetPilot could not connect.


                return None
                # Sends None back instead of crashing the program.