from app.database import get_connection


MINIMUM_SAMPLES = 3
STABLE_CHANGE_PERCENT = 5.0
VARIABLE_RANGE_PERCENT = 20.0


def get_interface_samples():
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
                    t.collected_at,
                    t.input_rate_bps,
                    t.output_rate_bps
                FROM interface_capacity c
                INNER JOIN interface_telemetry t
                    ON c.router = t.router
                    AND c.interface_name = t.interface_name
                WHERE c.bandwidth_bps > 0
                ORDER BY
                    c.router,
                    c.interface_name,
                    t.collected_at;
                """
            )

            return cursor.fetchall()

    except Exception as error:
        print(
            "Failed to retrieve interface samples: "
            + str(error)
        )
        return []

    finally:
        if connection is not None:
            connection.close()


def group_samples(rows):
    grouped = {}

    for row in rows:
        (
            router,
            interface_name,
            bandwidth_bps,
            collected_at,
            input_rate_bps,
            output_rate_bps
        ) = row

        key = (
            router,
            interface_name
        )

        if key not in grouped:
            grouped[key] = {
                "router": router,
                "interface": interface_name,
                "bandwidth_bps": bandwidth_bps,
                "samples": []
            }

        grouped[key]["samples"].append(
            {
                "collected_at": collected_at,
                "input_rate_bps": input_rate_bps or 0,
                "output_rate_bps": output_rate_bps or 0
            }
        )

    return grouped


def calculate_utilization(rate_bps, bandwidth_bps):
    if bandwidth_bps <= 0:
        return 0.0

    return (
        rate_bps
        / bandwidth_bps
        * 100
    )


def calculate_direction_trend(utilizations):
    if len(utilizations) < MINIMUM_SAMPLES:
        return "UNKNOWN"

    first_value = utilizations[0]
    last_value = utilizations[-1]

    total_change = last_value - first_value

    if abs(total_change) <= STABLE_CHANGE_PERCENT:
        value_range = (
            max(utilizations)
            - min(utilizations)
        )

        if value_range >= VARIABLE_RANGE_PERCENT:
            return "VARIABLE"

        return "STABLE"

    if total_change > 0:
        value_range = (
            max(utilizations)
            - min(utilizations)
        )

        if value_range >= VARIABLE_RANGE_PERCENT:
            return "VARIABLE"

        return "INCREASING"

    value_range = (
        max(utilizations)
        - min(utilizations)
    )

    if value_range >= VARIABLE_RANGE_PERCENT:
        return "VARIABLE"

    return "DECREASING"


def analyze_interface_trend(interface_data):
    bandwidth_bps = interface_data["bandwidth_bps"]
    samples = interface_data["samples"]

    input_utilizations = []
    output_utilizations = []

    for sample in samples:
        input_utilization = calculate_utilization(
            sample["input_rate_bps"],
            bandwidth_bps
        )

        output_utilization = calculate_utilization(
            sample["output_rate_bps"],
            bandwidth_bps
        )

        input_utilizations.append(
            input_utilization
        )

        output_utilizations.append(
            output_utilization
        )

    input_trend = calculate_direction_trend(
        input_utilizations
    )

    output_trend = calculate_direction_trend(
        output_utilizations
    )

    if input_trend == "INCREASING" or output_trend == "INCREASING":
        overall_trend = "INCREASING"

    elif (
        input_trend == "VARIABLE"
        or output_trend == "VARIABLE"
    ):
        overall_trend = "VARIABLE"

    elif (
        input_trend == "DECREASING"
        or output_trend == "DECREASING"
    ):
        overall_trend = "DECREASING"

    elif (
        input_trend == "STABLE"
        and output_trend == "STABLE"
    ):
        overall_trend = "STABLE"

    else:
        overall_trend = "UNKNOWN"

    return {
        "router": interface_data["router"],
        "interface": interface_data["interface"],
        "bandwidth_bps": bandwidth_bps,
        "sample_count": len(samples),
        "input_trend": input_trend,
        "output_trend": output_trend,
        "overall_trend": overall_trend,
        "first_input_utilization": input_utilizations[0]
        if input_utilizations else 0,
        "last_input_utilization": input_utilizations[-1]
        if input_utilizations else 0,
        "first_output_utilization": output_utilizations[0]
        if output_utilizations else 0,
        "last_output_utilization": output_utilizations[-1]
        if output_utilizations else 0
    }


def analyze_all_interfaces(grouped_samples):
    results = []

    for interface_data in grouped_samples.values():
        results.append(
            analyze_interface_trend(
                interface_data
            )
        )

    return results


def display_trends(results):
    print()
    print("========================================")
    print("NETPILOT CAPACITY TREND ANALYSIS")
    print("========================================")
    print()

    if not results:
        print("No capacity trend data available.")
        print()
        return

    trend_counts = {
        "STABLE": 0,
        "INCREASING": 0,
        "DECREASING": 0,
        "VARIABLE": 0,
        "UNKNOWN": 0
    }

    for result in results:
        trend = result["overall_trend"]

        trend_counts[trend] += 1

        print(
            result["router"]
            + " "
            + result["interface"]
        )

        print(
            "  Samples: "
            + str(result["sample_count"])
        )

        print(
            "  Input Trend: "
            + result["input_trend"]
        )

        print(
            "  Output Trend: "
            + result["output_trend"]
        )

        print(
            "  First Input: "
            + str(
                round(
                    result["first_input_utilization"],
                    2
                )
            )
            + "%"
        )

        print(
            "  Last Input: "
            + str(
                round(
                    result["last_input_utilization"],
                    2
                )
            )
            + "%"
        )

        print(
            "  First Output: "
            + str(
                round(
                    result["first_output_utilization"],
                    2
                )
            )
            + "%"
        )

        print(
            "  Last Output: "
            + str(
                round(
                    result["last_output_utilization"],
                    2
                )
            )
            + "%"
        )

        print(
            "  Overall Trend: "
            + result["overall_trend"]
        )

        print()

    print("----------------------------------------")
    print("TREND SUMMARY")
    print("----------------------------------------")
    print()

    print(
        "STABLE: "
        + str(trend_counts["STABLE"])
    )

    print(
        "INCREASING: "
        + str(trend_counts["INCREASING"])
    )

    print(
        "DECREASING: "
        + str(trend_counts["DECREASING"])
    )

    print(
        "VARIABLE: "
        + str(trend_counts["VARIABLE"])
    )

    print(
        "UNKNOWN: "
        + str(trend_counts["UNKNOWN"])
    )

    print()


def main():
    rows = get_interface_samples()

    if not rows:
        print("No interface telemetry samples found.")
        return

    grouped_samples = group_samples(rows)

    results = analyze_all_interfaces(
        grouped_samples
    )

    display_trends(results)


if __name__ == "__main__":
    main()