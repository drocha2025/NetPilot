import json

from app.database import get_connection


WORKFLOW_NAME = "AUTOMATED_TELEMETRY"


STAGE_DEFINITIONS = {
    "anomaly": "Telemetry / Anomaly",
    "correlation": "Correlation",
    "ai": "AI Assessment",
    "incident": "Incident Integration",
    "incident_sync": "Incident Synchronization",
    "validation": "Operational Validation"
}


def get_workflow_reliability():
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM workflow_runs
                WHERE workflow_name = %s
                  AND started_at >=
                      CURRENT_TIMESTAMP - INTERVAL '24 hours';
                """,
                (WORKFLOW_NAME,)
            )

            total_runs = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM workflow_runs
                WHERE workflow_name = %s
                  AND status = 'SUCCESS'
                  AND started_at >=
                      CURRENT_TIMESTAMP - INTERVAL '24 hours';
                """,
                (WORKFLOW_NAME,)
            )

            successful_runs = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM workflow_runs
                WHERE workflow_name = %s
                  AND status = 'FAILED'
                  AND started_at >=
                      CURRENT_TIMESTAMP - INTERVAL '24 hours';
                """,
                (WORKFLOW_NAME,)
            )

            failed_runs = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    AVG(duration_ms),
                    MIN(duration_ms),
                    MAX(duration_ms)
                FROM workflow_runs
                WHERE workflow_name = %s
                  AND status = 'SUCCESS'
                  AND started_at >=
                      CURRENT_TIMESTAMP - INTERVAL '24 hours'
                  AND duration_ms IS NOT NULL;
                """,
                (WORKFLOW_NAME,)
            )

            duration_result = cursor.fetchone()

            average_duration = duration_result[0]
            fastest_duration = duration_result[1]
            slowest_duration = duration_result[2]

            cursor.execute(
                """
                SELECT
                    run_id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    stages_completed,
                    stages_failed,
                    error
                FROM workflow_runs
                WHERE workflow_name = %s
                ORDER BY id DESC
                LIMIT 1;
                """,
                (WORKFLOW_NAME,)
            )

            latest = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    run_id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    stages_completed,
                    stages_failed,
                    error
                FROM workflow_runs
                WHERE workflow_name = %s
                  AND status = 'FAILED'
                ORDER BY id DESC
                LIMIT 1;
                """,
                (WORKFLOW_NAME,)
            )

            latest_failure = cursor.fetchone()

        if total_runs == 0:

            success_rate = None
            reliability_status = "UNKNOWN"

        else:

            success_rate = (
                successful_runs
                / total_runs
            ) * 100

            if failed_runs == 0:

                reliability_status = "HEALTHY"

            elif success_rate >= 90:

                reliability_status = "WARNING"

            else:

                reliability_status = "CRITICAL"

        latest_run = None

        if latest is not None:

            latest_run = {
                "run_id": latest[0],
                "status": latest[1],
                "started_at": str(latest[2]),
                "completed_at": (
                    str(latest[3])
                    if latest[3] is not None
                    else None
                ),
                "duration_ms": latest[4],
                "stages_completed": latest[5],
                "stages_failed": latest[6],
                "error": latest[7]
            }

        latest_failure_data = None

        if latest_failure is not None:

            latest_failure_data = {
                "run_id": latest_failure[0],
                "status": latest_failure[1],
                "started_at": str(
                    latest_failure[2]
                ),
                "completed_at": (
                    str(latest_failure[3])
                    if latest_failure[3] is not None
                    else None
                ),
                "duration_ms": latest_failure[4],
                "stages_completed": latest_failure[5],
                "stages_failed": latest_failure[6],
                "error": latest_failure[7]
            }

        return {
            "workflow_name": WORKFLOW_NAME,
            "status": reliability_status,

            "total_runs_24h": total_runs,
            "successful_runs_24h": successful_runs,
            "failed_runs_24h": failed_runs,
            "success_rate_24h": success_rate,

            "average_duration_ms": (
                float(average_duration)
                if average_duration is not None
                else None
            ),

            "fastest_duration_ms": fastest_duration,
            "slowest_duration_ms": slowest_duration,

            "latest_run": latest_run,
            "latest_failure": latest_failure_data
        }

    except Exception as error:

        return {
            "workflow_name": WORKFLOW_NAME,
            "status": "FAILED",
            "error": str(error)
        }

    finally:

        if connection is not None:
            connection.close()


def get_stage_reliability():
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    run_id,
                    status,
                    started_at,
                    summary
                FROM workflow_runs
                WHERE workflow_name = %s
                  AND started_at >=
                      CURRENT_TIMESTAMP - INTERVAL '24 hours'
                ORDER BY id DESC;
                """,
                (WORKFLOW_NAME,)
            )

            runs = cursor.fetchall()

        stage_results = {}

        for stage_key in STAGE_DEFINITIONS:

            stage_results[stage_key] = {
                "name": STAGE_DEFINITIONS[stage_key],

                "total": 0,
                "successful": 0,
                "failed": 0,
                "warning": 0,
                "unknown": 0,

                "success_rate": None,
                "status": "UNKNOWN",

                "latest_status": "UNKNOWN",
                "latest_run_id": None,
                "latest_failure": None
            }

        for run in runs:

            run_id = run[0]
            started_at = run[2]
            summary = run[3]

            if summary is None:
                continue

            if isinstance(summary, str):

                try:
                    summary = json.loads(summary)

                except json.JSONDecodeError:
                    continue

            if not isinstance(summary, dict):
                continue

            for stage_key in STAGE_DEFINITIONS:

                if stage_key not in summary:
                    continue

                stage_data = summary[stage_key]

                if not isinstance(stage_data, dict):
                    continue

                stage = stage_results[stage_key]

                stage["total"] += 1

                stage_status = str(
                    stage_data.get(
                        "status",
                        "UNKNOWN"
                    )
                ).upper()

                if stage["latest_run_id"] is None:

                    stage["latest_run_id"] = run_id
                    stage["latest_status"] = stage_status

                if stage_status in (
                    "COMPLETE",
                    "SUCCESS",
                    "VALID"
                ):

                    stage["successful"] += 1

                elif stage_status == "FAILED":

                    stage["failed"] += 1

                    if stage["latest_failure"] is None:

                        stage["latest_failure"] = {
                            "run_id": run_id,
                            "started_at": str(
                                started_at
                            ),
                            "status": stage_status,
                            "details": stage_data
                        }

                elif stage_status in (
                    "WARNING",
                    "WAITING",
                    "SKIPPED"
                ):

                    stage["warning"] += 1

                else:

                    stage["unknown"] += 1

        for stage_key in STAGE_DEFINITIONS:

            stage = stage_results[stage_key]

            if stage["total"] == 0:

                stage["success_rate"] = None
                stage["status"] = "UNKNOWN"

                continue

            stage["success_rate"] = (
                stage["successful"]
                / stage["total"]
            ) * 100

            if stage["failed"] > 0:

                if stage["success_rate"] >= 90:
                    stage["status"] = "WARNING"

                else:
                    stage["status"] = "CRITICAL"

            elif stage["warning"] > 0:

                stage["status"] = "WARNING"

            elif stage["unknown"] > 0:

                stage["status"] = "WARNING"

            else:

                stage["status"] = "HEALTHY"

        return stage_results

    except Exception as error:

        return {
            "error": str(error)
        }

    finally:

        if connection is not None:
            connection.close()


