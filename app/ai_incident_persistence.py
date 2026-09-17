import json
import requests

from app.incident_store import (
    get_active_incidents,
    get_incident_evidence,
    get_latest_ai_analysis,
    store_ai_analysis,
    store_audit_event,
)


OLLAMA_URL = "http://192.168.1.217:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:32b"
OLLAMA_TIMEOUT = 600


def build_ai_prompt(incident, evidence):
    evidence_text = json.dumps(
        evidence,
        indent=2,
        default=str,
    )

    return f"""
You are NetPilot, a senior Cisco network operations assistant.

Your job is to analyze a network incident using ONLY the verified
evidence supplied below.

Do not invent facts.
Do not assume configuration that is not present in the evidence.
Do not generate Cisco configuration commands.
Do not execute changes.
Do not claim that a change was performed.

The application, not the AI, is responsible for determining whether
a configuration change is safe and whether an engineer approves it.

INCIDENT

Incident ID:
{incident["incident_id"]}

Router:
{incident["router"]}

Incident Type:
{incident["incident_type"]}

Status:
{incident["status"]}

Description:
{incident["description"]}

Impact:
{incident["impact"]}

Health:
{incident.get("health")}

Active Path:
{incident.get("active_path")}

Default Next Hop:
{incident.get("default_next_hop")}

VERIFIED EVIDENCE

{evidence_text}

Return ONLY valid JSON using exactly this structure:

{{
  "root_cause": "short technical root cause",
  "confidence": "HIGH|MEDIUM|LOW",
  "evidence": [
    "specific evidence item",
    "specific evidence item"
  ],
  "symptoms": [
    "observed symptom",
    "observed symptom"
  ],
  "customer_impact": "concise customer impact",
  "recommended_action": "high-level recommended engineering action",
  "risk": "LOW|MEDIUM|HIGH",
  "validation": "how an engineer should validate the recommended action",
  "assumptions": [
    "assumption if any"
  ]
}}

Rules:

1. Every factual conclusion must be supported by the supplied evidence.
2. If evidence is insufficient, say so.
3. Never fabricate an interface, IP address, BGP neighbor, route,
   configuration command, or topology detail.
4. Do not provide configuration commands.
5. Do not say that remediation has occurred.
6. Keep the response concise and operational.
"""


def call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1200,
        },
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "response",
        ""
    ).strip()


def parse_ai_response(raw_response):
    if not raw_response:
        raise ValueError(
            "Ollama returned an empty response."
        )

    cleaned = raw_response.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace(
            "```json",
            "",
            1
        )

        cleaned = cleaned.replace(
            "```",
            ""
        )

        cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)

    except json.JSONDecodeError as error:
        raise ValueError(
            "Ollama did not return valid JSON: "
            + str(error)
        )

    required_fields = [
        "root_cause",
        "confidence",
        "evidence",
        "symptoms",
        "customer_impact",
        "recommended_action",
        "risk",
        "validation",
        "assumptions",
    ]

    for field in required_fields:

        if field not in result:
            raise ValueError(
                "Ollama response is missing field: "
                + field
            )

    if result["confidence"] not in [
        "HIGH",
        "MEDIUM",
        "LOW",
    ]:
        raise ValueError(
            "Invalid confidence value."
        )

    if result["risk"] not in [
        "LOW",
        "MEDIUM",
        "HIGH",
    ]:
        raise ValueError(
            "Invalid risk value."
        )

    if not isinstance(
        result["evidence"],
        list
    ):
        raise ValueError(
            "AI evidence must be a list."
        )

    if not isinstance(
        result["symptoms"],
        list
    ):
        raise ValueError(
            "AI symptoms must be a list."
        )

    if not isinstance(
        result["assumptions"],
        list
    ):
        raise ValueError(
            "AI assumptions must be a list."
        )

    return result


