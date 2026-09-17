from flask import Flask, render_template, redirect, url_for

from app.monitoring import collect_health_snapshot
from app.incident_manager import (
    process_health_snapshot,
    normalize_health_snapshot
)
from app.incident_orchestrator import (
    get_primary_wan_incident,
    run_ai_diagnosis
)
from app.noc_data import get_noc_data
from app.noc_service import build_capacity_intelligence


app = Flask(__name__)


def build_dashboard_data():
    """
    Build the current dashboard state.

    Network health is collected from Cisco devices.

    Persisted telemetry, correlations, AI assessments,
    telemetry incidents, audit events, and capacity
    intelligence are retrieved/calculated for dashboard
    presentation.

    Dashboard loading does not execute telemetry collection,
    anomaly detection, AI analysis, or remediation.
    """

    raw_health_snapshot = collect_health_snapshot()

    health_snapshot = normalize_health_snapshot(
        raw_health_snapshot
    )

    incident_result = process_health_snapshot(
        raw_health_snapshot
    )

    noc_data = get_noc_data()

    telemetry_anomalies = noc_data.get(
        "telemetry_anomalies",
        []
    )

    telemetry_correlations = noc_data.get(
        "telemetry_correlations",
        []
    )

    telemetry_ai_assessments = noc_data.get(
        "telemetry_ai_assessments",
        []
    )

    telemetry_incidents = noc_data.get(
        "telemetry_incidents",
        []
    )

    recent_audit_events = noc_data.get(
        "recent_audit_events",
        []
    )

    capacity = build_capacity_intelligence()

    total_routers = len(
        health_snapshot
    )

    online = len(
        [
            router
            for router in health_snapshot
            if router.get("availability") == "ONLINE"
        ]
    )

    healthy = len(
        [
            router
            for router in health_snapshot
            if router.get("health") == "HEALTHY"
        ]
    )

    degraded = len(
        [
            router
            for router in health_snapshot
            if router.get("health") == "DEGRADED"
        ]
    )

    critical = len(
        [
            router
            for router in health_snapshot
            if router.get("health") == "CRITICAL"
        ]
    )

    open_telemetry_anomalies = len(
        [
            anomaly
            for anomaly in telemetry_anomalies
            if anomaly.get("status") == "OPEN"
        ]
    )

    open_telemetry_correlations = len(
        [
            correlation
            for correlation in telemetry_correlations
            if correlation.get("status") == "OPEN"
        ]
    )

    return {
        "health": health_snapshot,

        "incidents": incident_result,

        "telemetry_anomalies":
            telemetry_anomalies,

        "telemetry_correlations":
            telemetry_correlations,

        "telemetry_ai_assessments":
            telemetry_ai_assessments,

        "telemetry_incidents":
            telemetry_incidents,

        "recent_audit_events":
            recent_audit_events,

        "capacity":
            capacity,

        "summary": {
            "total": total_routers,
            "online": online,
            "healthy": healthy,
            "degraded": degraded,
            "critical": critical,

            "active_incidents":
                incident_result.get(
                    "active_count",
                    0
                ),

            "telemetry_anomalies":
                len(telemetry_anomalies),

            "open_telemetry_anomalies":
                open_telemetry_anomalies,

            "telemetry_correlations":
                len(telemetry_correlations),

            "open_telemetry_correlations":
                open_telemetry_correlations,

            "telemetry_ai_assessments":
                len(telemetry_ai_assessments),

            "telemetry_incidents":
                len(telemetry_incidents),

            "capacity_status":
                capacity.get(
                    "status",
                    "UNKNOWN"
                ),

            "capacity_interfaces_analyzed":
                capacity.get(
                    "interfaces_analyzed",
                    0
                ),

            "capacity_forecast_available":
                capacity.get(
                    "forecast_available",
                    0
                ),

            "capacity_threshold_reached":
                capacity.get(
                    "threshold_reached",
                    0
                ),

            "capacity_increasing_trends":
                capacity.get(
                    "increasing_trends",
                    0
                ),

            "capacity_meaningful_risks":
                capacity.get(
                    "meaningful_risk_count",
                    0
                )
        }
    }


@app.route("/")
def dashboard():
    data = build_dashboard_data()

    return render_template(
        "dashboard.html",

        health=data["health"],

        incidents=data["incidents"],

        summary=data["summary"],

        telemetry_anomalies=
            data["telemetry_anomalies"],

        telemetry_correlations=
            data["telemetry_correlations"],

        telemetry_ai_assessments=
            data["telemetry_ai_assessments"],

        telemetry_incidents=
            data["telemetry_incidents"],

        recent_audit_events=
            data["recent_audit_events"],

        capacity=data["capacity"]
    )


@app.route("/ai/diagnose")
def ai_diagnose():
    """
    Run AI diagnosis for the currently active
    primary WAN incident.

    AI only provides analysis.
    """

    raw_health_snapshot = collect_health_snapshot()

    incident_result = process_health_snapshot(
        raw_health_snapshot
    )

    incident = get_primary_wan_incident(
        incident_result
    )

    if incident is not None:
        run_ai_diagnosis(
            incident_result
        )

    return redirect(
        url_for("dashboard")
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )