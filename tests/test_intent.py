from app.intent_engine import load_network_intent
# Imports the function that loads our network intent.


def main():
    # Creates the main function.


    intent = load_network_intent()
    # Loads the intended network configuration.


    print("\n===== NETPILOT NETWORK INTENT =====\n")
    # Prints a title.


    print(intent)
    # Displays the network intent.


if __name__ == "__main__":
    # Checks whether this program is being run directly.


    main()
    # Starts the program.