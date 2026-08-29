from app.cisco_client import run_command
# Imports the same function used by drift_detector.py.


print("Testing cisco_client.py...")
# Tells us the test is starting.


output = run_command("R1", "show ip ospf neighbor")
# Uses our actual NetPilot Cisco function to connect to R1
# and run the OSPF neighbor command.


print()
# Prints a blank line.


print(output)
# Displays the router's response.