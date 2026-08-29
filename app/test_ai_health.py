from app.cisco_client import run_command
# Imports our function that connects to the Cisco routers.


from app.ollama_client import ask_ollama
# Imports our function that sends information to Qwen.


ROUTERS = ["R1", "R2", "R3"]
# Creates a list of the routers we want to investigate.


def collect_evidence(router):
    # Collects OSPF information from one router.

    neighbors = run_command(router, "show ip ospf neighbor")
    # Gets the OSPF neighbor information.

    interfaces = run_command(router, "show ip ospf interface brief")
    # Gets the OSPF interface information.

    return neighbors, interfaces
    # Sends both pieces of information back to the program.


def build_prompt(evidence):
    # Creates the instructions we will give to the AI.

    prompt = """
You are NetPilot, an AI network troubleshooting assistant.

Analyze the Cisco OSPF evidence below.

Your job is to identify:

1. Which router has a problem.
2. Which interface has the problem.
3. What OSPF area the interface is using.
4. What you believe the correct area should be.
5. Why the problem is affecting OSPF.
6. The exact configuration change you recommend.

Do not guess when the evidence does not support an answer.

===== OSPF EVIDENCE =====

"""

    prompt += evidence
    # Adds the router information to our instructions.

    return prompt
    # Sends the completed prompt back to the program.


def main():
    # This function runs the entire AI health check.

    evidence = ""
    # Creates an empty area where we will store the router information.


    for router in ROUTERS:
        # Goes through R1, R2, and R3.

        neighbors, interfaces = collect_evidence(router)
        # Collects OSPF information from the current router.

        evidence += f"\n===== {router} =====\n"
        # Adds the router name to the evidence.

        evidence += "\nOSPF NEIGHBORS:\n"
        # Adds a heading for the neighbor information.

        evidence += neighbors
        # Adds the actual neighbor information.

        evidence += "\n\nOSPF INTERFACES:\n"
        # Adds a heading for the interface information.

        evidence += interfaces
        # Adds the actual interface information.


    prompt = build_prompt(evidence)
    # Builds the final instructions for Qwen.


    print()
    # Prints a blank line.

    print("===== SENDING NETWORK EVIDENCE TO AI =====")
    # Tells us that NetPilot is contacting Qwen.


    answer = ask_ollama(prompt)
    # Sends our evidence to Qwen and gets the AI response.


    print()
    # Prints a blank line.

    print("===== NETPILOT AI HEALTH DIAGNOSIS =====")
    # Displays a heading for the AI response.

    print(answer)
    # Displays Qwen's diagnosis.


if __name__ == "__main__":
    # Checks whether this file was started directly.

    main()
    # Starts the NetPilot AI health check.