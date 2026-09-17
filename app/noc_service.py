from app.monitoring import collect_health_snapshot

from app.incident_manager import (
    process_health_snapshot,
    normalize_health_snapshot
)

from app.noc_data import get_noc_data
from app.platform_health import get_platform_health
from app.reliability import get_reliability_data

from app.capacity_forecast import (
    get_interface_samples,
    group_samples,
    forecast_all_interfaces
)

from app.capacity_trends import (
    analyze_all_interfaces
)


CAPACITY_FORECAST_THRESHOLD = 75.0


def normalize_reliability_data(reliability):
    """
    Build a stable NOC-facing reliability view.

    The reliability module contains detailed workflow, stage,
    failure-analysis, and health-score structures. This function
    converts those structures into a consistent NOC contract.

    The explicit noc_summary values are preferred. Detailed
    reliability structures are used as fallbacks.

    This function is read-only.
    """

    health_score = reliability.get(
        "health_score",
        {}
    )

    workflow = reliability.get(
        "workflow",
        {}
    )

    failure_analysis = reliability.get(
        "failure_analysis",
        {}
    )

    recent_failures = reliability.get(
        "recent_failures",
        []
    )

    noc_summary = reliability.get(
        "noc_summary",
        {}
    )

    reliability_status = noc_summary.get(
        "reliability_status",
        reliability.get(
            "reliability_status",
            health_score.get(
                "status",
                "UNKNOWN"
            )
        )
    )

    reliability_score = noc_summary.get(
        "reliability_score",
        reliability.get(
            "reliability_score",
            health_score.get(
                "score",
                0
            )
        )
    )

    workflow_runs_24h = noc_summary.get(
        "workflow_runs_24h",
        workflow.get(
            "total_runs_24h",
            0
        )
    )

    workflow_successful_runs_24h = noc_summary.get(
        "workflow_successful_runs_24h",
        workflow.get(
            "successful_runs_24h",
            0
        )
    )

    workflow_failed_runs_24h = noc_summary.get(
        "workflow_failed_runs_24h",
        workflow.get(
            "failed_runs_24h",
            0
        )
    )

    workflow_success_rate = noc_summary.get(
        "workflow_success_rate",
        workflow.get(
            "success_rate_24h",
            "UNKNOWN"
        )
    )

    failed_stage_executions = noc_summary.get(
        "failed_stage_executions",
        failure_analysis.get(
            "total_failed_stages",
            0
        )
    )

    most_failure_prone_stage = noc_summary.get(
        "most_failure_prone_stage"
    )

    if most_failure_prone_stage is None:

        most_failed_stage = failure_analysis.get(
            "most_failed_stage"
        )

        if isinstance(
            most_failed_stage,
            dict
        ):

            most_failure_prone_stage = (
                most_failed_stage.get(
                    "stage_name",
                    "UNKNOWN"
                )
            )

        else:

            most_failure_prone_stage = (
                most_failed_stage
            )

    recent_workflow_failures = noc_summary.get(
        "recent_workflow_failures",
        len(recent_failures)
    )

    return {
        "status":
            reliability_status,

        "score":
            reliability_score,

        "workflow_runs_24h":
            workflow_runs_24h,

        "workflow_successful_runs_24h":
            workflow_successful_runs_24h,

        "workflow_failed_runs_24h":
            workflow_failed_runs_24h,

        "workflow_success_rate":
            workflow_success_rate,

        "average_duration_ms":
            workflow.get(
                "average_duration_ms",
                "UNKNOWN"
            ),

        "fastest_duration_ms":
            workflow.get(
                "fastest_duration_ms",
                "UNKNOWN"
            ),

        "slowest_duration_ms":
            workflow.get(
                "slowest_duration_ms",
                "UNKNOWN"
            ),

        "failed_stage_executions":
            failed_stage_executions,

        "most_failure_prone_stage":
            most_failure_prone_stage,

        "recent_workflow_failures":
            recent_workflow_failures,

        "reasons":
            health_score.get(
                "reasons",
                []
            )
    }


def format_reliability_score(score):
    """
    Format the reliability score for NOC display.
    """

    if isinstance(
        score,
        (int, float)
    ):

        return "{:.1f}".format(
            score
        )

    return str(score)


def format_percentage(value):
    """
    Format a percentage value consistently.

    Numeric values are displayed with one decimal place.
    UNKNOWN and other non-numeric values are preserved.
    """

    if isinstance(
        value,
        (int, float)
    ):

        return "{:.1f}".format(
            value
        )

    return str(value)


