import psycopg  # Imports the PostgreSQL driver used to connect to the NetPilot database.

from app.database import get_connection  # Imports NetPilot's existing database connection function.


def main():
    # Defines the main function that checks the actual foreign-key definitions.

    connection = None
    # Creates a variable that will hold the database connection.

    try:
        # Starts the protected database operation section.

        connection = get_connection()
        # Connects to the current working NetPilot PostgreSQL database.

        with connection.cursor() as cursor:
            # Creates a database cursor for executing SQL queries.

            cursor.execute(
                """
                SELECT
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS referenced_table,
                    ccu.column_name AS referenced_column,
                    rc.delete_rule,
                    rc.update_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                    AND tc.table_name = kcu.table_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.table_schema = ccu.table_schema
                JOIN information_schema.referential_constraints AS rc
                    ON tc.constraint_name = rc.constraint_name
                    AND tc.constraint_schema = rc.constraint_schema
                WHERE tc.table_schema = 'public'
                    AND tc.constraint_type = 'FOREIGN KEY'
                ORDER BY
                    tc.table_name,
                    tc.constraint_name;
                """
            )
            # Retrieves every foreign key and its actual delete/update behavior.

            rows = cursor.fetchall()
            # Stores all returned foreign-key definitions.

        print()
        # Prints a blank line for readability.

        print("========================================")
        # Prints the section separator.

        print("NETPILOT FOREIGN KEY DEFINITIONS")
        # Prints the section title.

        print("========================================")
        # Prints the closing separator.

        print()

        for row in rows:
            # Loops through every foreign-key definition.

            print(
                str(row[0])
                + " | "
                + str(row[1])
                + "."
                + str(row[2])
                + " -> "
                + str(row[3])
                + "."
                + str(row[4])
                + " | DELETE="
                + str(row[5])
                + " | UPDATE="
                + str(row[6])
            )
            # Displays the complete relationship and its referential actions.

        print()
        # Prints a final blank line.

    except Exception as error:
        # Handles any database or Python error.

        print("Foreign-key inspection failed: " + str(error))
        # Displays the error message.

    finally:
        # Runs regardless of whether the query succeeds or fails.

        if connection is not None:
            # Checks whether a database connection exists.

            connection.close()
            # Closes the database connection cleanly.


if __name__ == "__main__":
    # Ensures the main function executes only when this module is run directly.

    main()
    # Starts the foreign-key inspection.