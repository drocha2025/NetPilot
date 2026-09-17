from app.config_remediation import apply_remediation
# Imports our remediation function.


router = "R3"
# Identifies the router we want to test.


interface = "GigabitEthernet2"
# Identifies the interface we want to change.


configuration = "description NETPILOT-GIT-TEST1"
# Defines the configuration we want to restore.


apply_remediation(
    router,
    interface,
    configuration
)
# Starts the remediation process.
