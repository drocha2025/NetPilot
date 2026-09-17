from app.capacity_trends import (
    get_interface_samples,
    group_samples,
    calculate_utilization
)


FORECAST_THRESHOLD = 75.0

MINIMUM_SAMPLES = 3

MAX_FORECAST_DAYS = 90.0


def calculate_linear_slope(samples):
    if len(samples) < MINIMUM_SAMPLES:
        return None

    first_time = samples[0]["collected_at"]

    x_values = []
    y_values = []

    for sample in samples:

        elapsed_seconds = (
            sample["collected_at"]
            - first_time
        ).total_seconds()

        elapsed_hours = (
            elapsed_seconds
            / 3600.0
        )

        x_values.append(
            elapsed_hours
        )

        y_values.append(
            sample["utilization"]
        )

    x_average = (
        sum(x_values)
        / len(x_values)
    )

    y_average = (
        sum(y_values)
        / len(y_values)
    )

    numerator = 0.0
    denominator = 0.0

    for index in range(
        len(x_values)
    ):

        x_difference = (
            x_values[index]
            - x_average
        )

        y_difference = (
            y_values[index]
            - y_average
        )

        numerator += (
            x_difference
            * y_difference
        )

        denominator += (
            x_difference
            * x_difference
        )

    if denominator == 0:
        return None

    return (
        numerator
        / denominator
    )


def build_direction_samples(
    interface_data,
    direction
):
    samples = []

    for sample in interface_data["samples"]:

        if direction == "input":

            rate_bps = (
                sample["input_rate_bps"]
            )

        else:

            rate_bps = (
                sample["output_rate_bps"]
            )

        utilization = calculate_utilization(
            rate_bps,
            interface_data[
                "bandwidth_bps"
            ]
        )

        samples.append(
            {
                "collected_at":
                    sample["collected_at"],

                "utilization":
                    utilization
            }
        )

    return samples


def forecast_direction(
    interface_data,
    direction,
    threshold
):
    samples = build_direction_samples(
        interface_data,
        direction
    )

    if len(samples) < MINIMUM_SAMPLES:

        return {
            "status":
                "INSUFFICIENT_DATA",

            "slope_per_hour":
                None,

            "current_utilization":
                None,

            "hours_to_threshold":
                None,

            "days_to_threshold":
                None
        }

    slope = calculate_linear_slope(
        samples
    )

    current_utilization = (
        samples[-1]["utilization"]
    )

    if slope is None:

        return {
            "status":
                "INSUFFICIENT_DATA",

            "slope_per_hour":
                None,

            "current_utilization":
                current_utilization,

            "hours_to_threshold":
                None,

            "days_to_threshold":
                None
        }

    if current_utilization >= threshold:

        return {
            "status":
                "THRESHOLD_REACHED",

            "slope_per_hour":
                slope,

            "current_utilization":
                current_utilization,

            "hours_to_threshold":
                0.0,

            "days_to_threshold":
                0.0
        }

    if slope <= 0:

        return {
            "status":
                "NO_INCREASING_TREND",

            "slope_per_hour":
                slope,

            "current_utilization":
                current_utilization,

            "hours_to_threshold":
                None,

            "days_to_threshold":
                None
        }

    utilization_remaining = (
        threshold
        - current_utilization
    )

    hours_to_threshold = (
        utilization_remaining
        / slope
    )

    days_to_threshold = (
        hours_to_threshold
        / 24.0
    )

    if days_to_threshold > MAX_FORECAST_DAYS:

        return {
            "status":
                "NO_ACTIONABLE_FORECAST",

            "slope_per_hour":
                slope,

            "current_utilization":
                current_utilization,

            "hours_to_threshold":
                hours_to_threshold,

            "days_to_threshold":
                days_to_threshold
        }

    return {
        "status":
            "FORECAST_AVAILABLE",

        "slope_per_hour":
            slope,

        "current_utilization":
            current_utilization,

        "hours_to_threshold":
            hours_to_threshold,

        "days_to_threshold":
            days_to_threshold
    }


def forecast_interface(
    interface_data,
    threshold
):
    input_forecast = forecast_direction(
        interface_data,
        "input",
        threshold
    )

    output_forecast = forecast_direction(
        interface_data,
        "output",
        threshold
    )

    forecasts = [
        (
            "input",
            input_forecast
        ),
        (
            "output",
            output_forecast
        )
    ]

    actionable_forecasts = [
        forecast
        for direction, forecast
        in forecasts
        if forecast["status"]
        in (
            "FORECAST_AVAILABLE",
            "THRESHOLD_REACHED"
        )
    ]

    if not actionable_forecasts:

        if (
            input_forecast["status"]
            == "THRESHOLD_REACHED"
            or
            output_forecast["status"]
            == "THRESHOLD_REACHED"
        ):

            overall_status = (
                "THRESHOLD_REACHED"
            )

        elif (
            input_forecast["status"]
            == "INSUFFICIENT_DATA"
            and
            output_forecast["status"]
            == "INSUFFICIENT_DATA"
        ):

            overall_status = (
                "INSUFFICIENT_DATA"
            )

        else:

            overall_status = (
                "NO_ACTIONABLE_FORECAST"
            )

        days_to_threshold = None

    else:

        threshold_times = []

        for forecast in actionable_forecasts:

            if (
                forecast[
                    "days_to_threshold"
                ]
                is not None
            ):

                threshold_times.append(
                    forecast[
                        "days_to_threshold"
                    ]
                )

        if threshold_times:

            days_to_threshold = min(
                threshold_times
            )

            if days_to_threshold == 0:

                overall_status = (
                    "THRESHOLD_REACHED"
                )

            else:

                overall_status = (
                    "FORECAST_AVAILABLE"
                )

        else:

            days_to_threshold = None

            overall_status = (
                "NO_ACTIONABLE_FORECAST"
            )

    return {
        "router":
            interface_data["router"],

        "interface":
            interface_data["interface"],

        "threshold":
            threshold,

        "input_forecast":
            input_forecast,

        "output_forecast":
            output_forecast,

        "overall_status":
            overall_status,

        "days_to_threshold":
            days_to_threshold
    }


