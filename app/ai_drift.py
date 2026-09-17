from app.ollama_client import ask_ollama


def analyze_drift(router, missing, added):
    """
    Send configuration drift information to the local
    Qwen model running through Ollama.

    The AI analyzes the change and returns:
    - What changed
    - Affected router
    - Risk level
    - Why it matters
    - Recommended Cisco configuration
    """

    missing_text = "\n".join(missing)

    added_text = "\n".join(added)

    prompt = f"""
You are NetPilot AI, an enterprise network operations assistant.

Analyze the following Cisco configuration drift.

Router:
{router}

Configuration expected by the NetPilot golden configuration:
{missing_text}

Configuration currently detected on the router:
{added_text}

Provide a concise network-operations analysis using exactly these sections:

1. CHANGE DETECTED
Identify what configuration changed.

2. AFFECTED DEVICE
Identify the router.

3. RISK LEVEL
Choose exactly one:
LOW
MEDIUM
HIGH

4. WHY IT MATTERS
Explain the possible operational impact.

5. RECOMMENDED ACTION
Explain what should be restored.

6. CISCO CONFIGURATION
Provide the exact Cisco IOS configuration commands that would restore the expected configuration.

IMPORTANT:
- Do not claim that a configuration was changed unless the supplied data proves it.
- Do not invent interfaces, IP addresses, routing protocols, or commands.
- If the change is only an interface description, identify it as a documentation/configuration consistency issue.
- Do not execute any commands.
- This is analysis and recommendation only.
"""

    try:

        response = ask_ollama(prompt)

        if response:

            return response

        return (
            "AI analysis unavailable: "
            "Ollama returned an empty response."
        )

    except Exception as error:

        return (
            "AI analysis unavailable: "
            + str(error)
        )
