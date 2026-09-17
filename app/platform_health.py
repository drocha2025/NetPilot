# Imports the operating-system module so we can read environment variables.
import os

# Imports JSON support so we can decode the response returned by Ollama.
import json

# Imports time functions so we can measure dependency response times.
import time

# Imports urllib request functionality so we can test the Ollama HTTP endpoint.
import urllib.request

# Imports urllib error types so we can handle connection and timeout failures cleanly.
import urllib.error

# Imports the existing NetPilot database connection function.
from app.database import get_connection

# Imports the application's normal Ollama configuration.
from app.config import OLLAMA_HOST, OLLAMA_MODEL


# Defines the Ollama health endpoint.
# A dedicated environment variable allows controlled failure testing without
# changing the actual Ollama configuration used by NetPilot.
OLLAMA_URL = os.getenv(
    "NETPILOT_OLLAMA_HEALTH_URL",
    f"{OLLAMA_HOST}/api/tags",
)


# Defines the Ollama model used by the health check.
# The special health-test variable allows us to test a missing model safely.
# If no test model is supplied, the normal NetPilot model is checked.
OLLAMA_HEALTH_MODEL = os.getenv(
    "NETPILOT_OLLAMA_HEALTH_MODEL",
    OLLAMA_MODEL,
)


# Defines the maximum number of seconds allowed for an Ollama health request.
OLLAMA_TIMEOUT = 10


# Checks whether PostgreSQL is reachable and responding.
def check_postgresql():

    # Records the beginning of the database test.
    start_time = time.perf_counter()

    # Attempts to connect to PostgreSQL.
    try:

        # Opens a PostgreSQL connection using NetPilot's existing database configuration.
        connection = get_connection()

        # Creates a database cursor for executing the health query.
        with connection.cursor() as cursor:

            # Executes a lightweight query to confirm PostgreSQL is responding.
            cursor.execute(
                "SELECT current_database()"
            )

            # Retrieves the database name returned by PostgreSQL.
            database_name = cursor.fetchone()[0]

        # Closes the database connection after the health test.
        connection.close()

        # Calculates the database response time in milliseconds.
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000
        )

        # Returns the database health information using the field names
        # expected by the Unified NOC.
        return {
            "component": "POSTGRESQL",
            "status": "HEALTHY",
            "database": database_name,
            "duration_ms": duration_ms,
        }

    # Handles database connection, DNS, authentication, and query failures.
    except Exception as error:

        # Returns a clean failure result instead of crashing the platform.
        return {
            "component": "POSTGRESQL",
            "status": "FAILED",
            "error": str(error),
        }


# Checks whether Ollama is reachable and whether the requested model exists.
def check_ollama():

    # Records the beginning of the Ollama test.
    start_time = time.perf_counter()

    # Attempts to contact Ollama.
    try:

        # Creates an HTTP request for Ollama's model-list endpoint.
        request = urllib.request.Request(
            OLLAMA_URL,
            method="GET",
        )

        # Sends the request to Ollama and waits for the response.
        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT,
        ) as response:

            # Reads the response body returned by Ollama.
            response_body = response.read().decode(
                "utf-8"
            )

        # Converts the JSON response into a Python dictionary.
        data = json.loads(
            response_body
        )

        # Retrieves the models returned by Ollama.
        models = data.get(
            "models",
            []
        )

        # Creates a simple list containing the model names.
        model_names = [
            model.get(
                "name",
                ""
            )
            for model in models
        ]

        # Determines whether the requested model is available.
        model_available = (
            OLLAMA_HEALTH_MODEL
            in model_names
        )

        # Calculates the Ollama response time.
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000
        )

        # Returns WARNING when Ollama works but the required model is missing.
        if not model_available:

            return {
                "component": "OLLAMA",
                "status": "WARNING",
                "configured_model": OLLAMA_HEALTH_MODEL,
                "model_available": False,
                "models": model_names,
                "duration_ms": duration_ms,
                "error": (
                    "Configured NetPilot model "
                    "is not available."
                ),
            }

        # Returns HEALTHY when both Ollama and the requested model are available.
        return {
            "component": "OLLAMA",
            "status": "HEALTHY",
            "configured_model": OLLAMA_HEALTH_MODEL,
            "model_available": True,
            "models": model_names,
            "duration_ms": duration_ms,
        }

    # Handles HTTP errors returned by Ollama.
    except urllib.error.HTTPError as error:

        # Returns a clean failed health result.
        return {
            "component": "OLLAMA",
            "status": "FAILED",
            "configured_model": OLLAMA_HEALTH_MODEL,
            "error": (
                f"HTTP {error.code}: "
                f"{error.reason}"
            ),
        }

    # Handles DNS, connection, timeout, and other URL failures.
    except urllib.error.URLError as error:

        # Returns a clean failed health result.
        return {
            "component": "OLLAMA",
            "status": "FAILED",
            "configured_model": OLLAMA_HEALTH_MODEL,
            "error": str(error),
        }

    # Handles malformed JSON and unexpected errors.
    except Exception as error:

        # Returns a clean failed health result.
        return {
            "component": "OLLAMA",
            "status": "FAILED",
            "configured_model": OLLAMA_HEALTH_MODEL,
            "error": str(error),
        }


