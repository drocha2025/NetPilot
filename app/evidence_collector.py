from app.cisco_client import run_command
# Imports the function used to connect to Cisco routers
# and run show commands.


def collect_network_evidence():
    # Creates a function that collects troubleshooting
    # information from every router.


    evidence = {}
    # Creates an empty dictionary where we will store
    # all evidence collected from the routers.


    commands = [
        "show ip ospf neighbor",
        # Shows current OSPF neighbor relationships.


        "show ip ospf interface brief",
        # Shows which interfaces are running OSPF
        # and which OSPF area they belong to.


        "show ip protocols",
        # Shows OSPF routing protocol information.


        "show ip route ospf"
        # Shows routes learned through OSPF.
    ]


    routers = ["R1", "R2", "R3"]
    # Creates a list containing the routers
    # that NetPilot will investigate.


    for router in routers:
        # Loops through one router at a time.


        evidence[router] = {}
        # Creates an empty section for this router's evidence.


        for command in commands:
            # Loops through each troubleshooting command.


            print(f"Collecting {router}: {command}")
            # Displays which router and command
            # NetPilot is currently processing.


            output = run_command(router, command)
            # Connects to the router and runs the command.


            evidence[router][command] = output
            # Saves the command output inside the evidence dictionary.


    return evidence
    # Returns all collected evidence.