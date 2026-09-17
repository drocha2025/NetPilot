import json
import urllib.request
import urllib.error

from app.incident_engine import investigate_incident


OLLAMA_HOST = "http://192.168.1.217:11434"
OLLAMA_MODEL = "qwen2.5:32b"
OLLAMA_TIMEOUT = 600


def build_prompt(incident):
    """
    Build the AI investigation prompt.
    """

    router = incident["router"]
    incident_type = incident["type"]
    description = incident["description"]
    evidence = incident["evidence_summary"]

    prompt = f"""
You are NetPilot, an AI-assisted Cisco network operations engineer.

You are analyzing a customer network incident.

Your job is to analyze the supplied Cisco evidence and produce a
structured root-cause analysis.

IMPORTANT RULES:

1. Do not invent facts.
2. Only use evidence provided in the incident.
3. Clearly distinguish confirmed facts from assumptions.
4. Do not recommend configuration changes unless the evidence supports them.
5. Do not make any network changes yourself.
6. A human network engineer must approve any remediation.
7. Prioritize the most likely root cause.
8. Explain why the evidence supports your conclusion.
9. If the device is unreachable, treat device connectivity as a
   primary finding.
10. Consider operational safety and customer impact.

CUSTOMER INCIDENT

Router:
{router}

Incident Type:
{incident_type}

Customer Description:
{description}

COLLECTED EVIDENCE

{evidence}

Return your analysis using exactly this structure:

ROOT CAUSE:
<most likely root cause>

CONFIDENCE:
<High, Medium, or Low>

EVIDENCE:
- <important evidence item>
- <important evidence item>
- <important evidence item>

IMPACT:
<customer or network impact>

RECOMMENDED ACTION:
<recommended engineer action>

RISK:
<Low, Medium, or High>

VALIDATION:
<how the engineer should verify the issue is resolved>

CUSTOMER_SUMMARY:
<short explanation suitable for a customer-facing incident update>
"""

    return prompt


def call_ollama(prompt):
    """
    Send the investigation prompt to Ollama.
    """

    url = OLLAMA_HOST + "/api/generate"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT
        ) as response:

            response_data = response.read()

            result = json.loads(
                response_data.decode("utf-8")
            )

            return result.get(
                "response",
                ""
            )

    except urllib.error.URLError as error:

        return (
            "AI analysis unavailable. "
            "Unable to connect to Ollama: "
            + str(error)
        )

    except TimeoutError:

        return (
            "AI analysis unavailable. "
            "Ollama request timed out."
        )

    except Exception as error:

        return (
            "AI analysis unavailable: "
            + str(error)
        )


def analyze_incident(incident):
    """
    Analyze an investigated incident with Ollama.
    """

    print()
    print("========================================")
    print("NETPILOT AI ROOT-CAUSE ANALYSIS")
    print("========================================")

    prompt = build_prompt(incident)

    print()
    print("Sending incident evidence to Ollama...")
    print("Model: " + OLLAMA_MODEL)

    analysis = call_ollama(prompt)

    incident["ai_analysis"] = analysis
    incident["status"] = "AI_ANALYZED"

    print()
    print("========================================")
    print("AI ANALYSIS")
    print("========================================")

    print(analysis)

    return incident


if __name__ == "__main__":

    incident = investigate_incident(
        router="R2",
        incident_type="OSPF_CONNECTIVITY",
        description=(
            "Customer reports loss of connectivity "
            "involving R2."
        ),
    )

    analyze_incident(incident)

    print()
    print("========================================")
    print("AI INVESTIGATION COMPLETE")
    print("========================================")

    print(
        "Incident ID: "
        + incident["id"]
    )

    print(
        "Status: "
        + incident["status"]
    )