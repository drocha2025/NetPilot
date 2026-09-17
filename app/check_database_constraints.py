import psycopg  # Imports the PostgreSQL driver used to connect to the NetPilot database.

from app.database import get_connection  # Imports NetPilot's existing database connection function.


def main():
    # Defines the main function that performs the database inspection.

    connection = None
    # Creates a variable that will hold the database connection.

    try:
        # Starts the protected section where database operations are performed.

        connection = get_connection()
        # Connects to the currently working NetPilot PostgreSQL database.

        with connection.cursor() as cursor:
            # Creates a database cursor used to execute SQL queries.

            cursor.execute(
                """
                SELECT
                    tc.table_name,
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name
                FROM information_schema.table_constraints AS tc
                LEFT JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                    AND tc.table_name = kcu.table_name
                WHERE tc.table_schema = 'public'
                ORDER BY
                    tc.table_name,
                    tc.constraint_name,
                    kcu.ordinal_position;
                """
            )
            # Retrieves primary-key, unique, and foreign-key constraint information.

            constraint_rows = cursor.fetchall()
            # Stores all returned constraint rows in memory.

            cursor.execute(
                """
                SELECT
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY
                    tablename,
                    indexname;
                """
            )
            # Retrieves all indexes defined on the public NetPilot tables.

            index_rows = cursor.fetchall()
            # Stores all returned index rows in memory.

        print()
        # Prints a blank line for readability.

        print("========================================")
        # Prints the beginning of the constraints section.

        print("NETPILOT DATABASE CONSTRAINTS")
        # Prints the section title.

        print("========================================")
        # Prints the closing separator.

        print()
        # Prints a blank line.

        for row in constraint_rows:
            # Loops through every database constraint returned by PostgreSQL.

            print(
                str(row[0])
                + " | "
                + str(row[1])
                + " | TYPE="
                + str(row[2])
                + " | COLUMN="
                + str(row[3])
            )
            # Prints the table, constraint name, constraint type, and associated column.

        print()
        # Separates the constraints section from the indexes section.

        print("========================================")
        # Prints the beginning of the indexes section.

        print("NETPILOT DATABASE INDEXES")
        # Prints the section title.

        print("========================================")
        # Prints the closing separator.

        print()
        # Prints a blank line.

        for row in index_rows:
            # Loops through every database index returned by PostgreSQL.

            print(
                str(row[0])
                + " | "
                + str(row[1])
                + " | "
                + str(row[2])
            )
            # Prints the table name, index name, and complete PostgreSQL index definition.

        print()
        # Prints a final blank line.

    except Exception as error:
        # Handles any database or Python error.

        print("Database inspection failed: " + str(error))
        # Displays the error so we can troubleshoot it.

    finally:
        # Runs regardless of whether the database query succeeded or failed.

        if connection is not None:
            # Checks whether a database connection was successfully created.

            connection.close()
            # Closes the PostgreSQL connection cleanly.


if __name__ == "__main__":
    # Ensures the main function runs only when this file is executed directly.

    main()
    # Starts the database inspection.