def forecast_all_interfaces(
    grouped_samples
):
    results = []

    for interface_data in (
        grouped_samples.values()
    ):

        results.append(
            forecast_interface(
                interface_data,
                FORECAST_THRESHOLD
            )
        )

    return results


def display_forecasts(results):
    print()
    print("========================================")
    print("NETPILOT CAPACITY FORECAST")
    print("========================================")
    print()

    if not results:

        print(
            "No capacity forecast data available."
        )

        print()

        return

    forecast_count = 0

    reached_count = 0

    no_forecast_count = 0

    insufficient_count = 0

    for result in results:

        print(
            result["router"]
            + " "
            + result["interface"]
        )

        print(
            "  Forecast Threshold: "
            + str(
                result["threshold"]
            )
            + "%"
        )

        input_forecast = (
            result["input_forecast"]
        )

        output_forecast = (
            result["output_forecast"]
        )

        print()
        print("  INPUT")

        print(
            "    Current: "
            + (
                str(
                    round(
                        input_forecast[
                            "current_utilization"
                        ],
                        2
                    )
                )
                + "%"
                if input_forecast[
                    "current_utilization"
                ] is not None
                else "N/A"
            )
        )

        print(
            "    Slope: "
            + (
                str(
                    round(
                        input_forecast[
                            "slope_per_hour"
                        ],
                        6
                    )
                )
                + "%/hour"
                if input_forecast[
                    "slope_per_hour"
                ] is not None
                else "N/A"
            )
        )

        print(
            "    Status: "
            + input_forecast["status"]
        )

        if (
            input_forecast[
                "status"
            ]
            == "FORECAST_AVAILABLE"
        ):

            print(
                "    Days to Threshold: "
                + str(
                    round(
                        input_forecast[
                            "days_to_threshold"
                        ],
                        2
                    )
                )
            )

        print()
        print("  OUTPUT")

        print(
            "    Current: "
            + (
                str(
                    round(
                        output_forecast[
                            "current_utilization"
                        ],
                        2
                    )
                )
                + "%"
                if output_forecast[
                    "current_utilization"
                ] is not None
                else "N/A"
            )
        )

        print(
            "    Slope: "
            + (
                str(
                    round(
                        output_forecast[
                            "slope_per_hour"
                        ],
                        6
                    )
                )
                + "%/hour"
                if output_forecast[
                    "slope_per_hour"
                ] is not None
                else "N/A"
            )
        )

        print(
            "    Status: "
            + output_forecast["status"]
        )

        if (
            output_forecast[
                "status"
            ]
            == "FORECAST_AVAILABLE"
        ):

            print(
                "    Days to Threshold: "
                + str(
                    round(
                        output_forecast[
                            "days_to_threshold"
                        ],
                        2
                    )
                )
            )

        print()

        print(
            "  Overall Status: "
            + result["overall_status"]
        )

        if (
            result["overall_status"]
            == "FORECAST_AVAILABLE"
        ):

            print(
                "  Projected Threshold: "
                + str(
                    round(
                        result[
                            "days_to_threshold"
                        ],
                        2
                    )
                )
                + " days"
            )

        elif (
            result["overall_status"]
            == "NO_ACTIONABLE_FORECAST"
        ):

            print(
                "  Forecast: No actionable "
                "threshold breach within "
                + str(
                    MAX_FORECAST_DAYS
                )
                + " days."
            )

        print()

        if (
            result["overall_status"]
            == "FORECAST_AVAILABLE"
        ):

            forecast_count += 1

        elif (
            result["overall_status"]
            == "THRESHOLD_REACHED"
        ):

            reached_count += 1

        elif (
            result["overall_status"]
            == "INSUFFICIENT_DATA"
        ):

            insufficient_count += 1

        else:

            no_forecast_count += 1

    print("----------------------------------------")
    print("FORECAST SUMMARY")
    print("----------------------------------------")
    print()

    print(
        "Forecast Available: "
        + str(
            forecast_count
        )
    )

    print(
        "Threshold Already Reached: "
        + str(
            reached_count
        )
    )

    print(
        "No Actionable Forecast: "
        + str(
            no_forecast_count
        )
    )

    print(
        "Insufficient Data: "
        + str(
            insufficient_count
        )
    )

    print()


def main():

    rows = get_interface_samples()

    if not rows:

        print(
            "No interface telemetry samples found."
        )

        return

    grouped_samples = group_samples(
        rows
    )

    results = forecast_all_interfaces(
        grouped_samples
    )

    display_forecasts(
        results
    )


if __name__ == "__main__":

    main()