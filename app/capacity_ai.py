import json
import urllib.request
import urllib.error

from app.capacity_forecast import (
    get_interface_samples,
    group_samples,
    forecast_all_interfaces
)

from app.capacity_trends import (
    analyze_all_interfaces
)


OLLAMA_URL = "http://192.168.1.217:11434/api/generate"

OLLAMA_MODEL = "qwen2.5:32b"

FORECAST_THRESHOLD = 75.0

MAX_AI_RISKS = 10


def get_capacity_intelligence():
    """
    Build deterministic capacity intelligence.

    This function does not call Ollama.

    All utilization, trend, threshold, and forecast
    values originate from the NetPilot deterministic
    engineering pipeline.
    """

    rows = get_interface_samples()

    if not rows:
        return {
            "forecasts": [],
            "trends": []
        }

    grouped_samples = group_samples(
        rows
    )

    forecast_results = forecast_all_interfaces(
        grouped_samples
    )

    trend_results = analyze_all_interfaces(
        grouped_samples
    )

    return {
        "forecasts":
            forecast_results,

        "trends":
            trend_results
    }


def select_meaningful_risks(
    capacity_intelligence
):
    """
    Select capacity findings that are useful
    for AI engineering assessment.

    Only deterministic risk states are passed
    to Ollama.

    Increasing trends are included as engineering
    context even when they do not yet have an
    actionable forecast.
    """

    forecasts = capacity_intelligence.get(
        "forecasts",
        []
    )

    trends = capacity_intelligence.get(
        "trends",
        []
    )

    trend_lookup = {}

    for trend in trends:

        key = (
            trend.get("router"),
            trend.get("interface")
        )

        trend_lookup[key] = trend

    findings = []

    for forecast in forecasts:

        router = forecast.get(
            "router"
        )

        interface_name = forecast.get(
            "interface"
        )

        key = (
            router,
            interface_name
        )

        trend = trend_lookup.get(
            key,
            {}
        )

        overall_status = forecast.get(
            "overall_status",
            "UNKNOWN"
        )

        overall_trend = trend.get(
            "overall_trend",
            "UNKNOWN"
        )

        include_finding = False

        if overall_status in (
            "FORECAST_AVAILABLE",
            "THRESHOLD_REACHED"
        ):

            include_finding = True

        elif overall_trend == "INCREASING":

            include_finding = True

        if not include_finding:
            continue

        input_forecast = forecast.get(
            "input_forecast",
            {}
        )

        output_forecast = forecast.get(
            "output_forecast",
            {}
        )

        finding = {
            "router":
                router,

            "interface":
                interface_name,

            "threshold":
                forecast.get(
                    "threshold",
                    FORECAST_THRESHOLD
                ),

            "overall_status":
                overall_status,

            "days_to_threshold":
                forecast.get(
                    "days_to_threshold"
                ),

            "input_current_utilization":
                input_forecast.get(
                    "current_utilization"
                ),

            "input_slope_per_hour":
                input_forecast.get(
                    "slope_per_hour"
                ),

            "input_forecast_status":
                input_forecast.get(
                    "status",
                    "UNKNOWN"
                ),

            "output_current_utilization":
                output_forecast.get(
                    "current_utilization"
                ),

            "output_slope_per_hour":
                output_forecast.get(
                    "slope_per_hour"
                ),

            "output_forecast_status":
                output_forecast.get(
                    "status",
                    "UNKNOWN"
                ),

            "overall_trend":
                overall_trend,

            "input_trend":
                trend.get(
                    "input_trend",
                    "UNKNOWN"
                ),

            "output_trend":
                trend.get(
                    "output_trend",
                    "UNKNOWN"
                ),

            "sample_count":
                trend.get(
                    "sample_count",
                    0
                )
        }

        findings.append(
            finding
        )

    findings.sort(
        key=lambda item: (
            item.get(
                "days_to_threshold"
            )
            if item.get(
                "days_to_threshold"
            ) is not None
            else float("inf")
        )
    )

    return findings[
        :MAX_AI_RISKS
    ]


def build_ai_prompt(findings):
    """
    Build a structured engineering prompt.

    The prompt explicitly tells Ollama that the
    supplied values are deterministic evidence
    and that it must not invent missing data.
    """

    evidence = json.dumps(
        findings,
        indent=2,
        default=str
    )

    prompt = """
You are NetPilot's network capacity engineering assistant.

Your role is to interpret deterministic capacity evidence
collected from a Cisco network.

The Python system has already calculated:

- current utilization
- utilization trend
- utilization slope
- capacity threshold
- threshold forecast
- forecast status
- telemetry sample count

Do not invent values.

Do not change any calculated values.

Do not create a new forecast.

Do not recommend an automatic configuration change.

Do not claim that a circuit upgrade is definitely required
unless the supplied evidence supports that conclusion.

Treat short telemetry history as a limitation.

Your job is to provide an engineering assessment that helps
a Cisco network engineer decide what should be investigated.

For each finding, provide:

1. Router and interface
2. Engineering assessment
3. Primary concern
4. Recommended investigation
5. Customer-facing recommendation
6. Confidence: HIGH, MEDIUM, or LOW

The customer-facing recommendation should be cautious and
appropriate for an FDE/customer engagement.

If the evidence is weak because of limited historical data,
explicitly state that additional telemetry collection is needed.

Return valid JSON only using this structure:

{
  "assessment": "overall assessment",
  "findings": [
    {
      "router": "R1",
      "interface": "GigabitEthernet1",
      "engineering_assessment": "...",
      "primary_concern": "...",
      "recommended_investigation": "...",
      "customer_recommendation": "...",
      "confidence": "MEDIUM"
    }
  ]
}

Deterministic capacity evidence:

""" + evidence

    return prompt


