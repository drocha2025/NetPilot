from app.cisco_client import run_config, run_command
from app.audit_log import log_remediation


def apply_configuration(
    router,
    interface,
    old_configuration,
    new_configuration
):
    """
    Apply an already-approved configuration change.

    Approval is handled by the NetPilot web dashboard.
    This function only performs the approved remediation,
    verifies the result, and records the audit event.
    """

    print()
    print("===== NETPILOT REMEDIATION =====")

    print("Router: " + router)
    print("Interface: " + interface)

    print()
    print("Current configuration:")
    print(old_configuration)

    print()
    print("Approved configuration:")
    print(new_configuration)

    commands = [
        "interface " + interface,
        new_configuration
    ]

    print()
    print("Applying approved configuration...")

    output = run_config(
        router,
        commands
    )

    if output is None:

        print()
        print("Configuration could not be applied.")

        log_remediation(
            router,
            interface,
            old_configuration,
            new_configuration,
            "YES",
            "FAILED"
        )

        return False

    print(output)

    print()
    print("Configuration applied.")

    print()
    print("Verifying configuration...")

    verification = run_command(
        router,
        "show running-config interface "
        + interface
    )

    print()
    print("Verification output:")
    print(verification)

    if verification is None:

        print()
        print("Verification failed: router returned no output.")

        log_remediation(
            router,
            interface,
            old_configuration,
            new_configuration,
            "YES",
            "VERIFICATION FAILED"
        )

        return False

    if new_configuration in verification:

        result = "SUCCESS"

        print()
        print("Verification successful.")

    else:

        result = "VERIFICATION FAILED"

        print()
        print("Verification failed.")

    log_remediation(
        router,
        interface,
        old_configuration,
        new_configuration,
        "YES",
        result
    )

    return result == "SUCCESS"
