from app.database import test_database_connection
from app.platform_health import get_platform_health
from app.reliability import get_reliability_data
from app.telemetry_anomaly_store import get_open_anomalies
from app.telemetry_correlation import get_open_correlations
from app.noc_data import get_noc_data


def check_database():
    result = test_database_connection()

    if result.get("status") == "CONNECTED":
        return {
            "name": "PostgreSQL",
            "status": "PASS",
            "details": (
                "Database connection successful."
            )
        }

    return {
        "name": "PostgreSQL",
        "status": "FAIL",
        "details": (
            result.get(
                "error",
                "Database connection failed."
            )
        )
    }


def check_platform_health():
    result = get_platform_health()

    status = result.get(
        "status",
        "UNKNOWN"
    )

    if status in [
        "HEALTHY",
        "WARNING"
    ]:
        return {
            "name": "Platform Health",
            "status": "PASS",
            "details": (
                "Platform health is "
                + str(status)
                + "."
            )
        }

    return {
        "name": "Platform Health",
        "status": "FAIL",
        "details": (
            "Platform health is "
            + str(status)
            + "."
        )
    }


def check_telemetry_state():
    noc_data = get_noc_data()

    anomalies = noc_data.get(
        "telemetry_anomalies",
        []
    )

    correlations = noc_data.get(
        "telemetry_correlations",
        []
    )

    incidents = noc_data.get(
        "telemetry_incidents",
        []
    )

    open_anomalies = [
        anomaly
        for anomaly in anomalies
        if anomaly.get("status") == "OPEN"
    ]

    open_correlations = [
        correlation
        for correlation in correlations
        if correlation.get("status")
        in ["OPEN", "ONGOING"]
    ]

    active_incidents = [
        incident
        for incident in incidents
        if incident.get("status")
        in [
            "OPEN",
            "IN_PROGRESS",
            "DEGRADED"
        ]
    ]

    if (
        not open_anomalies
        and not open_correlations
        and not active_incidents
    ):
        return {
            "name": "Telemetry Operational State",
            "status": "PASS",
            "details": (
                "No open anomalies, correlations, "
                "or active telemetry incidents."
            )
        }

    return {
        "name": "Telemetry Operational State",
        "status": "WARNING",
        "details": (
            "Open anomalies: "
            + str(len(open_anomalies))
            + ", open correlations: "
            + str(len(open_correlations))
            + ", active incidents: "
            + str(len(active_incidents))
        )
    }


def check_reliability():
    reliability = get_reliability_data()

    status = reliability.get(
        "reliability_status",
        reliability.get(
            "health_score",
            {}
        ).get(
            "status",
            "UNKNOWN"
        )
    )

    score = reliability.get(
        "reliability_score",
        reliability.get(
            "health_score",
            {}
        ).get(
            "score",
            0
        )
    )

    if status == "HEALTHY":
        validation_status = "PASS"

    elif status == "WARNING":
        validation_status = "WARNING"

    elif status == "UNKNOWN":
        validation_status = "WARNING"

    else:
        validation_status = "WARNING"

    return {
        "name": "Reliability Intelligence",
        "status": validation_status,
        "details": (
            "Reliability score: "
            + str(score)
            + " / 100"
            + ", status: "
            + str(status)
        )
    }


def check_noc_data():
    noc_data = get_noc_data()

    required_sections = [
        "telemetry_anomalies",
        "telemetry_correlations",
        "telemetry_ai_assessments",
        "telemetry_incidents",
        "recent_audit_events"
    ]

    missing = []

    for section in required_sections:
        if section not in noc_data:
            missing.append(section)

    if not missing:
        return {
            "name": "NOC Data Contract",
            "status": "PASS",
            "details": (
                "Required NOC data sections are available."
            )
        }

    return {
        "name": "NOC Data Contract",
        "status": "FAIL",
        "details": (
            "Missing sections: "
            + ", ".join(missing)
        )
    }


def calculate_release_status(results):
    for result in results:
        if result["status"] == "FAIL":
            return "NOT_READY"

    for result in results:
        if result["status"] == "WARNING":
            return "READY_WITH_WARNINGS"

    return "READY"


def display_results(results, release_status):
    print()
    print("========================================")
    print("NETPILOT RELEASE VALIDATION")
    print("========================================")
    print()

    for result in results:
        print(
            result["status"]
            + " | "
            + result["name"]
        )

        print(
            "  "
            + result["details"]
        )

        print()

    print("----------------------------------------")
    print(
        "RELEASE STATUS: "
        + release_status
    )
    print("----------------------------------------")
    print()


def main():
    results = []

    results.append(
        check_database()
    )

    results.append(
        check_platform_health()
    )

    results.append(
        check_telemetry_state()
    )

    results.append(
        check_reliability()
    )

    results.append(
        check_noc_data()
    )

    release_status = calculate_release_status(
        results
    )

    display_results(
        results,
        release_status
    )


if __name__ == "__main__":
    main()