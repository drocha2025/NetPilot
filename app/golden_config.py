from app.cisco_client import run_command
# Imports the function that connects to the Cisco routers
# and runs show commands.


from pathlib import Path
# Imports Path, which makes it easier to work with files and folders.


ROUTERS = ["R1", "R2", "R3"]
# Creates a list containing the routers we want to collect.


def collect_running_config(router):
    # Collects the current configuration from one router.

    print(f"Collecting configuration from {router}...")
    # Shows which router NetPilot is currently working on.

    config = run_command(router, "show running-config")
    # Connects to the router and runs "show running-config".

    return config
    # Sends the configuration back to the program.


def save_golden_config(router, config):
    # Saves the router configuration as a golden configuration.

    directory = Path("data/golden")
    # Defines the folder where our golden configurations will live.

    directory.mkdir(parents=True, exist_ok=True)
    # Creates the data/golden folder if it doesn't already exist.

    filename = directory / f"{router}.cfg"
    # Creates a filename such as:
    # data/golden/R1.cfg

    filename.write_text(config)
    # Writes the router's configuration into the file.

    print(f"Saved golden configuration for {router}")
    # Tells us that the configuration was saved successfully.


def create_golden_config():
    # Creates the golden configuration for all routers.

    for router in ROUTERS:
        # Goes through R1, then R2, then R3.

        config = collect_running_config(router)
        # Gets the running configuration from the router.

        save_golden_config(router, config)
        # Saves that configuration as the golden configuration.


if __name__ == "__main__":
    # Checks whether we are running this file directly.

    create_golden_config()
    # Starts the entire golden configuration process.