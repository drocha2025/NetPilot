from app.telemetry_anomaly import (
    get_telemetry,
    group_samples,
    analyze_all_interfaces
)

from app.telemetry_anomaly_store import (
    save_or_update_anomaly,
    resolve_missing_anomalies,
    get_open_anomalies
)


def persist_findings(findings):
    created = 0
    updated = 0

    for finding in findings:
        result = save_or_update_anomaly(
            router=finding["router"],
            interface_name=finding["interface"],
            severity=finding["severity"],
            anomaly_type=finding["type"],
            message=finding["message"],
            detected_at=finding["timestamp"]
        )

        if result is None:
            continue

        if result["action"] == "CREATED":
            created += 1

        elif result["action"] == "UPDATED":
            updated += 1

    return created, updated


def display_summary(
    findings,
    created,
    updated,
    resolved
):
    print()
    print("========================================")
    print("NETPILOT TELEMETRY MONITOR")
    print("========================================")
    print()

    print(
        "Anomalies detected: "
        + str(len(findings))
    )

    print(
        "New anomalies: "
        + str(created)
    )

    print(
        "Existing anomalies updated: "
        + str(updated)
    )

    print(
        "Anomalies resolved: "
        + str(resolved)
    )

    print()

    if not findings:
        print("Telemetry is currently healthy.")
        print()


def display_open_count():
    anomalies = get_open_anomalies()

    print(
        "Open persisted anomalies: "
        + str(len(anomalies))
    )

    print()


def main():
    rows = get_telemetry()

    if not rows:
        print("No telemetry records found.")
        return

    samples = group_samples(rows)

    findings = analyze_all_interfaces(samples)

    created, updated = persist_findings(findings)

    resolved = resolve_missing_anomalies(findings)

    display_summary(
        findings,
        created,
        updated,
        resolved
    )

    display_open_count()


if __name__ == "__main__":
    main()