from pathlib import Path
# Lets Python work with files.


from app.cisco_client import run_command
# Lets NetPilot send commands to Cisco routers.


from app.ai_drift import analyze_drift
# Lets NetPilot send configuration differences to Qwen.


routers = ["R1", "R2", "R3"]
# These are the routers NetPilot will check.


def check_router(router):
    # Checks one router for configuration drift.

    print()
    # Prints a blank line.

    print("Checking " + router)
    # Shows which router we are checking.


    golden_file = Path("data/golden/" + router + ".cfg")
    # Finds the golden configuration for this router.


    golden = golden_file.read_text()
    # Reads the golden configuration.


    live = run_command(router, "show running-config")
    # Gets the current configuration from the Cisco router.


    golden_lines = golden.splitlines()
    # Breaks the golden configuration into individual lines.


    live_lines = live.splitlines()
    # Breaks the live configuration into individual lines.


    if golden == live:
        # Checks whether the configurations are exactly the same.

        print(router + " is compliant")
        # Tells us there is no drift.

        return
        # Stops checking this router.


    print(router + " has configuration drift")
    # Tells us that something changed.


    missing = []
    # Creates an empty list for configuration that is missing.


    added = []
    # Creates an empty list for configuration that was added.


    for line in golden_lines:
        # Looks at every line in the golden configuration.

        if line not in live_lines:
            # Checks if the golden line is missing from the live router.

            missing.append(line)
            # Adds the missing line to our list.


    for line in live_lines:
        # Looks at every line in the live configuration.

        if line not in golden_lines:
            # Checks if this live line wasn't in the golden configuration.

            added.append(line)
            # Adds the unexpected line to our list.


    print()
    # Adds spacing.


    print("Sending configuration drift to Qwen...")
    # Tells us that the AI analysis is starting.


    answer = analyze_drift(router, missing, added)
    # Sends the router and configuration differences to Qwen.


    print()
    # Adds spacing.


    print("===== NETPILOT AI DIAGNOSIS =====")
    # Displays the AI diagnosis heading.


    print(answer)
    # Displays Qwen's answer.


for router in routers:
    # Goes through R1, R2, and R3.

    check_router(router)
    # Checks the current router.