def call_ollama(prompt):
    """
    Send the engineering evidence to Ollama.

    This function is advisory only.

    No Cisco configuration or NetPilot state is
    modified by this function.
    """

    payload = {
        "model":
            OLLAMA_MODEL,

        "prompt":
            prompt,

        "stream":
            False,

        "format":
            "json"
    }

    request_data = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        OLLAMA_URL,
        data=request_data,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            response_data = (
                response.read()
                .decode("utf-8")
            )

        result = json.loads(
            response_data
        )

        response_text = result.get(
            "response",
            ""
        )

        if not response_text:

            return {
                "status":
                    "FAILED",

                "error":
                    "Ollama returned an empty response."
            }

        try:

            assessment = json.loads(
                response_text
            )

        except json.JSONDecodeError:

            return {
                "status":
                    "FAILED",

                "error":
                    "Ollama returned invalid JSON.",

                "raw_response":
                    response_text
            }

        return {
            "status":
                "SUCCESS",

            "assessment":
                assessment
        }

    except urllib.error.URLError as error:

        return {
            "status":
                "FAILED",

            "error":
                "Unable to connect to Ollama: "
                + str(error)
        }

    except Exception as error:

        return {
            "status":
                "FAILED",

            "error":
                "Ollama request failed: "
                + str(error)
        }


def display_assessment(
    result,
    findings
):
    """
    Display the Ollama engineering assessment.
    """

    print()
    print(
        "========================================"
    )

    print(
        "NETPILOT AI CAPACITY ASSESSMENT"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Model: "
        + OLLAMA_MODEL
    )

    print(
        "Forecast Threshold: "
        + str(
            FORECAST_THRESHOLD
        )
        + "%"
    )

    print(
        "Deterministic Findings: "
        + str(
            len(findings)
        )
    )

    print()

    if result.get(
        "status"
    ) != "SUCCESS":

        print(
            "AI Status: FAILED"
        )

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

        return

    print(
        "AI Status: SUCCESS"
    )

    print()

    assessment = result.get(
        "assessment",
        {}
    )

    overall_assessment = assessment.get(
        "assessment",
        "No overall assessment provided."
    )

    print(
        "Overall Assessment"
    )

    print(
        "----------------------------------------"
    )

    print(
        overall_assessment
    )

    print()

    ai_findings = assessment.get(
        "findings",
        []
    )

    if not ai_findings:

        print(
            "No AI findings returned."
        )

        print()

        return

    print(
        "Engineering Findings"
    )

    print(
        "----------------------------------------"
    )

    for finding in ai_findings:

        print(
            str(
                finding.get(
                    "router",
                    "UNKNOWN"
                )
            )
            + " | "
            + str(
                finding.get(
                    "interface",
                    "UNKNOWN"
                )
            )
        )

        print()

        print(
            "  Engineering Assessment: "
            + str(
                finding.get(
                    "engineering_assessment",
                    "N/A"
                )
            )
        )

        print()

        print(
            "  Primary Concern: "
            + str(
                finding.get(
                    "primary_concern",
                    "N/A"
                )
            )
        )

        print()

        print(
            "  Recommended Investigation: "
            + str(
                finding.get(
                    "recommended_investigation",
                    "N/A"
                )
            )
        )

        print()

        print(
            "  Customer Recommendation: "
            + str(
                finding.get(
                    "customer_recommendation",
                    "N/A"
                )
            )
        )

        print()

        print(
            "  Confidence: "
            + str(
                finding.get(
                    "confidence",
                    "UNKNOWN"
                )
            )
        )

        print()


def main():
    print()
    print(
        "Collecting deterministic capacity intelligence..."
    )

    capacity_intelligence = (
        get_capacity_intelligence()
    )

    findings = select_meaningful_risks(
        capacity_intelligence
    )

    if not findings:

        print()

        print(
            "No meaningful capacity findings "
            "require AI assessment."
        )

        print()

        return

    print(
        "Meaningful findings selected: "
        + str(
            len(findings)
        )
    )

    print()

    prompt = build_ai_prompt(
        findings
    )

    print(
        "Sending capacity evidence to Ollama..."
    )

    result = call_ollama(
        prompt
    )

    display_assessment(
        result,
        findings
    )


if __name__ == "__main__":

    main()
