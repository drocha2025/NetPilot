from app.cisco_client import run_command
# Imports the function that connects to Cisco routers
# and runs commands on them.


from pathlib import Path
# Imports Path, which makes it easier to work with files and folders.


ROUTERS = ["R1", "R2", "R3"]
# Creates a list containing the routers NetPilot will check.


def collect_running_config(router):
    # Collects the current configuration from one router.

    print(f"Collecting configuration from {router}...")
    # Tells us which router NetPilot is currently working with.


    config = run_command(router, "show running-config")
    # Connects to the router and runs "show running-config".


    if config is None:
        # Checks whether NetPilot was unable to connect to the router.

        return None
        # Tells the program that no configuration was collected.


    return config
    # Sends the configuration back to the program.


def save_golden_config(router, config):
    # Saves the router configuration as the golden configuration.

    directory = Path("data/golden")
    # Defines the folder where golden configurations are stored.


    directory.mkdir(parents=True, exist_ok=True)
    # Creates the data/golden folder if it does not already exist.


    filename = directory / f"{router}.cfg"
    # Creates a filename such as:
    # data/golden/R1.cfg


    filename.write_text(config)
    # Writes the router configuration into the file.


    print(f"Saved golden configuration for {router}")
    # Tells us that the configuration was saved successfully.


def create_golden_config():
    # Creates golden configurations for all routers.

    for router in ROUTERS:
        # Goes through the routers one at a time:
        # R1, then R2, then R3.


        config = collect_running_config(router)
        # Gets the running configuration from the router.


        if config is None:
            # Checks whether the configuration collection failed.


            print(f"Skipping {router}")
            # Tells us that this router will not be saved.


            continue
            # Moves to the next router in the list.


        save_golden_config(router, config)
        # Saves the configuration as the golden configuration.


if __name__ == "__main__":
    # Checks whether this file is being run directly.


    create_golden_config()
    # Starts the golden configuration collection process.