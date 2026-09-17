from pathlib import Path

from app.database import get_connection


SCHEMA_FILE = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "schema.sql"
)


def initialize_database():
    """
    Create the NetPilot PostgreSQL database schema.
    """

    if not SCHEMA_FILE.exists():

        return {
            "status": "FAILED",
            "error": (
                "Schema file not found: "
                + str(SCHEMA_FILE)
            )
        }

    connection = None

    try:

        schema = SCHEMA_FILE.read_text(
            encoding="utf-8"
        )

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(schema)

        connection.commit()

        return {
            "status": "INITIALIZED",
            "schema_file": str(SCHEMA_FILE)
        }

    except Exception as error:

        if connection is not None:
            connection.rollback()

        return {
            "status": "FAILED",
            "error": str(error)
        }

    finally:

        if connection is not None:
            connection.close()


def display_result(result):
    """
    Display database initialization result.
    """

    print()
    print("========================================")
    print("NETPILOT DATABASE SCHEMA")
    print("========================================")
    print()

    print(
        "Status: " +
        result.get("status", "UNKNOWN")
    )

    if result.get("schema_file"):

        print(
            "Schema: " +
            result.get("schema_file")
        )

    if result.get("error"):

        print(
            "Error: " +
            result.get("error")
        )

    print()


if __name__ == "__main__":

    result = initialize_database()

    display_result(result)