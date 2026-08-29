from app.ollama_client import ask_ollama
# Imports our existing function that sends information to Qwen.


def analyze_drift(router, missing, added):
    # Creates a function that sends configuration drift
    # to the AI for analysis.

    prompt = f"""
You are NetPilot, an AI network troubleshooting assistant.

Analyze the configuration drift below.

Router:
{router}

Configuration expected by the golden configuration:
{missing}

Configuration currently found on the router:
{added}

Explain:

1. What changed?
2. Why could this be a problem?
3. What network technology is affected?
4. Which router should be corrected?
5. What configuration should be restored?

Do not make changes to the router.
Only provide a diagnosis and recommended configuration.
"""
    # Creates the instructions that we will send to Qwen.

    answer = ask_ollama(prompt)
    # Sends the prompt to Ollama and gets Qwen's response.

    return answer
    # Sends the AI's answer back to our program.