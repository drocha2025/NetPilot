import json
import urllib.request
import urllib.error

from app.monitoring import collect_health_snapshot
from app.incident_manager import (
    normalize_health_snapshot,
    process_health_snapshot
)


OLLAMA_HOST = "http://192.168.1.217:11434"
OLLAMA_MODEL = "qwen2.5:32b"
OLLAMA_TIMEOUT = 600


def call_ollama(prompt):
    """
    Send a prompt to the local Ollama server.
    """

    url = OLLAMA_HOST + "/api/generate"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT
        ) as response:

            response_data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

            return response_data.get(
                "response",
                ""
            ).strip()

    except urllib.error.URLError as error:

        return (
            "OLLAMA_CONNECTION_ERROR: "
            + str(error)
        )

    except Exception as error:

        return (
            "OLLAMA_ERROR: "
            + str(error)
        )


def build_incident_evidence(
    incident
):
    """
    Build a compact evidence package for
    the LLM.

    Only verified NetPilot state is supplied.
    """

    evidence = incident.get(
        "evidence",
        {}
    )

    correlation = incident.get(
        "correlation",
        {}
    )

    return {
        "router": incident.get(
            "router"
        ),

        "incident_type": incident.get(
            "incident_type"
        ),

        "status": incident.get(
            "status"
        ),

        "description": incident.get(
            "description"
        ),

        "impact": incident.get(
            "impact"
        ),

        "availability": evidence.get(
            "availability"
        ),

        "health": evidence.get(
            "health"
        ),

        "ospf": evidence.get(
            "ospf"
        ),

        "ospf_neighbors": evidence.get(
            "ospf_neighbors"
        ),

        "wan": evidence.get(
            "wan"
        ),

        "active_path": evidence.get(
            "active_path"
        ),

        "default_route": evidence.get(
            "default_route"
        ),

        "default_next_hop": evidence.get(
            "default_next_hop"
        ),

        "primary_interface": evidence.get(
            "primary_interface"
        ),

        "primary_interface_name": evidence.get(
            "primary_interface_name"
        ),

        "primary_bgp": evidence.get(
            "primary_bgp"
        ),

        "primary_bgp_neighbor": evidence.get(
            "primary_bgp_neighbor"
        ),

        "backup_interface": evidence.get(
            "backup_interface"
        ),

        "backup_interface_name": evidence.get(
            "backup_interface_name"
        ),

        "backup_bgp": evidence.get(
            "backup_bgp"
        ),

        "backup_bgp_neighbor": evidence.get(
            "backup_bgp_neighbor"
        ),

        "correlated_symptoms": correlation.get(
            "symptoms",
            []
        )
    }


def build_ai_prompt(
    incident
):
    """
    Build a safety-focused RCA prompt.

    The LLM receives evidence only.
    """

    evidence = build_incident_evidence(
        incident
    )

    evidence_json = json.dumps(
        evidence,
        indent=2
    )

    prompt = f"""
You are the AI diagnostic assistant for NetPilot,
a Cisco network operations platform.

Your job is to analyze a VERIFIED network incident.

You are NOT allowed to make network changes.

You are NOT allowed to invent Cisco CLI output,
interfaces, IP addresses, BGP states, OSPF states,
routes, or other facts.

Use ONLY the supplied evidence.

If the evidence does not prove something,
clearly label it as an assumption or unknown.

The application has already determined the
incident classification.

Do NOT change the incident classification.

Incident:

{evidence_json}

Analyze the incident using this format:

ROOT CAUSE
State the most likely root cause based only
on the supplied evidence.

CONFIDENCE
Choose HIGH, MEDIUM, or LOW.

EVIDENCE
List the specific verified observations that
support the root cause.

SYMPTOMS
Explain the related symptoms and how they
connect to the root cause.

CUSTOMER IMPACT
Describe the likely operational impact.

RECOMMENDED ACTION
Recommend what the network engineer should
investigate or consider doing.

Do NOT provide configuration commands.

RISK
Choose LOW, MEDIUM, or HIGH and explain why.

VALIDATION
Describe what should be verified after the
engineer takes corrective action.

ASSUMPTIONS
List anything that cannot be proven from the
supplied evidence.

SAFETY
Explicitly state that no network changes were
made by the AI.

Keep the analysis concise and operational.
"""

    return prompt


