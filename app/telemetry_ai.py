import json
import requests

from app.database import get_connection
from app.telemetry_correlation import get_open_correlations


OLLAMA_URL = "http://192.168.1.217:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:32b"
OLLAMA_TIMEOUT = 600


def get_existing_ai_analysis(correlation_id):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    assessment,
                    likely_explanation,
                    customer_impact,
                    risk,
                    confidence,
                    observed_evidence,
                    recommended_investigation,
                    assumptions,
                    created_at
                FROM telemetry_ai_analysis
                WHERE correlation_id = %s
                ORDER BY id DESC
                LIMIT 1;
                """,
                (correlation_id,)
            )

            return cursor.fetchone()

    except Exception as error:
        print(
            "Failed to retrieve existing AI analysis: "
            + str(error)
        )
        return None

    finally:
        if connection is not None:
            connection.close()


def get_correlation_evidence(correlation_id):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    router,
                    interface_name,
                    correlation_type,
                    severity,
                    summary,
                    source_anomaly_ids,
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    status
                FROM telemetry_correlations
                WHERE id = %s;
                """,
                (correlation_id,)
            )

            correlation = cursor.fetchone()

            if correlation is None:
                return None

            anomaly_ids = correlation[6]

            cursor.execute(
                """
                SELECT
                    id,
                    router,
                    interface_name,
                    severity,
                    anomaly_type,
                    message,
                    first_detected_at,
                    last_detected_at,
                    occurrence_count,
                    status
                FROM telemetry_anomalies
                WHERE id IN (
                    SELECT
                        jsonb_array_elements_text(
                            %s::jsonb
                        )::BIGINT
                )
                ORDER BY id;
                """,
                (json.dumps(anomaly_ids),)
            )

            anomalies = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    id,
                    router,
                    interface_name,
                    interface_status,
                    protocol_status,
                    input_rate_bps,
                    output_rate_bps,
                    input_packets,
                    output_packets,
                    input_errors,
                    output_errors,
                    collected_at
                FROM interface_telemetry
                WHERE router = %s
                  AND interface_name = %s
                ORDER BY collected_at DESC
                LIMIT 20;
                """,
                (
                    correlation[1],
                    correlation[2]
                )
            )

            telemetry = cursor.fetchall()

        return {
            "correlation": correlation,
            "anomalies": anomalies,
            "telemetry": telemetry
        }

    except Exception as error:
        print(
            "Failed to collect telemetry AI evidence: "
            + str(error)
        )
        return None

    finally:
        if connection is not None:
            connection.close()


def build_evidence_package(evidence):
    correlation = evidence["correlation"]
    anomalies = evidence["anomalies"]
    telemetry = evidence["telemetry"]

    package = {
        "correlation": {
            "id": correlation[0],
            "router": correlation[1],
            "interface": correlation[2],
            "type": correlation[3],
            "severity": correlation[4],
            "summary": correlation[5],
            "source_anomaly_ids": correlation[6],
            "first_detected_at": str(correlation[7]),
            "last_detected_at": str(correlation[8]),
            "occurrence_count": correlation[9],
            "status": correlation[10]
        },
        "anomalies": [],
        "telemetry": []
    }

    for anomaly in anomalies:
        package["anomalies"].append(
            {
                "id": anomaly[0],
                "router": anomaly[1],
                "interface": anomaly[2],
                "severity": anomaly[3],
                "type": anomaly[4],
                "message": anomaly[5],
                "first_detected_at": str(anomaly[6]),
                "last_detected_at": str(anomaly[7]),
                "occurrence_count": anomaly[8],
                "status": anomaly[9]
            }
        )

    for sample in telemetry:
        package["telemetry"].append(
            {
                "id": sample[0],
                "router": sample[1],
                "interface": sample[2],
                "interface_status": sample[3],
                "protocol_status": sample[4],
                "input_rate_bps": sample[5],
                "output_rate_bps": sample[6],
                "input_packets": sample[7],
                "output_packets": sample[8],
                "input_errors": sample[9],
                "output_errors": sample[10],
                "collected_at": str(sample[11])
            }
        )

    return package


def build_ai_prompt(evidence_package):
    evidence_json = json.dumps(
        evidence_package,
        indent=2
    )

    return f"""
You are NetPilot's network operations analysis assistant.

Analyze ONLY the evidence provided below.

You are not allowed to execute commands.
You are not allowed to modify network configuration.
You are not allowed to claim that remediation has occurred.

Separate observed facts from hypotheses.

Return ONLY valid JSON using exactly these fields:

{{
  "assessment": "",
  "observed_evidence": [],
  "likely_explanation": "",
  "customer_impact": "",
  "recommended_investigation": [],
  "risk": "",
  "confidence": "",
  "assumptions": []
}}

Rules:

- assessment: concise engineer-readable summary.
- observed_evidence: facts directly supported by the evidence.
- likely_explanation: possible explanation, not a confirmed root cause.
- customer_impact: possible operational/customer impact.
- recommended_investigation: investigation steps only.
- Do not claim that any remediation occurred.
- risk must be LOW, MEDIUM, or HIGH.
- confidence must be LOW, MEDIUM, or HIGH.
- assumptions must identify missing information.

Evidence:

