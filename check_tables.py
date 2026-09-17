from app.database import get_connection
# Imports NetPilot's existing PostgreSQL connection function.

connection = get_connection()
# Opens a connection to the current NetPilot PostgreSQL database.

try:
    with connection.cursor() as cursor:
        # Creates a database cursor for executing SQL commands.

        cursor.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
        # Retrieves every table in PostgreSQL's public schema.

        tables = cursor.fetchall()
        # Retrieves all rows returned by the SQL query.

    print()
    # Prints a blank line for readability.

    print("===== CURRENT NETPILOT DATABASE TABLES =====")
    # Prints a heading for the database inventory.

    for table in tables:
        # Loops through every table returned by PostgreSQL.

        print(table[0])
        # Prints the name of the current table.

    print()
    # Prints a blank line after the results.

finally:
    connection.close()
    # Closes the PostgreSQL connection when the script finishes.