def analyze_incident(
    incident
):
    """
    Analyze one correlated incident with Ollama.
    """

    if not isinstance(
        incident,
        dict
    ):

        return {
            "status": "FAILED",
            "root_cause": None,
            "confidence": None,
            "analysis": (
                "Invalid incident object."
            )
        }

    prompt = build_ai_prompt(
        incident
    )

    response = call_ollama(
        prompt
    )

    if response.startswith(
        "OLLAMA_"
    ):

        return {
            "status": "FAILED",
            "root_cause": None,
            "confidence": None,
            "analysis": response
        }

    return {
        "status": "COMPLETED",
        "root_cause": extract_section(
            response,
            "ROOT CAUSE"
        ),
        "confidence": extract_section(
            response,
            "CONFIDENCE"
        ),
        "analysis": response
    }


def extract_section(
    text,
    section_name
):
    """
    Extract a section from structured LLM output.
    """

    if not text:
        return ""

    lines = text.splitlines()

    start_index = None

    for index, line in enumerate(
        lines
    ):

        if line.strip().upper() == section_name:

            start_index = index + 1

            break

    if start_index is None:
        return ""

    section_lines = []

    known_sections = [
        "ROOT CAUSE",
        "CONFIDENCE",
        "EVIDENCE",
        "SYMPTOMS",
        "CUSTOMER IMPACT",
        "RECOMMENDED ACTION",
        "RISK",
        "VALIDATION",
        "ASSUMPTIONS",
        "SAFETY"
    ]

    for line in lines[
        start_index:
    ]:

        normalized = line.strip().upper()

        if normalized in known_sections:
            break

        section_lines.append(
            line
        )

    return "\n".join(
        section_lines
    ).strip()


def find_primary_wan_incident(
    incident_result
):
    """
    Find the correlated primary WAN incident.
    """

    for incident in incident_result.get(
        "active",
        []
    ):

        if (
            incident.get(
                "incident_type"
            )
            == "PRIMARY_WAN_FAILURE"
        ):

            return incident

    return None


def analyze_current_incident():
    """
    Collect current network state,
    correlate incidents, and analyze the
    primary WAN incident with Ollama.
    """

    snapshot = (
        collect_health_snapshot()
    )

    incident_result = (
        process_health_snapshot(
            snapshot
        )
    )

    incident = (
        find_primary_wan_incident(
            incident_result
        )
    )

    if incident is None:

        return {
            "status": "NO_INCIDENT",
            "incident": None,
            "analysis": None
        }

    analysis = analyze_incident(
        incident
    )

    incident["ai_analysis"] = analysis

    return {
        "status": analysis.get(
            "status",
            "UNKNOWN"
        ),

        "incident": incident,

        "analysis": analysis
    }


def display_ai_analysis(
    result
):

    print()
    print("========================================")
    print("NETPILOT AI INCIDENT ANALYSIS")
    print("========================================")
    print()

    print(
        "Status: "
        + result.get(
            "status",
            "UNKNOWN"
        )
    )

    incident = result.get(
        "incident"
    )

    if incident is None:

        print()
        print(
            "No PRIMARY_WAN_FAILURE incident "
            "is currently active."
        )

        return

    print()

    print(
        "Incident: "
        + incident.get(
            "incident_type",
            "UNKNOWN"
        )
    )

    print(
        "Router: "
        + incident.get(
            "router",
            "UNKNOWN"
        )
    )

    analysis = result.get(
        "analysis",
        {}
    )

    print()

    print(
        "ROOT CAUSE:"
    )

    print(
        analysis.get(
            "root_cause",
            "NOT_AVAILABLE"
        )
    )

    print()

    print(
        "CONFIDENCE:"
    )

    print(
        analysis.get(
            "confidence",
            "NOT_AVAILABLE"
        )
    )

    print()

    print(
        "FULL ANALYSIS:"
    )

    print(
        analysis.get(
            "analysis",
            "NOT_AVAILABLE"
        )
    )

    print()


if __name__ == "__main__":

    result = (
        analyze_current_incident()
    )

    display_ai_analysis(
        result
    )