{evidence_json}
"""


def call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1500
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        return data.get("response", "")

    except Exception as error:
        print(
            "Ollama request failed: "
            + str(error)
        )
        return None


def parse_ai_response(response_text):
    if not response_text:
        return None

    cleaned = response_text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if len(lines) >= 3:
            cleaned = "\n".join(
                lines[1:-1]
            ).strip()

    try:
        result = json.loads(cleaned)

    except json.JSONDecodeError as error:
        print(
            "Ollama returned invalid JSON: "
            + str(error)
        )
        return None

    required_fields = [
        "assessment",
        "observed_evidence",
        "likely_explanation",
        "customer_impact",
        "recommended_investigation",
        "risk",
        "confidence",
        "assumptions"
    ]

    for field in required_fields:
        if field not in result:
            print(
                "Ollama response missing field: "
                + field
            )
            return None

    if result["risk"] not in [
        "LOW",
        "MEDIUM",
        "HIGH"
    ]:
        print("Invalid AI risk value.")
        return None

    if result["confidence"] not in [
        "LOW",
        "MEDIUM",
        "HIGH"
    ]:
        print("Invalid AI confidence value.")
        return None

    if not isinstance(
        result["observed_evidence"],
        list
    ):
        print("Invalid observed_evidence.")
        return None

    if not isinstance(
        result["recommended_investigation"],
        list
    ):
        print("Invalid recommended_investigation.")
        return None

    if not isinstance(
        result["assumptions"],
        list
    ):
        print("Invalid assumptions.")
        return None

    return result


def save_ai_analysis(
    correlation_id,
    analysis
):
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO telemetry_ai_analysis (
                    correlation_id,
                    status,
                    assessment,
                    likely_explanation,
                    customer_impact,
                    risk,
                    confidence,
                    observed_evidence,
                    recommended_investigation,
                    assumptions
                )
                VALUES (
                    %s,
                    'COMPLETE',
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::jsonb,
                    %s::jsonb,
                    %s::jsonb
                )
                RETURNING id;
                """,
                (
                    correlation_id,
                    analysis["assessment"],
                    analysis["likely_explanation"],
                    analysis["customer_impact"],
                    analysis["risk"],
                    analysis["confidence"],
                    json.dumps(
                        analysis["observed_evidence"]
                    ),
                    json.dumps(
                        analysis[
                            "recommended_investigation"
                        ]
                    ),
                    json.dumps(
                        analysis["assumptions"]
                    )
                )
            )

            analysis_id = cursor.fetchone()[0]

        connection.commit()

        return analysis_id

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "Failed to save telemetry AI analysis: "
            + str(error)
        )

        return None

    finally:
        if connection is not None:
            connection.close()


def build_result_from_database(row):
    return {
        "analysis_id": row[0],
        "status": row[1],
        "analysis": {
            "assessment": row[2],
            "likely_explanation": row[3],
            "customer_impact": row[4],
            "risk": row[5],
            "confidence": row[6],
            "observed_evidence": row[7],
            "recommended_investigation": row[8],
            "assumptions": row[9]
        },
        "created_at": row[10]
    }


def analyze_correlation(correlation_id):
    existing = get_existing_ai_analysis(
        correlation_id
    )

    if existing is not None:
        print(
            "AI analysis already exists for "
            "correlation "
            + str(correlation_id)
        )

        result = build_result_from_database(
            existing
        )

        result["reused"] = True

        return result

    evidence = get_correlation_evidence(
        correlation_id
    )

    if evidence is None:
        print(
            "No evidence found for correlation "
            + str(correlation_id)
        )
        return None

    evidence_package = build_evidence_package(
        evidence
    )

    prompt = build_ai_prompt(
        evidence_package
    )

    print()
    print("Sending telemetry evidence to Ollama...")
    print(
        "Model: "
        + OLLAMA_MODEL
    )

    response_text = call_ollama(prompt)

    if response_text is None:
        return None

    analysis = parse_ai_response(
        response_text
    )

    if analysis is None:
        return None

    analysis_id = save_ai_analysis(
        correlation_id,
        analysis
    )

    if analysis_id is None:
        return None

    return {
        "analysis_id": analysis_id,
        "status": "COMPLETE",
        "analysis": analysis,
        "created_at": None,
        "reused": False
    }


def display_analysis(result):
    if result is None:
        print("No AI analysis available.")
        return

    analysis = result["analysis"]

    print()
    print("========================================")
    print("NETPILOT AI TELEMETRY ASSESSMENT")
    print("========================================")
    print()

    print(
        "Analysis ID: "
        + str(result["analysis_id"])
    )

    print(
        "Status: "
        + str(result["status"])
    )

    print(
        "Reused existing analysis: "
        + str(result.get("reused", False))
    )

    print()

    print("Assessment:")
    print(
        analysis["assessment"]
    )

    print()

    print("Observed Evidence:")

    for item in analysis["observed_evidence"]:
        print(
            "- "
            + str(item)
        )

    print()

    print("Likely Explanation:")
    print(
        analysis["likely_explanation"]
    )

    print()

    print("Customer Impact:")
    print(
        analysis["customer_impact"]
    )

    print()

    print("Recommended Investigation:")

    for item in analysis[
        "recommended_investigation"
    ]:
        print(
            "- "
            + str(item)
        )

    print()

    print(
        "Risk: "
        + str(analysis["risk"])
    )

    print(
        "Confidence: "
        + str(analysis["confidence"])
    )

    print()

    print("Assumptions:")

    for item in analysis["assumptions"]:
        print(
            "- "
            + str(item)
        )

    print()


def main():
    correlations = get_open_correlations()

    if not correlations:
        print(
            "No open telemetry correlations."
        )
        return

    print()
    print("========================================")
    print("NETPILOT TELEMETRY AI")
    print("========================================")
    print()

    print(
        "Open correlations: "
        + str(len(correlations))
    )

    for correlation in correlations:
        correlation_id = correlation[0]

        print()
        print(
            "Analyzing correlation "
            + str(correlation_id)
            + "..."
        )

        result = analyze_correlation(
            correlation_id
        )

        display_analysis(result)


if __name__ == "__main__":
    main()