import os

import psycopg


DATABASE_HOST = os.getenv(
    "NETPILOT_DB_HOST",
    "192.168.1.217"
)

DATABASE_PORT = os.getenv(
    "NETPILOT_DB_PORT",
    "5432"
)

DATABASE_NAME = os.getenv(
    "NETPILOT_DB_NAME",
    "netpilot"
)

DATABASE_USER = os.getenv(
    "NETPILOT_DB_USER",
    "netpilot_app"
)

DATABASE_PASSWORD = os.getenv(
    "NETPILOT_DB_PASSWORD",
    ""
)


def get_connection():
    """
    Create a PostgreSQL connection for NetPilot.
    """

    return psycopg.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        dbname=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD
    )


def test_database_connection():
    """
    Test connectivity to the NetPilot PostgreSQL database.
    """

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    version();
                """
            )

            result = cursor.fetchone()

        return {
            "status": "CONNECTED",
            "database": result[0],
            "user": result[1],
            "version": result[2]
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error)
        }

    finally:

        if connection is not None:
            connection.close()


def display_database_status(result):
    """
    Display database connection status.
    """

    print()
    print("========================================")
    print("NETPILOT DATABASE")
    print("========================================")
    print()

    print(
        "Status: " +
        result.get("status", "UNKNOWN")
    )

    if result.get("status") == "CONNECTED":

        print(
            "Database: " +
            result.get("database", "UNKNOWN")
        )

        print(
            "User: " +
            result.get("user", "UNKNOWN")
        )

        print(
            "PostgreSQL: " +
            result.get("version", "UNKNOWN")
        )

    else:

        print(
            "Error: " +
            result.get("error", "UNKNOWN")
        )

    print()


if __name__ == "__main__":

    result = test_database_connection()

    display_database_status(result)