# Checks workflow execution history in PostgreSQL.
def check_workflow_engine():

    # Attempts to query recent workflow information.
    try:

        # Opens a PostgreSQL connection.
        connection = get_connection()

        # Creates a cursor for the workflow query.
        with connection.cursor() as cursor:

            # Retrieves workflow statistics from the last 24 hours.
            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE status = 'SUCCESS'
                    ) AS successful_runs_24h,
                    COUNT(*) FILTER (
                        WHERE status = 'FAILED'
                    ) AS failed_runs_24h,
                    AVG(duration_ms) AS average_duration_ms
                FROM workflow_runs
                WHERE started_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
                """
            )

            # Retrieves the aggregated workflow statistics.
            row = cursor.fetchone()

            # Retrieves the most recent workflow execution.
            cursor.execute(
                """
                SELECT
                    run_id,
                    status
                FROM workflow_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            )

            # Retrieves the latest workflow row.
            latest_row = cursor.fetchone()

        # Closes the database connection.
        connection.close()

        # Extracts the number of successful workflow runs.
        successful_runs = row[0]

        # Extracts the number of failed workflow runs.
        failed_runs = row[1]

        # Extracts the average workflow duration.
        average_duration = row[2]

        # Converts the database numeric value into a normal Python float.
        if average_duration is not None:

            average_duration = float(
                average_duration
            )

        # Creates the latest-run structure when workflow history exists.
        latest_run = None

        # Checks whether a latest workflow was found.
        if latest_row is not None:

            # Creates the structure expected by the NOC display.
            latest_run = {
                "run_id": latest_row[0],
                "status": latest_row[1],
            }

        # Determines the workflow-engine state.
        #
        # No workflow history means we do not have enough evidence to call
        # the workflow engine healthy or failed.
        if (
            successful_runs == 0
            and failed_runs == 0
        ):

            workflow_status = "UNKNOWN"

        # Any recent failed workflow means the workflow engine requires attention.
        elif failed_runs > 0:

            workflow_status = "WARNING"

        # Otherwise recent successful workflows provide evidence of health.
        else:

            workflow_status = "HEALTHY"

        # Returns the workflow health information.
        return {
            "component": "WORKFLOW_ENGINE",
            "status": workflow_status,
            "successful_runs_24h": successful_runs,
            "failed_runs_24h": failed_runs,
            "average_duration_ms": average_duration,
            "latest_run": latest_run,
        }

    # Handles PostgreSQL failures affecting workflow health.
    except Exception as error:

        # Returns a clean workflow failure instead of crashing.
        return {
            "component": "WORKFLOW_ENGINE",
            "status": "FAILED",
            "error": str(error),
        }


# Calculates the overall NetPilot platform status.
def calculate_overall_status(results):

    # Checks whether any component completely failed.
    if any(
        result.get("status") == "FAILED"
        for result in results
    ):

        # A failed critical dependency makes the platform CRITICAL.
        return "CRITICAL"

    # Checks whether any component requires attention.
    if any(
        result.get("status") == "WARNING"
        for result in results
    ):

        # A warning means the platform is operating but degraded.
        return "WARNING"

    # Checks whether any component lacks enough evidence.
    if any(
        result.get("status") == "UNKNOWN"
        for result in results
    ):

        # UNKNOWN prevents us from declaring complete platform health.
        return "WARNING"

    # Returns HEALTHY when all components explicitly report healthy.
    return "HEALTHY"


