import requests
# Imports the "requests" Python library.
# This library allows Python to communicate with websites and APIs.
# NetPilot uses it to communicate with Ollama.


from app.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT
# Imports three settings from our config.py file:
#
# OLLAMA_HOST    = The IP address of the computer running Ollama.
# OLLAMA_MODEL   = The AI model we want to use.
# OLLAMA_TIMEOUT = How long Python will wait for Ollama to respond.


def ask_ollama(prompt: str) -> str:
# Creates a function called "ask_ollama".
#
# A function is a reusable block of Python code.
#
# "prompt" is the question/information we want to send to the AI.
#
# ": str" means we expect the prompt to be text.
#
# "-> str" means this function will return text.
#
# In simple terms:
#
#     Give this function a prompt
#              ↓
#     Send it to Ollama
#              ↓
#     Get an AI response back


    url = f"{OLLAMA_HOST}/api/chat"
    # Creates the web address that Python will use to communicate
    # with Ollama.
    #
    # For our NetPilot setup, OLLAMA_HOST points to:
    #
    #     http://192.168.1.217:11434
    #
    # So the final URL becomes:
    #
    #     http://192.168.1.217:11434/api/chat
    #
    # "/api/chat" tells Ollama that we want to have a conversation
    # with the AI model.


    payload = {
    # Creates a Python dictionary called "payload".
    #
    # A dictionary is a way of storing information using
    # names and values.
    #
    # This dictionary will contain everything we want to
    # send to Ollama.


        "model": OLLAMA_MODEL,
        # Tells Ollama which AI model to use.
        #
        # In our project this is:
        #
        #     qwen2.5:32b
        #
        # This is the Qwen model running on your desktop.


        "messages": [
        # Creates a list of messages that will be sent to the AI.
        #
        # We are using two messages:
        #
        # 1. A system message
        # 2. A user message


            {
                "role": "system",
                # Identifies this message as a SYSTEM instruction.
                #
                # System instructions tell the AI how it should
                # behave and what type of expert it should act as.


                "content": (
                    "You are NetPilot, an AI network operations assistant. "
                    # Tells the AI that its name/role is NetPilot
                    # and that it is helping with network operations.


                    "You specialize in enterprise Cisco networking, "
                    # Tells the AI that Cisco networking is one of
                    # its areas of expertise.


                    "routing, switching, security, and troubleshooting."
                    # Gives the AI additional areas of expertise:
                    #
                    # Routing
                    # Switching
                    # Network security
                    # Troubleshooting
                ),
            },
            # The system message ends here.


            {
                "role": "user",
                # Identifies this message as information coming
                # from the user/program.
                #
                # In our case, NetPilot's Python program will
                # provide the network troubleshooting prompt.


                "content": prompt,
                # Places the actual prompt into the message.
                #
                # This is where our network evidence and questions
                # will eventually be sent to Qwen.
            },
            # The user message ends here.


        ],
        # The messages list ends here.


        "stream": False,
        # Tells Ollama NOT to send the response one piece at a time.
        #
        # False means:
        #
        #     Send us the complete AI response
        #
        # instead of:
        #
        #     Send us the response gradually as it is generated.
    }
    # The payload dictionary is now complete.


    response = requests.post(
        url,
        # Sends the request to the Ollama URL we created earlier.


        json=payload,
        # Sends our payload to Ollama as JSON data.
        #
        # JSON is a common format used for sending information
        # between applications.


        timeout=OLLAMA_TIMEOUT,
        # Tells Python how long it should wait for Ollama.
        #
        # If Ollama takes too long to respond, Python will stop
        # waiting and report a timeout error.
    )
    # The HTTP request has now been sent to Ollama.


    response.raise_for_status()
    # Checks whether Ollama returned an error.
    #
    # If everything worked:
    #
    #     Python continues.
    #
    # If Ollama returned an HTTP error such as 404 or 500:
    #
    #     Python raises an error so we know something went wrong.


    data = response.json()
    # Takes Ollama's response and converts the JSON data
    # into a Python dictionary.
    #
    # This makes it easier for Python to access the AI's answer.


    return data["message"]["content"]
    # Extracts the actual text generated by Qwen.
    #
    # Ollama's response contains several pieces of information.
    #
    # We navigate through:
    #
    #     message
    #        ↓
    #     content
    #
    # "content" contains the actual AI response.
    #
    # "return" sends that response back to whatever part
    # of NetPilot called the ask_ollama() function.