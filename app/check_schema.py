from app.database import get_connection
# Imports NetPilot's existing PostgreSQL connection function.


def main():
    # Defines the main function that inspects the current NetPilot database schema.

    connection = None
    # Creates a variable that will hold the PostgreSQL connection.

    try:
        connection = get_connection()
        # Opens a connection to the current NetPilot PostgreSQL database.

        with connection.cursor() as cursor:
            # Creates a database cursor for executing SQL queries.

            cursor.execute(
                """
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
                """
            )
            # Retrieves every column from every table in the public schema.
            # The results are ordered by table and then by column position.

            rows = cursor.fetchall()
            # Retrieves all rows returned by PostgreSQL.

        print()
        # Prints a blank line for readability.

        print("========================================")
        # Prints the top border of the report.

        print("CURRENT NETPILOT DATABASE SCHEMA")
        # Prints the title of the database schema report.

        print("========================================")
        # Prints the bottom border of the report heading.

        current_table = None
        # Tracks the table currently being displayed.

        for row in rows:
            # Loops through every column returned by PostgreSQL.

            table_name = row[0]
            # Gets the table name from the current result.

            column_name = row[1]
            # Gets the column name from the current result.

            data_type = row[2]
            # Gets the PostgreSQL data type.

            nullable = row[3]
            # Gets whether the column allows NULL values.

            default_value = row[4]
            # Gets the column's default value or expression.

            if table_name != current_table:
                # Detects when the report moves to a different table.

                print()
                # Adds spacing before the next table.

                print("TABLE: " + str(table_name))
                # Prints the name of the current table.

                print("----------------------------------------")
                # Prints a separator below the table name.

                current_table = table_name
                # Remembers the current table so we know when it changes.

            print(
                "  "
                + str(column_name)
                + " | TYPE="
                + str(data_type)
                + " | NULL="
                + str(nullable)
                + " | DEFAULT="
                + str(default_value)
            )
            # Prints the definition of the current database column.

        print()
        # Prints a blank line after the report.

    except Exception as error:
        # Handles any database or Python error.

        print("Schema query failed: " + str(error))
        # Displays the error without exposing database credentials.

    finally:
        if connection is not None:
            # Checks whether a database connection was successfully created.

            connection.close()
            # Closes the PostgreSQL connection.


if __name__ == "__main__":
    # Runs the main function when this file is executed directly.

    main()
    # Starts the database schema inspection.