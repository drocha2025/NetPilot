from netmiko import ConnectHandler
# Imports Netmiko so Python can connect to Cisco.


device = {
    "device_type": "cisco_ios",
    "host": "192.168.1.201",
    "username": "netpilot",
    "password": "NetPilotLab2026!",
    "port": 22,
}
# Contains the information Netmiko needs to connect to R1.


print("Connecting to R1...")
# Tells us that the connection attempt is starting.


connection = ConnectHandler(**device)
# Attempts to establish the SSH connection.


print("Connected!")
# If we get here, Netmiko successfully connected.


output = connection.send_command("show ip ospf neighbor")
# Sends a simple Cisco command.


print(output)
# Displays the router's response.


connection.disconnect()
# Closes the SSH connection.