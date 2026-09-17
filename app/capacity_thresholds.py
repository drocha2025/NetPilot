from app.capacity_analytics import get_capacity_utilization


HEALTHY_THRESHOLD = 60.0
WATCH_THRESHOLD = 75.0
HIGH_THRESHOLD = 90.0


def classify_utilization(utilization):
    if utilization < HEALTHY_THRESHOLD:
        return "HEALTHY"

    if utilization <= WATCH_THRESHOLD:
        return "WATCH"

    if utilization <= HIGH_THRESHOLD:
        return "HIGH"

    return "CRITICAL"


def determine_interface_status(result):
    input_status = classify_utilization(
        result["current_input_utilization"]
    )

    output_status = classify_utilization(
        result["current_output_utilization"]
    )

    status_order = {
        "HEALTHY": 0,
        "WATCH": 1,
        "HIGH": 2,
        "CRITICAL": 3
    }

    if status_order[input_status] >= status_order[output_status]:
        overall_status = input_status
    else:
        overall_status = output_status

    return {
        "router": result["router"],
        "interface": result["interface"],
        "capacity_mbps": result["bandwidth_bps"] / 1000000,
        "current_input_utilization": result[
            "current_input_utilization"
        ],
        "current_output_utilization": result[
            "current_output_utilization"
        ],
        "average_input_utilization": result[
            "average_input_utilization"
        ],
        "average_output_utilization": result[
            "average_output_utilization"
        ],
        "peak_input_utilization": result[
            "peak_input_utilization"
        ],
        "peak_output_utilization": result[
            "peak_output_utilization"
        ],
        "input_status": input_status,
        "output_status": output_status,
        "overall_status": overall_status
    }


def evaluate_capacity(results):
    evaluations = []

    for result in results:
        evaluations.append(
            determine_interface_status(result)
        )

    return evaluations


def display_capacity_status(evaluations):
    print()
    print("========================================")
    print("NETPILOT CAPACITY THRESHOLD ENGINE")
    print("========================================")
    print()

    if not evaluations:
        print("No capacity evaluations available.")
        print()
        return

    status_counts = {
        "HEALTHY": 0,
        "WATCH": 0,
        "HIGH": 0,
        "CRITICAL": 0
    }

    for evaluation in evaluations:
        status = evaluation["overall_status"]
        status_counts[status] += 1

        print(
            evaluation["router"]
            + " "
            + evaluation["interface"]
        )

        print(
            "  Capacity: "
            + str(round(evaluation["capacity_mbps"], 2))
            + " Mbps"
        )

        print(
            "  Current Input: "
            + str(
                round(
                    evaluation["current_input_utilization"],
                    2
                )
            )
            + "% | "
            + evaluation["input_status"]
        )

        print(
            "  Current Output: "
            + str(
                round(
                    evaluation["current_output_utilization"],
                    2
                )
            )
            + "% | "
            + evaluation["output_status"]
        )

        print(
            "  Peak Input: "
            + str(
                round(
                    evaluation["peak_input_utilization"],
                    2
                )
            )
            + "%"
        )

        print(
            "  Peak Output: "
            + str(
                round(
                    evaluation["peak_output_utilization"],
                    2
                )
            )
            + "%"
        )

        print(
            "  Overall Status: "
            + evaluation["overall_status"]
        )

        print()

    print("----------------------------------------")
    print("CAPACITY STATUS SUMMARY")
    print("----------------------------------------")
    print()

    print(
        "HEALTHY: "
        + str(status_counts["HEALTHY"])
    )

    print(
        "WATCH: "
        + str(status_counts["WATCH"])
    )

    print(
        "HIGH: "
        + str(status_counts["HIGH"])
    )

    print(
        "CRITICAL: "
        + str(status_counts["CRITICAL"])
    )

    print()


def main():
    utilization_results = get_capacity_utilization()

    evaluations = evaluate_capacity(
        utilization_results
    )

    display_capacity_status(evaluations)


if __name__ == "__main__":
    main()