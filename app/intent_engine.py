import json
# Imports Python's built-in JSON library.
# JSON files are commonly used to store structured information.


def load_network_intent():
    # Creates a function that will load our network intent file.


    with open("data/network_intent.json", "r") as file:
        # Opens the network_intent.json file.
        #
        # "r" means we are opening the file for reading.


        intent = json.load(file)
        # Reads the JSON file and converts the information
        # into a Python dictionary.


    return intent
    # Sends the network intent information back to the program.