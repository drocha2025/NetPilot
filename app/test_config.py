from app.cisco_client import send_config
# Imports our function that can send configuration commands.


commands = [
    "interface Loopback0",
    "description NETPILOT-TEST",
]
# Creates two configuration commands.
# These commands only add a description to Loopback0.


print("===== TESTING CONFIGURATION =====")
# Displays a heading.


output = send_config("R3", commands)
# Sends the commands to R3.


print(output)
# Displays the router's response.