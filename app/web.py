from flask import Flask, render_template, request, redirect, url_for

from pathlib import Path

from app.cisco_client import DEVICES, run_command

from app.ai_drift import analyze_drift

from app.config_remediation import apply_configuration


app = Flask(__name__)


# ============================================================
# ROUTER HEALTH
# ============================================================

def get_router_health(router):

    ospf = run_command(
        router,
        "show ip ospf neighbor"
    )

    if ospf is None:

        return {
            "status": "OFFLINE",
            "ospf": "UNKNOWN"
        }

    if "FULL" in ospf:

        return {
            "status": "ONLINE",
            "ospf": "HEALTHY"
        }

    return {
        "status": "ONLINE",
        "ospf": "WARNING"
    }


# ============================================================
# PARSE CISCO INTERFACES
# ============================================================

def parse_interfaces(configuration):

    interfaces = {}

    current_interface = None

    if not configuration:

        return interfaces

    for raw_line in configuration.splitlines():

        line = raw_line.strip()

        if line.startswith("interface "):

            current_interface = line[
                len("interface "):
            ].strip()

            interfaces[current_interface] = []

            continue

        if current_interface is not None and line:

            interfaces[current_interface].append(
                line
            )

    return interfaces


# ============================================================
# INTERFACE DESCRIPTION
# ============================================================

def get_description(interface_lines):

    for line in interface_lines:

        if line.startswith("description "):

            return line

    return None


# ============================================================
# DRIFT DETECTION
# ============================================================

def get_drift_status(router):

    golden_path = Path(
        f"data/golden/{router}.cfg"
    )

    if not golden_path.exists():

        return {
            "status": "UNKNOWN",
            "interface": "",
            "expected": "",
            "current": "",
            "diagnosis": ""
        }


    golden = golden_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )


    live = run_command(
        router,
        "show running-config"
    )


    if live is None:

        return {
            "status": "UNKNOWN",
            "interface": "",
            "expected": "",
            "current": "",
            "diagnosis": ""
        }


    golden_interfaces = parse_interfaces(
        golden
    )

    live_interfaces = parse_interfaces(
        live
    )


    all_interfaces = sorted(
        set(golden_interfaces.keys())
        |
        set(live_interfaces.keys())
    )


    for interface in all_interfaces:

        golden_description = get_description(
            golden_interfaces.get(
                interface,
                []
            )
        )


        live_description = get_description(
            live_interfaces.get(
                interface,
                []
            )
        )


        if golden_description != live_description:

            expected = (
                golden_description
                if golden_description
                else ""
            )


            current = (
                live_description
                if live_description
                else ""
            )


            missing = []

            added = []


            if expected:

                missing.append(
                    expected
                )


            if current:

                added.append(
                    current
                )


            try:

                diagnosis = analyze_drift(
                    router,
                    missing,
                    added
                )

            except Exception as error:

                diagnosis = (
                    "AI analysis unavailable: "
                    + str(error)
                )


            return {
                "status": "DRIFT",
                "interface": interface,
                "expected": expected,
                "current": current,
                "diagnosis": diagnosis
            }


    return {
        "status": "COMPLIANT",
        "interface": "",
        "expected": "",
        "current": "",
        "diagnosis": ""
    }


# ============================================================
# EVENTS
# ============================================================

def create_events(router, health, drift):

    events = []


    if health["status"] == "OFFLINE":

        events.append(
            {
                "router": router,
                "type": "DEVICE",
                "severity": "HIGH",
                "title": "Router Offline",
                "message":
                    f"{router} could not be reached."
            }
        )

        return events


    if health["ospf"] == "WARNING":

        events.append(
            {
                "router": router,
                "type": "OSPF",
                "severity": "MEDIUM",
                "title": "OSPF Warning",
                "message":
                    f"{router} is online, but no FULL "
                    "OSPF neighbor was detected."
            }
        )


    if drift["status"] == "DRIFT":

        events.append(
            {
                "router": router,
                "type": "DRIFT",
                "severity": "HIGH",
                "title": "Configuration Drift",
                "message":
                    f"{router} has configuration drift.",
                "interface":
                    drift["interface"],
                "expected":
                    drift["expected"],
                "current":
                    drift["current"],
                "diagnosis":
                    drift["diagnosis"]
            }
        )


    if (
        health["status"] == "ONLINE"
        and health["ospf"] == "HEALTHY"
        and drift["status"] == "COMPLIANT"
    ):

        events.append(
            {
                "router": router,
                "type": "HEALTH",
                "severity": "INFO",
                "title": "Network Healthy",
                "message":
                    f"{router} is online, OSPF is healthy, "
                    "and configuration is compliant."
            }
        )


    return events


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    routers = []

    events = []

    online = 0

    offline = 0

    ospf_healthy = 0

    ospf_warnings = 0

    drift_count = 0


    for router in DEVICES:

        health = get_router_health(
            router
        )

        drift = get_drift_status(
            router
        )


        if health["status"] == "ONLINE":

            online += 1

        else:

            offline += 1


        if health["ospf"] == "HEALTHY":

            ospf_healthy += 1

        elif health["ospf"] == "WARNING":

            ospf_warnings += 1


        if drift["status"] == "DRIFT":

            drift_count += 1


        routers.append(
            {
                "name":
                    router,

                "status":
                    health["status"],

                "ospf":
                    health["ospf"],

                "drift_status":
                    drift["status"],

                "interface":
                    drift["interface"],

                "expected":
                    drift["expected"],

                "current":
                    drift["current"],

                "diagnosis":
                    drift["diagnosis"]
            }
        )


        events.extend(
            create_events(
                router,
                health,
                drift
            )
        )


    summary = {

        "devices":
            len(DEVICES),

        "online":
            online,

        "offline":
            offline,

        "ospf_healthy":
            ospf_healthy,

        "warnings":
            ospf_warnings,

        "drift":
            drift_count,

        "events":
            len(events)
    }


    return render_template(
        "dashboard.html",
        routers=routers,
        summary=summary,
        events=events
    )