def get_failure_analysis(stage_data):

    if not isinstance(stage_data, dict):

        return {
            "status": "FAILED",
            "error": "Invalid stage reliability data."
        }

    if "error" in stage_data:

        return {
            "status": "FAILED",
            "error": stage_data["error"]
        }

    failed_stages = []

    for stage_key in STAGE_DEFINITIONS:

        stage = stage_data.get(
            stage_key,
            {}
        )

        if stage.get("failed", 0) > 0:

            failed_stages.append(
                {
                    "stage_key": stage_key,

                    "stage_name": stage.get(
                        "name",
                        STAGE_DEFINITIONS[
                            stage_key
                        ]
                    ),

                    "failed": stage.get(
                        "failed",
                        0
                    ),

                    "total": stage.get(
                        "total",
                        0
                    ),

                    "success_rate": stage.get(
                        "success_rate"
                    ),

                    "latest_failure": stage.get(
                        "latest_failure"
                    )
                }
            )

    failed_stages.sort(
        key=lambda item: (
            item["failed"],
            item["total"]
        ),
        reverse=True
    )

    total_stage_failures = 0

    for stage in failed_stages:

        total_stage_failures += stage[
            "failed"
        ]

    most_failed_stage = None

    if failed_stages:

        most_failed_stage = failed_stages[0]

    return {
        "status": (
            "FAILURES_DETECTED"
            if failed_stages
            else "NO_FAILURES"
        ),

        "total_failed_stages": (
            total_stage_failures
        ),

        "failed_stages": failed_stages,

        "most_failed_stage": most_failed_stage
    }


