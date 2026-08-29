from app.cisco_client import run_command
# Imports the function used to SSH into Cisco routers.


from app.ollama_client import ask_ollama
# Imports the function used to communicate with Ollama/Qwen.


def collect_network_evidence():
# Function responsible for collecting live network information.


    evidence = {}
    # Empty dictionary where all network evidence will be stored.


    commands = [
    # List of Cisco commands NetPilot will execute.


        "show ip ospf neighbor",
        # Checks OSPF neighbor relationships.


        "show ip ospf interface brief",
        # Checks OSPF information on router interfaces.


    ]
    # End of command list.


    for router in ["R1", "R2", "R3"]:
    # Process each router one at a time.


        evidence[router] = {}
        # Create a place to store this router's information.


        for command in commands:
        # Execute every diagnostic command against this router.


            print(f"Collecting {router}: {command}")
            # Tell the user what NetPilot is doing.


            output = run_command(router, command)
            # SSH into the router and execute the command.


            evidence[router][command] = output
            # Save the result.


    return evidence
    # Return all collected network information.


def build_prompt(evidence):
# Creates the AI instructions.


    return f"""
You are NetPilot, an expert Cisco network troubleshooting AI.

Analyze the following LIVE network evidence.

Your job is to identify the most likely ROOT CAUSE of the OSPF
connectivity problem.

Do not assume that the network is healthy.

Do not make configuration changes.

Explain:

1. What is wrong?
2. Which routers/interfaces are affected?
3. What evidence proves the problem?
4. What is the likely root cause?
5. What configuration should be corrected?

LIVE NETWORK EVIDENCE:

{evidence}
"""
# The Cisco evidence is inserted into the prompt.


def main():
# Main NetPilot program.


    print("\n===== NETPILOT NETWORK DIAGNOSTICS =====\n")
    # Display startup message.


    evidence = collect_network_evidence()
    # Collect live Cisco information.


    print("\n===== SENDING EVIDENCE TO QWEN =====\n")
    # Tell us that the AI phase is beginning.


    prompt = build_prompt(evidence)
    # Create the AI prompt.


    answer = ask_ollama(prompt)
    # Send the evidence to Qwen through Ollama.


    print("\n===== NETPILOT DIAGNOSIS =====\n")
    # Display diagnosis heading.


    print(answer)
    # Display the AI's answer.


if __name__ == "__main__":
# Start the application if this file is run directly.


    main()
    # Execute NetPilot.