# ============================================================
# APPROVE REMEDIATION
# ============================================================

@app.route(
    "/remediate",
    methods=["POST"]
)
def remediate():

    router = request.form.get(
        "router",
        ""
    ).strip()


    interface = request.form.get(
        "interface",
        ""
    ).strip()


    submitted_expected = request.form.get(
        "expected",
        ""
    ).strip()


    submitted_current = request.form.get(
        "current",
        ""
    ).strip()


    # --------------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------------

    if not router:

        return redirect(
            url_for("dashboard")
        )


    if not interface:

        return redirect(
            url_for("dashboard")
        )


    if router not in DEVICES:

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # LOAD GOLDEN CONFIGURATION
    # --------------------------------------------------------

    golden_path = Path(
        f"data/golden/{router}.cfg"
    )


    if not golden_path.exists():

        print(
            "REMEDIATION BLOCKED: "
            "Golden configuration not found."
        )

        return redirect(
            url_for("dashboard")
        )


    golden = golden_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )


    golden_interfaces = parse_interfaces(
        golden
    )


    # --------------------------------------------------------
    # VERIFY INTERFACE EXISTS
    # --------------------------------------------------------

    if interface not in golden_interfaces:

        print(
            "REMEDIATION BLOCKED: "
            "Interface is not present in golden configuration."
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # GET AUTHORITATIVE EXPECTED VALUE
    # --------------------------------------------------------

    golden_expected = get_description(
        golden_interfaces.get(
            interface,
            []
        )
    )


    golden_expected = (
        golden_expected
        if golden_expected
        else ""
    )


    # --------------------------------------------------------
    # VERIFY SUBMITTED CONFIGURATION
    # --------------------------------------------------------

    if submitted_expected != golden_expected:

        print(
            "REMEDIATION BLOCKED: "
            "Submitted configuration does not match "
            "the golden configuration."
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # VERIFY CURRENT ROUTER STATE
    # --------------------------------------------------------

    live = run_command(
        router,
        "show running-config interface "
        + interface
    )


    if live is None:

        print(
            "REMEDIATION BLOCKED: "
            "Could not verify current router state."
        )

        return redirect(
            url_for("dashboard")
        )


    live_interfaces = parse_interfaces(
        live
    )


    actual_current = get_description(
        live_interfaces.get(
            interface,
            []
        )
    )


    actual_current = (
        actual_current
        if actual_current
        else ""
    )


    # --------------------------------------------------------
    # PREVENT STALE APPROVAL
    # --------------------------------------------------------

    if actual_current != submitted_current:

        print(
            "REMEDIATION BLOCKED: "
            "Router configuration changed "
            "since the approval page was generated."
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # ENSURE DRIFT STILL EXISTS
    # --------------------------------------------------------

    if actual_current == golden_expected:

        print(
            "REMEDIATION BLOCKED: "
            "Router is already compliant."
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # APPLY APPROVED CONFIGURATION
    # --------------------------------------------------------

    print()
    print(
        "===== APPROVED NETPILOT REMEDIATION ====="
    )

    print(
        "Router: "
        + router
    )

    print(
        "Interface: "
        + interface
    )

    print(
        "Current: "
        + actual_current
    )

    print(
        "Expected: "
        + golden_expected
    )


    result = apply_configuration(
        router,
        interface,
        actual_current,
        golden_expected
    )


    print(
        "Remediation result: "
        + str(result)
    )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