def build_capacity_intelligence():
    """
    Build a read-only NOC-facing capacity intelligence view.

    Capacity information is derived from the existing
    interface_capacity and interface_telemetry data.

    The capacity forecast and trend engines perform
    deterministic analysis only.

    Only actionable capacity forecasts and threshold
    breaches are treated as meaningful NOC risks.

    Long-range forecasts and non-actionable forecasts
    remain in the detailed forecast data but are not
    promoted as NOC risks.

    This function does not perform Cisco configuration
    changes, telemetry collection, remediation, or AI analysis.
    """

    rows = get_interface_samples()

    if not rows:

        return {
            "status":
                "NO_DATA",

            "threshold":
                CAPACITY_FORECAST_THRESHOLD,

            "interfaces_analyzed":
                0,

            "forecast_available":
                0,

            "threshold_reached":
                0,

            "increasing_trends":
                0,

            "meaningful_risks":
                [],

            "forecasts":
                [],

            "trends":
                []
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

    forecast_available = 0

    threshold_reached = 0

    increasing_trends = 0

    meaningful_risks = []

    for result in forecast_results:

        overall_status = result.get(
            "overall_status",
            "UNKNOWN"
        )

        if overall_status == "FORECAST_AVAILABLE":

            forecast_available += 1

            meaningful_risks.append(
                result
            )

        elif overall_status == "THRESHOLD_REACHED":

            threshold_reached += 1

            meaningful_risks.append(
                result
            )

    for trend in trend_results:

        if trend.get(
            "overall_trend"
        ) == "INCREASING":

            increasing_trends += 1

    meaningful_risks.sort(
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

    if threshold_reached > 0:

        status = "CRITICAL"

    elif meaningful_risks:

        status = "WATCH"

    elif increasing_trends > 0:

        status = "WATCH"

    else:

        status = "HEALTHY"

    return {
        "status":
            status,

        "threshold":
            CAPACITY_FORECAST_THRESHOLD,

        "interfaces_analyzed":
            len(
                grouped_samples
            ),

        "forecast_available":
            forecast_available,

        "threshold_reached":
            threshold_reached,

        "increasing_trends":
            increasing_trends,

        "meaningful_risks":
            meaningful_risks,

        "forecasts":
            forecast_results,

        "trends":
            trend_results
    }


def build_noc_snapshot():
    """
    Build a unified, read-only NOC snapshot.

    Network health and incident state are collected from
    the existing monitoring and incident systems.

    Persisted telemetry, AI assessments, telemetry incidents,
    and audit history are read from PostgreSQL.

    NetPilot platform health is collected for PostgreSQL,
    Ollama, and the workflow engine.

    Workflow reliability intelligence is collected from the
    existing workflow execution history.

    Capacity intelligence is calculated from the existing
    capacity and telemetry datasets.

    This function does not perform configuration changes,
    remediation, telemetry collection, or new AI analysis.
    """

    raw_health_snapshot = collect_health_snapshot()

    health = normalize_health_snapshot(
        raw_health_snapshot
    )

    incidents = process_health_snapshot(
        raw_health_snapshot
    )

    persisted_noc_data = get_noc_data()

    platform_health = get_platform_health()

    reliability = get_reliability_data()

    reliability_noc = normalize_reliability_data(
        reliability
    )

    capacity = build_capacity_intelligence()

    total = len(
        health
    )

    online = len(
        [
            router
            for router in health
            if router.get(
                "availability"
            ) == "ONLINE"
        ]
    )

    healthy = len(
        [
            router
            for router in health
            if router.get(
                "health"
            ) == "HEALTHY"
        ]
    )

    degraded = len(
        [
            router
            for router in health
            if router.get(
                "health"
            ) == "DEGRADED"
        ]
    )

    critical = len(
        [
            router
            for router in health
            if router.get(
                "health"
            ) == "CRITICAL"
        ]
    )

    telemetry_anomalies = persisted_noc_data.get(
        "telemetry_anomalies",
        []
    )

    telemetry_correlations = persisted_noc_data.get(
        "telemetry_correlations",
        []
    )

    telemetry_ai_assessments = persisted_noc_data.get(
        "telemetry_ai_assessments",
        []
    )

    telemetry_incidents = persisted_noc_data.get(
        "telemetry_incidents",
        []
    )

    recent_audit_events = persisted_noc_data.get(
        "recent_audit_events",
        []
    )

    open_anomalies = len(
        [
            anomaly
            for anomaly in telemetry_anomalies
            if anomaly.get(
                "status"
            ) == "OPEN"
        ]
    )

    open_correlations = len(
        [
            correlation
            for correlation in telemetry_correlations
            if correlation.get(
                "status"
            ) in [
                "OPEN",
                "ONGOING"
            ]
        ]
    )

    active_telemetry_incidents = len(
        [
            incident
            for incident in telemetry_incidents
            if incident.get(
                "status"
            ) in [
                "OPEN",
                "IN_PROGRESS",
                "DEGRADED"
            ]
        ]
    )

    return {
        "health":
            health,

        "incidents":
            incidents,

        "platform_health":
            platform_health,

        "reliability":
            reliability,

        "reliability_noc":
            reliability_noc,

        "capacity":
            capacity,

        "telemetry": {
            "anomalies":
                telemetry_anomalies,

            "correlations":
                telemetry_correlations,

            "ai_assessments":
                telemetry_ai_assessments,

            "incidents":
                telemetry_incidents
        },

        "audit_events":
            recent_audit_events,

        "summary": {
            "total":
                total,

            "online":
                online,

            "healthy":
                healthy,

            "degraded":
                degraded,

            "critical":
                critical,

            "active_incidents":
                incidents.get(
                    "active_count",
                    0
                ),

            "telemetry_anomalies":
                len(
                    telemetry_anomalies
                ),

            "open_telemetry_anomalies":
                open_anomalies,

            "telemetry_correlations":
                len(
                    telemetry_correlations
                ),

            "open_telemetry_correlations":
                open_correlations,

            "telemetry_ai_assessments":
                len(
                    telemetry_ai_assessments
                ),

            "telemetry_incidents":
                len(
                    telemetry_incidents
                ),

            "active_telemetry_incidents":
                active_telemetry_incidents,

            "platform_status":
                platform_health.get(
                    "status",
                    "UNKNOWN"
                ),

            "reliability_status":
                reliability_noc.get(
                    "status",
                    "UNKNOWN"
                ),

            "reliability_score":
                reliability_noc.get(
                    "score",
                    0
                ),

            "workflow_runs_24h":
                reliability_noc.get(
                    "workflow_runs_24h",
                    0
                ),

            "workflow_successful_runs_24h":
                reliability_noc.get(
                    "workflow_successful_runs_24h",
                    0
                ),

            "workflow_failed_runs_24h":
                reliability_noc.get(
                    "workflow_failed_runs_24h",
                    0
                ),

            "workflow_success_rate":
                reliability_noc.get(
                    "workflow_success_rate",
                    "UNKNOWN"
                ),

            "failed_stage_executions":
                reliability_noc.get(
                    "failed_stage_executions",
                    0
                ),

            "most_failure_prone_stage":
                reliability_noc.get(
                    "most_failure_prone_stage"
                ),

            "recent_workflow_failures":
                reliability_noc.get(
                    "recent_workflow_failures",
                    0
                ),

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
                len(
                    capacity.get(
                        "meaningful_risks",
                        []
                    )
                )
        }
    }


def display_capacity_intelligence(capacity):
    """
    Display the NOC capacity intelligence section.
    """

    print(
        "Network Capacity Intelligence"
    )

    print(
        "----------------------------------------"
    )

    status = capacity.get(
        "status",
        "UNKNOWN"
    )

    threshold = capacity.get(
        "threshold",
        CAPACITY_FORECAST_THRESHOLD
    )

    interfaces_analyzed = capacity.get(
        "interfaces_analyzed",
        0
    )

    forecast_available = capacity.get(
        "forecast_available",
        0
    )

    threshold_reached = capacity.get(
        "threshold_reached",
        0
    )

    increasing_trends = capacity.get(
        "increasing_trends",
        0
    )

    meaningful_risks = capacity.get(
        "meaningful_risks",
        []
    )

    print(
        "Status: "
        + str(
            status
        )
    )

    print(
        "Forecast Threshold: "
        + str(
            threshold
        )
        + "%"
    )

    print(
        "Interfaces Analyzed: "
        + str(
            interfaces_analyzed
        )
    )

    print(
        "Forecasts Available: "
        + str(
            forecast_available
        )
    )

    print(
        "Thresholds Reached: "
        + str(
            threshold_reached
        )
    )

    print(
        "Increasing Trends: "
        + str(
            increasing_trends
        )
    )

    print(
        "Meaningful Capacity Risks: "
        + str(
            len(
                meaningful_risks
            )
        )
    )

    print()

    if not meaningful_risks:

        print(
            "No meaningful capacity risks detected."
        )

        print()

        return

    print(
        "Capacity Risks"
    )

    print(
        "----------------------------------------"
    )

    for risk in meaningful_risks:

        print(
            str(
                risk.get(
                    "router",
                    "UNKNOWN"
                )
            )
            + " | "
            + str(
                risk.get(
                    "interface",
                    "UNKNOWN"
                )
            )
        )

        print(
            "  Status: "
            + str(
                risk.get(
                    "overall_status",
                    "UNKNOWN"
                )
            )
        )

        print(
            "  Threshold: "
            + str(
                risk.get(
                    "threshold",
                    "UNKNOWN"
                )
            )
            + "%"
        )

        days_to_threshold = risk.get(
            "days_to_threshold"
        )

        if days_to_threshold is not None:

            print(
                "  Projected Threshold: "
                + str(
                    round(
                        days_to_threshold,
                        2
                    )
                )
                + " days"
            )

        input_forecast = risk.get(
            "input_forecast",
            {}
        )

        output_forecast = risk.get(
            "output_forecast",
            {}
        )

        input_utilization = (
            input_forecast.get(
                "current_utilization"
            )
        )

        output_utilization = (
            output_forecast.get(
                "current_utilization"
            )
        )

        print(
            "  Input Utilization: "
            + (
                str(
                    round(
                        input_utilization,
                        2
                    )
                )
                + "%"
                if input_utilization is not None
                else "N/A"
            )
        )

        print(
            "  Output Utilization: "
            + (
                str(
                    round(
                        output_utilization,
                        2
                    )
                )
                + "%"
                if output_utilization is not None
                else "N/A"
            )
        )

        print()


def display_noc_snapshot(data):
    """
    Display the unified NetPilot NOC snapshot.

    All information displayed here is read-only.
    """

    print()
    print(
        "========================================"
    )

    print(
        "NETPILOT UNIFIED NOC"
    )

    print(
        "========================================"
    )

    print()

    summary = data.get(
        "summary",
        {}
    )

    print(
        "Routers: "
        + str(
            summary.get(
                "total",
                0
            )
        )
    )

    print(
        "Online: "
        + str(
            summary.get(
                "online",
                0
            )
        )
    )

    print(
        "Healthy: "
        + str(
            summary.get(
                "healthy",
                0
            )
        )
    )

    print(
        "Degraded: "
        + str(
            summary.get(
                "degraded",
                0
            )
        )
    )

    print(
        "Critical: "
        + str(
            summary.get(
                "critical",
                0
            )
        )
    )

    print(
        "Active Incidents: "
        + str(
            summary.get(
                "active_incidents",
                0
            )
        )
    )

    print(
        "Telemetry Anomalies: "
        + str(
            summary.get(
                "telemetry_anomalies",
                0
            )
        )
    )

    print(
        "Open Telemetry Anomalies: "
        + str(
            summary.get(
                "open_telemetry_anomalies",
                0
            )
        )
    )

    print(
        "Telemetry Correlations: "
        + str(
            summary.get(
                "telemetry_correlations",
                0
            )
        )
    )

    print(
        "Open Telemetry Correlations: "
        + str(
            summary.get(
                "open_telemetry_correlations",
                0
            )
        )
    )

    print(
        "Telemetry AI Assessments: "
        + str(
            summary.get(
                "telemetry_ai_assessments",
                0
            )
        )
    )

    print(
        "Telemetry Incidents: "
        + str(
            summary.get(
                "telemetry_incidents",
                0
            )
        )
    )

    print(
        "Active Telemetry Incidents: "
        + str(
            summary.get(
                "active_telemetry_incidents",
                0
            )
        )
    )

    print()

    # ---------------------------------------------------------------
    # Network Capacity Intelligence
    # 12.6
    # ---------------------------------------------------------------

    capacity = data.get(
        "capacity",
        {}
    )

    display_capacity_intelligence(
        capacity
    )

    # ---------------------------------------------------------------
    # Platform Health
    # ---------------------------------------------------------------

    platform_health = data.get(
        "platform_health",
        {}
    )

    print(
        "NetPilot Platform Health"
    )

    print(
        "----------------------------------------"
    )

    print(
        "Overall Status: "
        + str(
            platform_health.get(
                "status",
                "UNKNOWN"
            )
        )
    )

    print()

    for component in platform_health.get(
        "components",
        []
    ):

        component_name = component.get(
            "component",
            "UNKNOWN"
        )

        component_status = component.get(
            "status",
            "UNKNOWN"
        )

        print(
            component_name
            + " | "
            + component_status
        )

        if component_name == "POSTGRESQL":

            if component_status == "HEALTHY":

                print(
                    "  Database: "
                    + str(
                        component.get(
                            "database",
                            "UNKNOWN"
                        )
                    )
                )

                print(
                    "  Response: "
                    + str(
                        component.get(
                            "duration_ms",
                            "UNKNOWN"
                        )
                    )
                    + " ms"
                )

            else:

                print(
                    "  Error: "
                    + str(
                        component.get(
                            "error",
                            "UNKNOWN"
                        )
                    )
                )

        elif component_name == "OLLAMA":

            if component_status == "HEALTHY":

                models = component.get(
                    "models",
                    []
                )

                if models:

                    print(
                        "  Models: "
                        + ", ".join(
                            models
                        )
                    )

                else:

                    print(
                        "  Models: NONE"
                    )

                print(
                    "  Response: "
                    + str(
                        component.get(
                            "duration_ms",
                            "UNKNOWN"
                        )
                    )
                    + " ms"
                )

            else:

                print(
                    "  Error: "
                    + str(
                        component.get(
                            "error",
                            "UNKNOWN"
                        )
                    )
                )

        elif component_name == "WORKFLOW_ENGINE":

            print(
                "  Successful runs (24h): "
                + str(
                    component.get(
                        "successful_runs_24h",
                        0
                    )
                )
            )

            print(
                "  Failed runs (24h): "
                + str(
                    component.get(
                        "failed_runs_24h",
                        0
                    )
                )
            )

            print(
                "  Average duration: "
                + str(
                    component.get(
                        "average_duration_ms",
                        "UNKNOWN"
                    )
                )
                + " ms"
            )

            latest_run = component.get(
                "latest_run"
            )

            if latest_run is not None:

                print(
                    "  Latest run: "
                    + str(
                        latest_run.get(
                            "run_id",
                            "UNKNOWN"
                        )
                    )
                )

                print(
                    "  Latest status: "
                    + str(
                        latest_run.get(
                            "status",
                            "UNKNOWN"
                        )
                    )
                )

        print()

    # ---------------------------------------------------------------
    # Reliability Intelligence
    # ---------------------------------------------------------------

    reliability = data.get(
        "reliability",
        {}
    )

    reliability_noc = data.get(
        "reliability_noc",
        {}
    )

    stages = reliability.get(
        "stages",
        {}
    )

    reliability_status = reliability_noc.get(
        "status",
        "UNKNOWN"
    )

    reliability_score = reliability_noc.get(
        "score",
        0
    )

    workflow_runs_24h = reliability_noc.get(
        "workflow_runs_24h",
        0
    )

    workflow_successful_runs_24h = (
        reliability_noc.get(
            "workflow_successful_runs_24h",
            0
        )
    )

    workflow_failed_runs_24h = (
        reliability_noc.get(
            "workflow_failed_runs_24h",
            0
        )
    )

    workflow_success_rate = (
        reliability_noc.get(
            "workflow_success_rate",
            "UNKNOWN"
        )
    )

    failed_stage_executions = (
        reliability_noc.get(
            "failed_stage_executions",
            0
        )
    )

    most_failure_prone_stage = (
        reliability_noc.get(
            "most_failure_prone_stage"
        )
    )

    recent_workflow_failures = (
        reliability_noc.get(
            "recent_workflow_failures",
            0
        )
    )

    print(
        "NetPilot Reliability Intelligence"
    )

    print(
        "----------------------------------------"
    )

    print(
        "Health Score: "
        + format_reliability_score(
            reliability_score
        )
        + " / 100"
    )

    print(
        "Status: "
        + str(
            reliability_status
        )
    )

    print()

    print(
        "Workflow Reliability"
    )

    print(
        "----------------------------------------"
    )

    print(
        "Runs (24h): "
        + str(
            workflow_runs_24h
        )
    )

    print(
        "Successful: "
        + str(
            workflow_successful_runs_24h
        )
    )

    print(
        "Failed: "
        + str(
            workflow_failed_runs_24h
        )
    )

    print(
        "Success Rate: "
        + format_percentage(
            workflow_success_rate
        )
        + "%"
    )

    print(
        "Average Duration: "
        + str(
            reliability_noc.get(
                "average_duration_ms",
                "UNKNOWN"
            )
        )
        + " ms"
    )

    print()

    print(
        "Stage Reliability"
    )

    print(
        "----------------------------------------"
    )

    stage_labels = {
        "anomaly":
            "Telemetry / Anomaly",

        "correlation":
            "Correlation",

        "ai":
            "AI Assessment",

        "incident":
            "Incident Integration",

        "incident_sync":
            "Incident Synchronization",

        "validation":
            "Operational Validation"
    }

    for stage_key, stage_label in stage_labels.items():

        stage = stages.get(
            stage_key,
            {}
        )

        stage_status = stage.get(
            "status",
            "UNKNOWN"
        )

        stage_success_rate = stage.get(
            "success_rate",
            "UNKNOWN"
        )

        print(
            stage_label
            + " | "
            + str(
                stage_status
            )
            + " | Success Rate: "
            + format_percentage(
                stage_success_rate
            )
            + "%"
        )

    print()

    print(
        "Failure Intelligence"
    )

    print(
        "----------------------------------------"
    )

    print(
        "Failed Stage Executions: "
        + str(
            failed_stage_executions
        )
    )

    if most_failure_prone_stage is not None:

        print(
            "Most Failure-Prone Stage: "
            + str(
                most_failure_prone_stage
            )
        )

    else:

        print(
            "Most Failure-Prone Stage: None"
        )

    print(
        "Recent Workflow Failures: "
        + str(
            recent_workflow_failures
        )
    )

    print()

    print(
        "Reliability Assessment"
    )

    print(
        "----------------------------------------"
    )

    reasons = reliability_noc.get(
        "reasons",
        []
    )

    if reasons:

        for reason in reasons:

            print(
                "- "
                + str(
                    reason
                )
            )

    else:

        print(
            "- No workflow or stage reliability issues detected."
        )

    print()

    # ---------------------------------------------------------------
    # Telemetry Correlations
    # ---------------------------------------------------------------

    telemetry = data.get(
        "telemetry",
        {}
    )

    print(
        "Telemetry Correlations"
    )

    print(
        "----------------------------------------"
    )

    correlations = telemetry.get(
        "correlations",
        []
    )

    if correlations:

        for correlation in correlations:

            print(
                str(
                    correlation.get(
                        "router",
                        "UNKNOWN"
                    )
                )
                + " | "
                + str(
                    correlation.get(
                        "interface_name",
                        "UNKNOWN"
                    )
                )
                + " | "
                + str(
                    correlation.get(
                        "correlation_type",
                        "UNKNOWN"
                    )
                )
                + " | "
                + str(
                    correlation.get(
                        "severity",
                        "UNKNOWN"
                    )
                )
                + " | "
                + str(
                    correlation.get(
                        "status",
                        "UNKNOWN"
                    )
                )
            )

    else:

        print(
            "No telemetry correlations."
        )

    print()

    # ---------------------------------------------------------------
    # Telemetry Incidents
    # ---------------------------------------------------------------

    print(
        "Telemetry Incidents"
    )

    print(
        "----------------------------------------"
    )

    telemetry_incidents = telemetry.get(
        "incidents",
        []
    )

    if telemetry_incidents:

        for incident in telemetry_incidents:

            print(
                str(
                    incident.get(
                        "incident_id",
                        "UNKNOWN"
                    )
                )
                + " | "
                + str(
                    incident.get(
                        "router",
                        "UNKNOWN"
                    )
                )
                + " | "
                + str(
                    incident.get(
                        "incident_type",
                        "UNKNOWN"
                    )
                )
                + " | "
                + str(
                    incident.get(
                        "status",
                        "UNKNOWN"
                    )
                )
            )

    else:

        print(
            "No telemetry incidents."
        )

    print()

    # ---------------------------------------------------------------
    # Recent Audit Events
    # ---------------------------------------------------------------

    print(
        "Recent Audit Events"
    )

    print(
        "----------------------------------------"
    )

    audit_events = data.get(
        "audit_events",
        []
    )

    if audit_events:

        for event in audit_events:

            print(
                str(
                    event.get(
                        "event_type",
                        "UNKNOWN"
                    )
                )
                + " | incident="
                + str(
                    event.get(
                        "incident_id",
                        "N/A"
                    )
                )
                + " | actor="
                + str(
                    event.get(
                        "actor",
                        "UNKNOWN"
                    )
                )
            )

    else:

        print(
            "No recent audit events."
        )

    print()


if __name__ == "__main__":

    data = build_noc_snapshot()

    display_noc_snapshot(
        data
    )
