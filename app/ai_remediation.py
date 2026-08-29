from app.cisco_client import run_command, send_config
# Imports the functions used to read from and configure Cisco routers.


from app.ollama_client import ask_ollama
# Imports the function that sends our network information to Qwen.


ROUTERS = ["R1", "R2", "R3"]
# Creates a list of routers that NetPilot will check.


def collect_ospf_evidence():
    # Collects OSPF information from every router.

    evidence = ""
    # Creates an empty area where we will store the evidence.

    for router in ROUTERS:
        # Checks each router one at a time.

        print(f"Collecting OSPF information from {router}...")
        # Shows which router NetPilot is checking.

        neighbors = run_command(router, "show ip ospf neighbor")
        # Gets the OSPF neighbor information.

        interfaces = run_command(router, "show ip ospf interface brief")
        # Gets the OSPF interface information.

        evidence += f"\n===== {router} =====\n"
        # Adds the router name to the evidence.

        evidence += "\nOSPF NEIGHBORS\n"
        # Adds a heading for the neighbor information.

        evidence += neighbors
        # Adds the neighbor information.

        evidence += "\n\nOSPF INTERFACES\n"
        # Adds a heading for the interface information.

        evidence += interfaces
        # Adds the interface information.

    return evidence
    # Sends all of the collected evidence back to the program.


def get_ai_recommendation(evidence):
    # Sends the network evidence to Qwen.

    prompt = f"""
You are NetPilot, an AI network operations assistant.

Analyze the Cisco OSPF evidence below.

Identify the specific router and interface that requires correction.

Return ONLY these five lines:

ROUTER: <router>
INTERFACE: <interface>
CURRENT_AREA: <number>
EXPECTED_AREA: <number>
REASON: <short explanation>

Do not include configuration commands.

NETWORK EVIDENCE:

{evidence}
"""
    # Creates the instructions that will be sent to Qwen.

    print()
    # Adds an empty line.

    print("===== SENDING EVIDENCE TO AI =====")
    # Shows that NetPilot is sending information to Qwen.

    recommendation = ask_ollama(prompt)
    # Sends the evidence to Qwen.

    return recommendation
    # Returns Qwen's answer.


def parse_recommendation(recommendation):
    # Reads Qwen's answer and extracts the important information.

    router = None
    # Creates an empty variable for the router.

    interface = None
    # Creates an empty variable for the interface.

    current_area = None
    # Creates an empty variable for the current area.

    expected_area = None
    # Creates an empty variable for the expected area.

    reason = None
    # Creates an empty variable for the reason.

    for line in recommendation.splitlines():
        # Goes through Qwen's response one line at a time.

        if line.startswith("ROUTER:"):
            # Looks for the router line.

            router = line.replace("ROUTER:", "").strip()
            # Removes "ROUTER:" and saves the router name.

        elif line.startswith("INTERFACE:"):
            # Looks for the interface line.

            interface = line.replace("INTERFACE:", "").strip()
            # Removes "INTERFACE:" and saves the interface name.

        elif line.startswith("CURRENT_AREA:"):
            # Looks for the current OSPF area.

            current_area = line.replace("CURRENT_AREA:", "").strip()
            # Removes the label and saves the area.

        elif line.startswith("EXPECTED_AREA:"):
            # Looks for the expected OSPF area.

            expected_area = line.replace("EXPECTED_AREA:", "").strip()
            # Removes the label and saves the expected area.

        elif line.startswith("REASON:"):
            # Looks for the explanation.

            reason = line.replace("REASON:", "").strip()
            # Removes the label and saves the explanation.

    return router, interface, current_area, expected_area, reason
    # Sends all five pieces of information back to the program.


def approve_change(router, interface, current_area, expected_area, reason):
    # Shows the proposed change and asks the user for permission.

    print()
    # Adds an empty line.

    print("===== PROPOSED REMEDIATION =====")
    # Displays a heading.

    print(f"Router: {router}")
    # Shows which router will be changed.

    print(f"Interface: {interface}")
    # Shows which interface will be changed.

    print(f"Current OSPF Area: {current_area}")
    # Shows the current OSPF area.

    print(f"Expected OSPF Area: {expected_area}")
    # Shows the OSPF area NetPilot expects.

    print(f"Reason: {reason}")
    # Shows why the change is being recommended.

    print()
    # Adds an empty line.

    print("Configuration that will be applied:")
    # Displays a heading for the configuration.

    print(f"interface {interface}")
    # Shows the interface command.

    print(f" ip ospf 1 area {expected_area}")
    # Shows the OSPF command NetPilot will apply.

    print()
    # Adds an empty line.

    answer = input("Apply this change? (yes/no): ")
    # Asks the network engineer for approval.

    return answer.lower() == "yes"
    # Returns True if the engineer typed yes.


def apply_change(router, interface, expected_area):
    # Applies the approved configuration to the router.

    commands = [
        f"interface {interface}",
        f"ip ospf 1 area {expected_area}",
    ]
    # Creates the Cisco configuration commands.

    print()
    # Adds an empty line.

    print("===== APPLYING CHANGE =====")
    # Shows that NetPilot is now making the change.

    output = send_config(router, commands)
    # Sends the configuration to the selected router.

    print(output)
    # Displays the router's response.


def verify_change(router):
    # Checks whether the change was successful.

    print()
    # Adds an empty line.

    print("===== VERIFYING CHANGE =====")
    # Displays a verification heading.

    neighbors = run_command(router, "show ip ospf neighbor")
    # Gets the router's current OSPF neighbors.

    interfaces = run_command(router, "show ip ospf interface brief")
    # Gets the router's current OSPF interface information.

    print()
    # Adds an empty line.

    print("OSPF NEIGHBORS:")
    # Displays a heading.

    print(neighbors)
    # Displays the neighbor information.

    print()
    # Adds an empty line.

    print("OSPF INTERFACES:")
    # Displays a heading.

    print(interfaces)
    # Displays the interface information.


if __name__ == "__main__":
    # Starts the program when this file is executed directly.

    evidence = collect_ospf_evidence()
    # Collects the current network information.

    recommendation = get_ai_recommendation(evidence)
    # Sends the information to Qwen.

    print()
    # Adds an empty line.

    print("===== NETPILOT AI DIAGNOSIS =====")
    # Displays a heading.

    print(recommendation)
    # Displays Qwen's recommendation.

    router, interface, current_area, expected_area, reason = parse_recommendation(
        recommendation
    )
    # Extracts the router, interface, areas, and reason from Qwen's response.

    if not router or not interface or not expected_area:
        # Checks whether Qwen provided the information NetPilot needs.

        print()
        # Adds an empty line.

        print("AI recommendation could not be understood.")
        # Stops the program if the AI response was incomplete.

        print("No configuration was changed.")
        # Confirms that nothing was modified.

        exit()
        # Stops the program.


    approved = approve_change(
        router,
        interface,
        current_area,
        expected_area,
        reason,
    )
    # Shows the proposed change and asks for approval.

    if approved:
        # Runs this section if the engineer approved the change.

        apply_change(router, interface, expected_area)
        # Sends the configuration to the router.

        verify_change(router)
        # Checks the router after the change.

        print()
        # Adds an empty line.

        print("===== REMEDIATION COMPLETE =====")
        # Tells us that NetPilot finished the remediation.

    else:
        # Runs this section if the engineer rejected the change.

        print()
        # Adds an empty line.

        print("Change rejected.")
        # Tells us the change was not approved.

        print("No configuration was changed.")
        # Confirms that NetPilot did not modify the network.