def analyze_incident(incident):
    """
    Analyze one persisted incident.

    The database is checked first so an existing AI analysis
    is reused instead of calling Ollama again.
    """

    existing_analysis = get_latest_ai_analysis(
        incident["database_id"]
    )

    if existing_analysis is not None:

        return {
            "status": "EXISTS",
            "incident_id":
                incident["incident_id"],
            "analysis_id":
                existing_analysis["id"],
            "model":
                existing_analysis.get("model"),
            "analysis":
                existing_analysis,
        }

    evidence = get_incident_evidence(
        incident["database_id"]
    )

    if not evidence:

        return {
            "status": "FAILED",
            "incident_id":
                incident["incident_id"],
            "error":
                "No stored evidence exists "
                "for this incident.",
        }

    prompt = build_ai_prompt(
        incident,
        evidence,
    )

    try:

        raw_response = call_ollama(
            prompt
        )

        analysis = parse_ai_response(
            raw_response
        )

        analysis_id = store_ai_analysis(
            incident_database_id=
                incident["database_id"],

            model=
                OLLAMA_MODEL,

            root_cause=
                analysis["root_cause"],

            confidence=
                analysis["confidence"],

            evidence=
                analysis["evidence"],

            symptoms=
                analysis["symptoms"],

            customer_impact=
                analysis["customer_impact"],

            recommended_action=
                analysis["recommended_action"],

            risk=
                analysis["risk"],

            validation=
                analysis["validation"],

            assumptions=
                analysis["assumptions"],

            raw_response=
                raw_response,
        )

        store_audit_event(
            incident["database_id"],
            "AI_ANALYSIS_CREATED",
            "netpilot-ai",
            {
                "analysis_id":
                    analysis_id,

                "model":
                    OLLAMA_MODEL,

                "incident_id":
                    incident["incident_id"],
            },
        )

        return {
            "status": "SUCCESS",
            "incident_id":
                incident["incident_id"],
            "analysis_id":
                analysis_id,
            "model":
                OLLAMA_MODEL,
            "analysis":
                analysis,
        }

    except Exception as error:

        store_audit_event(
            incident["database_id"],
            "AI_ANALYSIS_FAILED",
            "netpilot-ai",
            {
                "incident_id":
                    incident["incident_id"],

                "error":
                    str(error),
            },
        )

        return {
            "status": "FAILED",
            "incident_id":
                incident["incident_id"],
            "error":
                str(error),
        }


def analyze_active_incidents():
    """
    Analyze all active PostgreSQL incidents.

    Existing AI analyses are reused.
    New incidents are analyzed with Ollama.
    """

    incidents = get_active_incidents()

    results = []

    for incident in incidents:

        print()
        print("Analyzing incident:")
        print(
            "  Incident ID: "
            + incident["incident_id"]
        )

        print(
            "  Router: "
            + incident["router"]
        )

        print(
            "  Type: "
            + incident["incident_type"]
        )

        result = analyze_incident(
            incident
        )

        if result["status"] == "EXISTS":

            print(
                "  AI analysis already exists."
            )

            print(
                "  Analysis ID: "
                + str(
                    result["analysis_id"]
                )
            )

        elif result["status"] == "SUCCESS":

            print(
                "  New AI analysis created."
            )

            print(
                "  Analysis ID: "
                + str(
                    result["analysis_id"]
                )
            )

        else:

            print(
                "  AI analysis failed."
            )

            print(
                "  Error: "
                + str(
                    result.get(
                        "error",
                        "UNKNOWN"
                    )
                )
            )

        results.append(result)

    return results


def analyze_persisted_incident(
    incident
):
    """
    Analyze a specific incident returned by
    the incident manager.

    PostgreSQL remains the source of truth for
    existing AI analysis.
    """

    if not incident:
        return {
            "status": "NO_INCIDENT",
            "incident": None,
            "analysis": None,
        }

    result = analyze_incident(
        incident
    )

    return {
        "status":
            result.get(
                "status",
                "UNKNOWN"
            ),

        "incident":
            incident,

        "analysis":
            result.get(
                "analysis"
            ),

        "analysis_id":
            result.get(
                "analysis_id"
            ),

        "model":
            result.get(
                "model"
            ),

        "error":
            result.get(
                "error"
            ),
    }


def display_results(results):
    print()
    print("========================================")
    print("NETPILOT AI INCIDENT ANALYSIS")
    print("========================================")
    print()

    if not results:

        print(
            "No active incidents require AI analysis."
        )

        print()

        return

    for result in results:

        print(
            "Incident ID: "
            + result.get(
                "incident_id",
                "UNKNOWN"
            )
        )

        print(
            "Status: "
            + result.get(
                "status",
                "UNKNOWN"
            )
        )

        if result.get("status") in [
            "SUCCESS",
            "EXISTS",
        ]:

            analysis = result.get(
                "analysis",
                {}
            )

            print(
                "Analysis ID: "
                + str(
                    result.get(
                        "analysis_id",
                        "UNKNOWN"
                    )
                )
            )

            print(
                "Root Cause: "
                + str(
                    analysis.get(
                        "root_cause",
                        "UNKNOWN"
                    )
                )
            )

            print(
                "Confidence: "
                + str(
                    analysis.get(
                        "confidence",
                        "UNKNOWN"
                    )
                )
            )

            print(
                "Risk: "
                + str(
                    analysis.get(
                        "risk",
                        "UNKNOWN"
                    )
                )
            )

            print(
                "Recommended Action: "
                + str(
                    analysis.get(
                        "recommended_action",
                        "UNKNOWN"
                    )
                )
            )

        else:

            print(
                "Error: "
                + str(
                    result.get(
                        "error",
                        "UNKNOWN"
                    )
                )
            )

        print()


if __name__ == "__main__":

    results = analyze_active_incidents()

    display_results(
        results
    )