def get_recent_failure_history():

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    run_id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    stages_completed,
                    stages_failed,
                    error
                FROM workflow_runs
                WHERE workflow_name = %s
                  AND status = 'FAILED'
                ORDER BY id DESC
                LIMIT 10;
                """,
                (WORKFLOW_NAME,)
            )

            rows = cursor.fetchall()

        failures = []

        for row in rows:

            failures.append(
                {
                    "run_id": row[0],
                    "status": row[1],

                    "started_at": str(
                        row[2]
                    ),

                    "completed_at": (
                        str(row[3])
                        if row[3] is not None
                        else None
                    ),

                    "duration_ms": row[4],

                    "stages_completed": row[5],

                    "stages_failed": row[6],

                    "error": row[7]
                }
            )

        return failures

    except Exception as error:

        return {
            "error": str(error)
        }

    finally:

        if connection is not None:
            connection.close()


def calculate_reliability_score(
    workflow,
    stages
):

    if workflow.get("status") == "FAILED":

        return {
            "score": 0,
            "status": "CRITICAL",
            "reasons": [
                "Workflow reliability data could not be collected."
            ]
        }

    total_runs = workflow.get(
        "total_runs_24h",
        0
    )

    success_rate = workflow.get(
        "success_rate_24h"
    )

    if total_runs == 0 or success_rate is None:

        return {
            "score": None,
            "status": "UNKNOWN",
            "reasons": [
                "No workflow execution history is available."
            ]
        }

    score = 100.0

    reasons = []

    failed_runs = workflow.get(
        "failed_runs_24h",
        0
    )

    if failed_runs > 0:

        failure_rate = (
            failed_runs
            / total_runs
        ) * 100

        workflow_penalty = min(
            failure_rate * 2,
            40
        )

        score -= workflow_penalty

        reasons.append(
            "Workflow failure rate is "
            + str(
                round(
                    failure_rate,
                    2
                )
            )
            + "%."
        )

    failed_stage_count = 0
    warning_stage_count = 0
    unknown_stage_count = 0

    if isinstance(stages, dict):

        for stage_key in STAGE_DEFINITIONS:

            stage = stages.get(
                stage_key,
                {}
            )

            failed_stage_count += stage.get(
                "failed",
                0
            )

            warning_stage_count += stage.get(
                "warning",
                0
            )

            unknown_stage_count += stage.get(
                "unknown",
                0
            )

    if failed_stage_count > 0:

        stage_penalty = min(
            failed_stage_count * 5,
            25
        )

        score -= stage_penalty

        reasons.append(
            str(
                failed_stage_count
            )
            + " failed stage execution(s) detected."
        )

    if warning_stage_count > 0:

        warning_penalty = min(
            warning_stage_count * 2,
            10
        )

        score -= warning_penalty

        reasons.append(
            str(
                warning_stage_count
            )
            + " stage warning(s) detected."
        )

    if unknown_stage_count > 0:

        unknown_penalty = min(
            unknown_stage_count * 2,
            10
        )

        score -= unknown_penalty

        reasons.append(
            str(
                unknown_stage_count
            )
            + " stage result(s) have an unknown state."
        )

    if score < 0:
        score = 0

    score = round(
        score,
        2
    )

    if score >= 95:

        status = "HEALTHY"

    elif score >= 80:

        status = "WARNING"

    else:

        status = "CRITICAL"

    if not reasons:

        reasons.append(
            "No workflow or stage reliability issues detected."
        )

    return {
        "score": score,
        "status": status,
        "reasons": reasons
    }


def build_noc_reliability_summary(
    workflow,
    stages,
    failure_analysis,
    recent_failures,
    health_score
):
    """
    Build explicit reliability fields for NOC consumers.

    The detailed reliability structures remain available,
    while these fields provide a stable and simple interface
    for the NOC dashboard.
    """

    failed_stage_executions = 0

    if isinstance(
        failure_analysis,
        dict
    ):

        failed_stage_executions = (
            failure_analysis.get(
                "total_failed_stages",
                0
            )
        )

    most_failure_prone_stage = None

    if isinstance(
        failure_analysis,
        dict
    ):

        most_failed_stage = (
            failure_analysis.get(
                "most_failed_stage"
            )
        )

        if isinstance(
            most_failed_stage,
            dict
        ):

            most_failure_prone_stage = (
                most_failed_stage.get(
                    "stage_name"
                )
            )

    recent_workflow_failures = 0

    if isinstance(
        recent_failures,
        list
    ):

        recent_workflow_failures = len(
            recent_failures
        )

    reliability_score = None
    reliability_status = "UNKNOWN"

    if isinstance(
        health_score,
        dict
    ):

        reliability_score = (
            health_score.get(
                "score"
            )
        )

        reliability_status = (
            health_score.get(
                "status",
                "UNKNOWN"
            )
        )

    return {
        "failed_stage_executions":
            failed_stage_executions,

        "most_failure_prone_stage":
            most_failure_prone_stage,

        "recent_workflow_failures":
            recent_workflow_failures,

        "reliability_score":
            reliability_score,

        "reliability_status":
            reliability_status,

        "workflow_success_rate":
            workflow.get(
                "success_rate_24h"
            ),

        "workflow_runs_24h":
            workflow.get(
                "total_runs_24h",
                0
            ),

        "workflow_successful_runs_24h":
            workflow.get(
                "successful_runs_24h",
                0
            ),

        "workflow_failed_runs_24h":
            workflow.get(
                "failed_runs_24h",
                0
            )
    }


def get_reliability_data():

    workflow = get_workflow_reliability()

    stages = get_stage_reliability()

    failure_analysis = (
        get_failure_analysis(
            stages
        )
    )

    recent_failures = (
        get_recent_failure_history()
    )

    health_score = (
        calculate_reliability_score(
            workflow,
            stages
        )
    )

    noc_summary = (
        build_noc_reliability_summary(
            workflow,
            stages,
            failure_analysis,
            recent_failures,
            health_score
        )
    )

    return {
        "workflow": workflow,

        "stages": stages,

        "failure_analysis":
            failure_analysis,

        "recent_failures":
            recent_failures,

        "health_score":
            health_score,

        "noc_summary":
            noc_summary,

        "reliability_status":
            noc_summary[
                "reliability_status"
            ],

        "reliability_score":
            noc_summary[
                "reliability_score"
            ],

        "failed_stage_executions":
            noc_summary[
                "failed_stage_executions"
            ],

        "most_failure_prone_stage":
            noc_summary[
                "most_failure_prone_stage"
            ],

        "recent_workflow_failures":
            noc_summary[
                "recent_workflow_failures"
            ]
    }


def display_workflow_reliability(data):

    print()
    print("========================================")
    print("NETPILOT WORKFLOW RELIABILITY")
    print("========================================")
    print()

    print(
        "Workflow: "
        + str(
            data.get(
                "workflow_name",
                "UNKNOWN"
            )
        )
    )

    print(
        "Status: "
        + str(
            data.get(
                "status",
                "UNKNOWN"
            )
        )
    )

    print(
        "Runs (24h): "
        + str(
            data.get(
                "total_runs_24h",
                0
            )
        )
    )

    print(
        "Successful: "
        + str(
            data.get(
                "successful_runs_24h",
                0
            )
        )
    )

    print(
        "Failed: "
        + str(
            data.get(
                "failed_runs_24h",
                0
            )
        )
    )

    success_rate = data.get(
        "success_rate_24h"
    )

    if success_rate is None:

        print(
            "Success Rate: UNKNOWN"
        )

    else:

        print(
            "Success Rate: "
            + str(
                round(
                    success_rate,
                    2
                )
            )
            + "%"
        )

    average_duration = data.get(
        "average_duration_ms"
    )

    if average_duration is None:
        average_duration = "UNKNOWN"

    print(
        "Average Duration: "
        + str(
            average_duration
        )
        + " ms"
    )

    print(
        "Fastest Duration: "
        + str(
            data.get(
                "fastest_duration_ms",
                "UNKNOWN"
            )
        )
        + " ms"
    )

    print(
        "Slowest Duration: "
        + str(
            data.get(
                "slowest_duration_ms",
                "UNKNOWN"
            )
        )
        + " ms"
    )

    print()

    latest = data.get(
        "latest_run"
    )

    print("Latest Workflow Run")
    print("----------------------------------------")

    if latest is None:

        print(
            "No workflow runs found."
        )

    else:

        print(
            "Run ID: "
            + str(
                latest.get(
                    "run_id",
                    "UNKNOWN"
                )
            )
        )

        print(
            "Status: "
            + str(
                latest.get(
                    "status",
                    "UNKNOWN"
                )
            )
        )

        print(
            "Duration: "
            + str(
                latest.get(
                    "duration_ms",
                    "UNKNOWN"
                )
            )
            + " ms"
        )

        print(
            "Stages completed: "
            + str(
                latest.get(
                    "stages_completed",
                    0
                )
            )
        )

        print(
            "Stages failed: "
            + str(
                latest.get(
                    "stages_failed",
                    0
                )
            )
        )

    print()

    latest_failure = data.get(
        "latest_failure"
    )

    print("Latest Workflow Failure")
    print("----------------------------------------")

    if latest_failure is None:

        print(
            "No workflow failures found."
        )

    else:

        print(
            "Run ID: "
            + str(
                latest_failure.get(
                    "run_id",
                    "UNKNOWN"
                )
            )
        )

        print(
            "Stages completed: "
            + str(
                latest_failure.get(
                    "stages_completed",
                    0
                )
            )
        )

        print(
            "Stages failed: "
            + str(
                latest_failure.get(
                    "stages_failed",
                    0
                )
            )
        )

        print(
            "Error: "
            + str(
                latest_failure.get(
                    "error",
                    "UNKNOWN"
                )
            )
        )

    print()


def display_stage_reliability(data):

    print("Workflow Stage Reliability")
    print("----------------------------------------")

    if "error" in data:

        print(
            "Stage analysis failed: "
            + str(
                data["error"]
            )
        )

        print()
        return

    for stage_key in STAGE_DEFINITIONS:

        stage = data.get(
            stage_key,
            {}
        )

        stage_name = STAGE_DEFINITIONS[
            stage_key
        ]

        status = stage.get(
            "status",
            "UNKNOWN"
        )

        success_rate = stage.get(
            "success_rate"
        )

        if success_rate is None:

            rate_text = "UNKNOWN"

        else:

            rate_text = (
                str(
                    round(
                        success_rate,
                        2
                    )
                )
                + "%"
            )

        print(
            stage_name
            + " | "
            + status
            + " | Success Rate: "
            + rate_text
            + " | Runs: "
            + str(
                stage.get(
                    "total",
                    0
                )
            )
            + " | Failed: "
            + str(
                stage.get(
                    "failed",
                    0
                )
            )
        )

    print()


def display_failure_analysis(data):

    print("Workflow Failure Analysis")
    print("----------------------------------------")

    if data.get("status") == "NO_FAILURES":

        print(
            "No workflow stage failures detected."
        )

        print()

        return

    if data.get("status") == "FAILED":

        print(
            "Failure analysis failed: "
            + str(
                data.get(
                    "error",
                    "UNKNOWN"
                )
            )
        )

        print()

        return

    print(
        "Total failed stage executions: "
        + str(
            data.get(
                "total_failed_stages",
                0
            )
        )
    )

    most_failed = data.get(
        "most_failed_stage"
    )

    print()

    if most_failed is not None:

        print(
            "Most Failure-Prone Stage: "
            + most_failed.get(
                "stage_name",
                "UNKNOWN"
            )
        )

        print(
            "Failures: "
            + str(
                most_failed.get(
                    "failed",
                    0
                )
            )
        )

        success_rate = (
            most_failed.get(
                "success_rate"
            )
        )

        if success_rate is None:

            print(
                "Success Rate: UNKNOWN"
            )

        else:

            print(
                "Success Rate: "
                + str(
                    round(
                        success_rate,
                        2
                    )
                )
                + "%"
            )

        latest_failure = (
            most_failed.get(
                "latest_failure"
            )
        )

        if latest_failure is not None:

            print(
                "Latest Failure Run: "
                + str(
                    latest_failure.get(
                        "run_id",
                        "UNKNOWN"
                    )
                )
            )

            print(
                "Failure Time: "
                + str(
                    latest_failure.get(
                        "started_at",
                        "UNKNOWN"
                    )
                )
            )

    print()

    failed_stages = data.get(
        "failed_stages",
        []
    )

    if failed_stages:

        print("Failure Frequency by Stage")
        print("----------------------------------------")

        for stage in failed_stages:

            success_rate = stage.get(
                "success_rate"
            )

            if success_rate is None:

                rate_text = "UNKNOWN"

            else:

                rate_text = (
                    str(
                        round(
                            success_rate,
                            2
                        )
                    )
                    + "%"
                )

            print(
                stage.get(
                    "stage_name",
                    "UNKNOWN"
                )
                + " | Failures: "
                + str(
                    stage.get(
                        "failed",
                        0
                    )
                )
                + " | Runs: "
                + str(
                    stage.get(
                        "total",
                        0
                    )
                )
                + " | Success Rate: "
                + rate_text
            )

    print()


def display_recent_failures(data):

    print("Recent Workflow Failures")
    print("----------------------------------------")

    if isinstance(data, dict):

        print(
            "Failure history retrieval failed: "
            + str(
                data.get(
                    "error",
                    "UNKNOWN"
                )
            )
        )

        print()

        return

    if not data:

        print(
            "No workflow failures found."
        )

        print()

        return

    for failure in data:

        print(
            "Run ID: "
            + str(
                failure.get(
                    "run_id",
                    "UNKNOWN"
                )
            )
        )

        print(
            "Started: "
            + str(
                failure.get(
                    "started_at",
                    "UNKNOWN"
                )
            )
        )

        print(
            "Stages completed: "
            + str(
                failure.get(
                    "stages_completed",
                    0
                )
            )
        )

        print(
            "Stages failed: "
            + str(
                failure.get(
                    "stages_failed",
                    0
                )
            )
        )

        print(
            "Error: "
            + str(
                failure.get(
                    "error",
                    "UNKNOWN"
                )
            )
        )

        print()


def display_health_score(data):

    print("NetPilot Reliability Health Score")
    print("----------------------------------------")

    score = data.get(
        "score"
    )

    status = data.get(
        "status",
        "UNKNOWN"
    )

    if score is None:

        print(
            "Score: UNKNOWN"
        )

    else:

        print(
            "Score: "
            + str(score)
            + " / 100"
        )

    print(
        "Status: "
        + status
    )

    print()

    print("Score Interpretation")
    print("----------------------------------------")
    print("95-100  HEALTHY")
    print("80-94   WARNING")
    print("0-79    CRITICAL")
    print()

    print("Reasons")
    print("----------------------------------------")

    reasons = data.get(
        "reasons",
        []
    )

    for reason in reasons:

        print(
            "- "
            + str(reason)
        )

    print()


def main():

    reliability_data = (
        get_reliability_data()
    )

    workflow = reliability_data.get(
        "workflow",
        {}
    )

    stages = reliability_data.get(
        "stages",
        {}
    )

    failure_analysis = (
        reliability_data.get(
            "failure_analysis",
            {}
        )
    )

    recent_failures = (
        reliability_data.get(
            "recent_failures",
            []
        )
    )

    health_score = (
        reliability_data.get(
            "health_score",
            {}
        )
    )

    display_workflow_reliability(
        workflow
    )

    display_stage_reliability(
        stages
    )

    display_failure_analysis(
        failure_analysis
    )

    display_recent_failures(
        recent_failures
    )

    display_health_score(
        health_score
    )


if __name__ == "__main__":
    main()
