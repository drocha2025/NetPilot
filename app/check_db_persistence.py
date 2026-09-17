# Imports the existing NetPilot database connection function.
from app.database import get_connection


# Opens a connection to the PostgreSQL database.
connection = get_connection()

# Creates a cursor so we can execute SQL queries.
cursor = connection.cursor()


# Counts the number of workflow execution records.
cursor.execute("SELECT COUNT(*) FROM workflow_runs")

# Retrieves the workflow record count.
workflow_count = cursor.fetchone()[0]


# Counts the number of interface telemetry records.
cursor.execute("SELECT COUNT(*) FROM interface_telemetry")

# Retrieves the telemetry record count.
telemetry_count = cursor.fetchone()[0]


# Displays the workflow record count.
print(f"workflow_runs rows: {workflow_count}")

# Displays the telemetry record count.
print(f"interface_telemetry rows: {telemetry_count}")


# Closes the database connection cleanly.
connection.close()
