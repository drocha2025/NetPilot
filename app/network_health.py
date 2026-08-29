from app.cisco_client import run_command
# Imports our existing function that connects to a Cisco router
# and runs a command.


ROUTERS = ["R1", "R2", "R3"]
# Creates a list of the routers NetPilot will check.


def check_router(router):
    # This function checks the health of one router.

    print()
    # Prints a blank line to make the output easier to read.

    print(f"===== Checking {router} =====")
    # Displays the name of the router we are checking.


    ospf_neighbors = run_command(router, "show ip ospf neighbor")
    # Connects to the router and asks Cisco for its OSPF neighbors.


    ospf_interfaces = run_command(router, "show ip ospf interface brief")
    # Connects to the router and asks Cisco for its OSPF interfaces.


    print()
    # Adds a blank line before displaying the results.

    print("OSPF NEIGHBORS")
    # Creates a heading for the neighbor information.

    print(ospf_neighbors)
    # Displays the OSPF neighbor information.


    print()
    # Adds another blank line.

    print("OSPF INTERFACES")
    # Creates a heading for the interface information.

    print(ospf_interfaces)
    # Displays the OSPF interface information.


for router in ROUTERS:
    # Goes through the routers one at a time:
    # R1, then R2, then R3.

    check_router(router)
    # Sends the current router to our check_router function.