# Provides the structured platform-health API used by the Unified NOC.
def get_platform_health():

    # Runs the PostgreSQL health check.
    postgresql = check_postgresql()

    # Runs the Ollama health check.
    ollama = check_ollama()

    # Runs the workflow-engine health check.
    workflow_engine = check_workflow_engine()

    # Places all component results into one list.
    components = [
        postgresql,
        ollama,
        workflow_engine,
    ]

    # Calculates the overall platform status.
    overall_status = calculate_overall_status(
        components
    )

    # Returns the stable structure expected by noc_service.py.
    return {
        "status": overall_status,
        "components": components,
    }


# Displays one component's information safely in the terminal.
def display_result(result):

    # Retrieves the component name.
    component = result.get(
        "component",
        "UNKNOWN"
    )

    # Retrieves the component status.
    status = result.get(
        "status",
        "UNKNOWN"
    )

    # Prints the component status.
    print(
        f"{component}: {status}"
    )

    # Handles PostgreSQL output.
    if component == "POSTGRESQL":

        # Displays the database name when available.
        if "database" in result:

            print(
                f"  Database: "
                f"{result['database']}"
            )

        # Displays the response time when available.
        if "duration_ms" in result:

            print(
                f"  Response: "
                f"{result['duration_ms']} ms"
            )

        # Displays an error when PostgreSQL failed.
        if "error" in result:

            print(
                f"  Error: "
                f"{result['error']}"
            )

    # Handles Ollama output.
    elif component == "OLLAMA":

        # Displays the model being tested.
        if "configured_model" in result:

            print(
                f"  Configured model: "
                f"{result['configured_model']}"
            )

        # Displays whether the requested model exists.
        if "model_available" in result:

            print(
                f"  Model available: "
                f"{result['model_available']}"
            )

        # Displays available Ollama models.
        if "models" in result:

            print(
                f"  Models: "
                f"{', '.join(result['models'])}"
            )

        # Displays the Ollama response time.
        if "duration_ms" in result:

            print(
                f"  Response: "
                f"{result['duration_ms']} ms"
            )

        # Displays an Ollama error.
        if "error" in result:

            print(
                f"  Error: "
                f"{result['error']}"
            )

    # Handles workflow-engine output.
    elif component == "WORKFLOW_ENGINE":

        # Displays successful workflow executions.
        if "successful_runs_24h" in result:

            print(
                f"  Successful runs (24h): "
                f"{result['successful_runs_24h']}"
            )

        # Displays failed workflow executions.
        if "failed_runs_24h" in result:

            print(
                f"  Failed runs (24h): "
                f"{result['failed_runs_24h']}"
            )

        # Displays average workflow duration.
        if "average_duration_ms" in result:

            print(
                f"  Average duration: "
                f"{result['average_duration_ms']} ms"
            )

        # Retrieves the latest workflow execution.
        latest_run = result.get(
            "latest_run"
        )

        # Displays the latest workflow information when available.
        if latest_run is not None:

            print(
                f"  Latest run: "
                f"{latest_run.get('run_id', 'UNKNOWN')}"
            )

            print(
                f"  Latest status: "
                f"{latest_run.get('status', 'UNKNOWN')}"
            )

        # Displays the workflow error when one exists.
        if "error" in result:

            print(
                f"  Error: "
                f"{result['error']}"
            )


# Runs the complete platform-health assessment from the command line.
def main():

    # Prints the health-check separator.
    print()

    # Prints the health-check title.
    print(
        "========================================"
    )

    # Prints the NetPilot platform health heading.
    print(
        "NETPILOT PLATFORM HEALTH"
    )

    # Prints the health-check separator.
    print(
        "========================================"
    )

    # Prints a blank line before component results.
    print()

    # Gets the complete structured platform health.
    platform_health = get_platform_health()

    # Retrieves the overall platform status.
    overall_status = platform_health.get(
        "status",
        "UNKNOWN"
    )

    # Retrieves the component list.
    components = platform_health.get(
        "components",
        []
    )

    # Prints the overall status.
    print(
        f"Overall status: "
        f"{overall_status}"
    )

    # Prints a blank line.
    print()

    # Displays each platform component.
    for component in components:

        # Displays the current component.
        display_result(
            component
        )

        # Separates components visually.
        print()

    # Prints the final platform status.
    print(
        f"NetPilot platform status: "
        f"{overall_status}"
    )

    # Prints a final blank line.
    print()


# Runs the CLI health check when this module is executed directly.
if __name__ == "__main__":

    # Starts the platform health assessment.
    main()
