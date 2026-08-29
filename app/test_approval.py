from app.cisco_client import send_config
# Imports the function that can make configuration changes.


router = "R3"
# Defines which router we want to change.


commands = [
    "interface Loopback0",
    "description NETPILOT-APPROVED",
]
# Defines the configuration commands NetPilot wants to apply.


print("===== NETPILOT PROPOSED CHANGE =====")
# Displays a heading.


print()
# Adds an empty line.


print(f"Router: {router}")
# Shows which router will be changed.


print()
# Adds an empty line.


print("Commands:")
# Displays a heading for the commands.


for command in commands:
    # Goes through each configuration command.

    print(f"  {command}")
    # Displays the command that NetPilot wants to execute.


print()
# Adds an empty line.


approval = input("Apply this change? (yes/no): ")
# Stops the program and asks YOU for permission.


if approval.lower() == "yes":
    # Checks whether you typed yes.

    print()
    # Adds an empty line.

    print("Applying configuration...")
    # Tells you NetPilot is going to make the change.

    output = send_config(router, commands)
    # Sends the approved configuration to the router.

    print(output)
    # Displays the router's response.

    print()
    # Adds an empty line.

    print("Change applied.")
    # Confirms that the change was sent.


else:
    # Runs when you type anything other than yes.

    print()
    # Adds an empty line.

    print("Change rejected.")
    # Tells you the change was not applied.