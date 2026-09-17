from pathlib import Path
from datetime import datetime


AUDIT_FILE = Path("data/logs/remediation.log")
# Defines where NetPilot will store remediation history.


def log_remediation(
    router,
    interface,
    old_configuration,
    new_configuration,
    approved,
    result
):
    # Records a remediation event.


    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Creates the log directory if it does not already exist.


    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Creates a readable timestamp.


    entry = f"""
============================================================
NETPILOT REMEDIATION EVENT
============================================================
Timestamp: {timestamp}
Router: {router}
Interface: {interface}

Previous Configuration:
{old_configuration}

New Configuration:
{new_configuration}

Engineer Approved: {approved}
Result: {result}
============================================================

"""
    # Builds the audit record.


    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        # Opens the audit file in append mode.


        file.write(entry)
        # Adds the new event to the audit log.


    print()
    # Adds spacing.


    print("Audit event recorded.")
    # Confirms that the event was logged.
