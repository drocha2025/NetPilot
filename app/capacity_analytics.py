from app.database import get_connection


def get_capacity_utilization():
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.router,
                    c.interface_name,
                    c.bandwidth_bps,
                    COUNT(t.id) AS sample_count,

                    MAX(t.input_rate_bps) AS peak_input_bps,
                    MAX(t.output_rate_bps) AS peak_output_bps,

                    MIN(t.input_rate_bps) AS minimum_input_bps,
                    MIN(t.output_rate_bps) AS minimum_output_bps,

                    AVG(t.input_rate_bps) AS average_input_bps,
                    AVG(t.output_rate_bps) AS average_output_bps,

                    (
                        SELECT t2.input_rate_bps
                        FROM interface_telemetry t2
                        WHERE t2.router = c.router
                          AND t2.interface_name = c.interface_name
                        ORDER BY t2.collected_at DESC
                        LIMIT 1
                    ) AS current_input_bps,

                    (
                        SELECT t3.output_rate_bps
                        FROM interface_telemetry t3
                        WHERE t3.router = c.router
                          AND t3.interface_name = c.interface_name
                        ORDER BY t3.collected_at DESC
                        LIMIT 1
                    ) AS current_output_bps

                FROM interface_capacity c

                LEFT JOIN interface_telemetry t
                    ON c.router = t.router
                    AND c.interface_name = t.interface_name

                GROUP BY
                    c.router,
                    c.interface_name,
                    c.bandwidth_bps

                ORDER BY
                    c.router,
                    c.interface_name;
                """
            )

            rows = cursor.fetchall()

        results = []

        for row in rows:
            (
                router,
                interface_name,
                bandwidth_bps,
                sample_count,
                peak_input_bps,
                peak_output_bps,
                minimum_input_bps,
                minimum_output_bps,
                average_input_bps,
                average_output_bps,
                current_input_bps,
                current_output_bps
            ) = row

            if bandwidth_bps <= 0:
                continue

            peak_input_utilization = (
                peak_input_bps / bandwidth_bps * 100
                if peak_input_bps is not None
                else 0
            )

            peak_output_utilization = (
                peak_output_bps / bandwidth_bps * 100
                if peak_output_bps is not None
                else 0
            )

            minimum_input_utilization = (
                minimum_input_bps / bandwidth_bps * 100
                if minimum_input_bps is not None
                else 0
            )

            minimum_output_utilization = (
                minimum_output_bps / bandwidth_bps * 100
                if minimum_output_bps is not None
                else 0
            )

            average_input_utilization = (
                average_input_bps / bandwidth_bps * 100
                if average_input_bps is not None
                else 0
            )

            average_output_utilization = (
                average_output_bps / bandwidth_bps * 100
                if average_output_bps is not None
                else 0
            )

            current_input_utilization = (
                current_input_bps / bandwidth_bps * 100
                if current_input_bps is not None
                else 0
            )

            current_output_utilization = (
                current_output_bps / bandwidth_bps * 100
                if current_output_bps is not None
                else 0
            )

            results.append(
                {
                    "router": router,
                    "interface": interface_name,
                    "bandwidth_bps": bandwidth_bps,
                    "sample_count": sample_count,
                    "current_input_utilization": current_input_utilization,
                    "current_output_utilization": current_output_utilization,
                    "average_input_utilization": average_input_utilization,
                    "average_output_utilization": average_output_utilization,
                    "peak_input_utilization": peak_input_utilization,
                    "peak_output_utilization": peak_output_utilization,
                    "minimum_input_utilization": minimum_input_utilization,
                    "minimum_output_utilization": minimum_output_utilization
                }
            )

        return results

    except Exception as error:
        print("Failed to calculate capacity utilization: " + str(error))
        return []

    finally:
        if connection is not None:
            connection.close()


def display_results(results):
    print()
    print("========================================")
    print("NETPILOT CAPACITY UTILIZATION")
    print("========================================")
    print()

    if not results:
        print("No capacity utilization data available.")
        print()
        return

    for result in results:
        print(
            result["router"]
            + " "
            + result["interface"]
        )

        print(
            "  Capacity: "
            + str(round(result["bandwidth_bps"] / 1000000, 2))
            + " Mbps"
        )

        print(
            "  Samples: "
            + str(result["sample_count"])
        )

        print(
            "  Current Input: "
            + str(round(result["current_input_utilization"], 2))
            + "%"
        )

        print(
            "  Current Output: "
            + str(round(result["current_output_utilization"], 2))
            + "%"
        )

        print(
            "  Average Input: "
            + str(round(result["average_input_utilization"], 2))
            + "%"
        )

        print(
            "  Average Output: "
            + str(round(result["average_output_utilization"], 2))
            + "%"
        )

        print(
            "  Peak Input: "
            + str(round(result["peak_input_utilization"], 2))
            + "%"
        )

        print(
            "  Peak Output: "
            + str(round(result["peak_output_utilization"], 2))
            + "%"
        )

        print(
            "  Minimum Input: "
            + str(round(result["minimum_input_utilization"], 2))
            + "%"
        )

        print(
            "  Minimum Output: "
            + str(round(result["minimum_output_utilization"], 2))
            + "%"
        )

        print()


def main():
    results = get_capacity_utilization()
    display_results(results)


if __name__ == "__main__":
    main()