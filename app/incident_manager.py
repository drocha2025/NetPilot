from datetime import datetime, timezone

from app.incident_store import (
    create_incident as db_create_incident,
    find_active_incident,
    update_incident as db_update_incident,
    resolve_incident as db_resolve_incident,
    store_evidence,
    store_audit_event,
    get_active_incidents,
)


def current_timestamp():
    """
    Return a consistent UTC timestamp.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


def normalize_health_snapshot(health_snapshot):
    """
    Convert the monitoring snapshot into a consistent
    dashboard and incident-management data model.
    """

    normalized = []

    if not isinstance(
        health_snapshot,
        dict
    ):
        return normalized

    routers = health_snapshot.get(
        "routers",
        []
    )

    for router_record in routers:

        if not isinstance(
            router_record,
            dict
        ):
            continue

        router = router_record.get(
            "router",
            "UNKNOWN"
        )

        availability = router_record.get(
            "status",
            "UNKNOWN"
        )

        health = router_record.get(
            "health",
            "UNKNOWN"
        )

        issues = router_record.get(
            "issues",
            []
        )

        state = router_record.get(
            "state",
            {}
        )

        ospf = state.get(
            "ospf",
            {}
        )

        wan_state = state.get(
            "wan_state",
            {}
        )

        path_status = wan_state.get(
            "path_status",
            {}
        )

        default_route = wan_state.get(
            "default_route",
            {}
        )

        primary = wan_state.get(
            "primary",
            {}
        )

        backup = wan_state.get(
            "backup",
            {}
        )

        primary_interface = primary.get(
            "interface",
            {}
        )

        primary_bgp = primary.get(
            "bgp",
            {}
        )

        backup_interface = backup.get(
            "interface",
            {}
        )

        backup_bgp = backup.get(
            "bgp",
            {}
        )

        normalized.append(
            {
                "router": router,

                "availability":
                    availability,

                "status":
                    availability,

                "health":
                    health,

                "issues":
                    issues,

                "ospf":
                    ospf,

                "ospf_neighbors":
                    ospf.get(
                        "neighbor_count",
                        0
                    ),

                "wan":
                    wan_state,

                "active_path":
                    path_status.get(
                        "active_path",
                        "UNKNOWN"
                    ),

                "default_route":
                    default_route.get(
                        "status",
                        "UNKNOWN"
                    ),

                "default_next_hop":
                    default_route.get(
                        "next_hop"
                    ),

                "primary_interface":
                    _interface_status(
                        primary_interface
                    ),

                "primary_interface_name":
                    primary_interface.get(
                        "interface"
                    ),

                "primary_bgp":
                    _bgp_status(
                        primary_bgp
                    ),

                "primary_bgp_neighbor":
                    primary_bgp.get(
                        "neighbor"
                    ),

                "backup_interface":
                    _interface_status(
                        backup_interface
                    ),

                "backup_interface_name":
                    backup_interface.get(
                        "interface"
                    ),

                "backup_bgp":
                    _bgp_status(
                        backup_bgp
                    ),

                "backup_bgp_neighbor":
                    backup_bgp.get(
                        "neighbor"
                    ),

                "wan_state":
                    wan_state
            }
        )

    return normalized


def _interface_status(interface):
    """
    Convert Cisco interface state into a simple status.
    """

    if not interface:
        return "NOT_APPLICABLE"

    status = interface.get(
        "status",
        ""
    ).lower()

    protocol = interface.get(
        "protocol",
        ""
    ).lower()

    if (
        status == "up"
        and
        protocol == "up"
    ):
        return "UP"

    return "DOWN"


def _bgp_status(bgp):
    """
    Convert BGP state into a normalized status.
    """

    if not bgp:
        return "NOT_APPLICABLE"

    state = str(
        bgp.get(
            "state",
            ""
        )
    ).upper()

    if state == "ESTABLISHED":
        return "ESTABLISHED"

    return "NOT_ESTABLISHED"


def create_incident(
    router,
    incident_type,
    description,
    health_record
):
    """
    Create a new incident object for persistence.
    """

    timestamp = current_timestamp()

    incident_id = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d%H%M%S%f"
    )

    evidence = build_incident_evidence(
        health_record
    )

    impact = build_incident_impact(
        health_record
    )

    return {
        "incident_id":
            incident_id,

        "router":
            router,

        "incident_type":
            incident_type,

        "status":
            "ACTIVE",

        "description":
            description,

        "impact":
            impact,

        "health":
            health_record.get(
                "health"
            ),

        "active_path":
            health_record.get(
                "active_path"
            ),

        "default_next_hop":
            health_record.get(
                "default_next_hop"
            ),

        "created_at":
            timestamp,

        "updated_at":
            timestamp,

        "evidence":
            evidence,

        "correlation": {
            "symptoms": []
        },

        "ai_analysis":
            None,

        "approval": {
            "status":
                "NOT_STARTED"
        },

        "remediation": {
            "status":
                "NOT_STARTED"
        },

        "validation": {
            "status":
                "NOT_STARTED"
        }
    }


def update_incident(
    incident,
    health_record
):
    """
    Update an existing incident with current
    verified network state.
    """

    incident["status"] = "ACTIVE"

    incident["updated_at"] = (
        current_timestamp()
    )

    incident["health"] = (
        health_record.get(
            "health"
        )
    )

    incident["active_path"] = (
        health_record.get(
            "active_path"
        )
    )

    incident["default_next_hop"] = (
        health_record.get(
            "default_next_hop"
        )
    )

    incident["evidence"] = (
        build_incident_evidence(
            health_record
        )
    )

    incident["impact"] = (
        build_incident_impact(
            health_record
        )
    )

    incident["description"] = (
        build_incident_description(
            incident["incident_type"],
            health_record
        )
    )

    return incident


def resolve_incident_object(
    incident
):
    """
    Mark an incident object resolved.
    """

    timestamp = current_timestamp()

    incident["status"] = "RESOLVED"

    incident["resolved_at"] = (
        timestamp
    )

    incident["updated_at"] = (
        timestamp
    )

    return incident


def build_incident_evidence(
    health_record
):
    """
    Build a compact verified evidence object.
    """

    return {
        "router":
            health_record.get(
                "router"
            ),

        "availability":
            health_record.get(
                "availability"
            ),

        "health":
            health_record.get(
                "health"
            ),

        "issues":
            health_record.get(
                "issues",
                []
            ),

        "ospf":
            health_record.get(
                "ospf"
            ),

        "ospf_neighbors":
            health_record.get(
                "ospf_neighbors"
            ),

        "wan":
            health_record.get(
                "wan"
            ),

        "active_path":
            health_record.get(
                "active_path"
            ),

        "default_route":
            health_record.get(
                "default_route"
            ),

        "default_next_hop":
            health_record.get(
                "default_next_hop"
            ),

        "primary_interface":
            health_record.get(
                "primary_interface"
            ),

        "primary_interface_name":
            health_record.get(
                "primary_interface_name"
            ),

        "primary_bgp":
            health_record.get(
                "primary_bgp"
            ),

        "primary_bgp_neighbor":
            health_record.get(
                "primary_bgp_neighbor"
            ),

        "backup_interface":
            health_record.get(
                "backup_interface"
            ),

        "backup_interface_name":
            health_record.get(
                "backup_interface_name"
            ),

        "backup_bgp":
            health_record.get(
                "backup_bgp"
            ),

        "backup_bgp_neighbor":
            health_record.get(
                "backup_bgp_neighbor"
            )
    }


def build_incident_impact(
    health_record
):
    """
    Build a customer-impact statement.
    """

    router = health_record.get(
        "router",
        "UNKNOWN"
    )

    health = health_record.get(
        "health",
        "UNKNOWN"
    )

    active_path = health_record.get(
        "active_path",
        "UNKNOWN"
    )

    if health == "CRITICAL":

        return (
            "Critical network condition detected "
            "on "
            + router
            + "."
        )

    if (
        health == "DEGRADED"
        and
        active_path == "BACKUP"
    ):

        return (
            "Primary WAN path is unavailable on "
            + router
            + ". Traffic is using the backup "
            "WAN path."
        )

    if health == "DEGRADED":

        return (
            "Network service is degraded on "
            + router
            + "."
        )

    return (
        "No confirmed customer impact."
    )


def build_incident_description(
    incident_type,
    health_record
):
    """
    Build a deterministic incident description.
    """

    router = health_record.get(
        "router",
        "UNKNOWN"
    )

    if incident_type == "DEVICE_OFFLINE":

        return (
            router
            + " is unreachable through the "
            "NetPilot management connection."
        )

    if incident_type == "PRIMARY_WAN_FAILURE":

        return (
            "Primary WAN failure detected on "
            + router
            + ". Primary WAN connectivity is "
            "unavailable and traffic is using "
            "the backup path."
        )

    if incident_type == "PRIMARY_BGP_FAILURE":

        return (
            "Primary WAN BGP session failure "
            "detected on "
            + router
            + "."
        )

    if incident_type == "BACKUP_WAN_FAILURE":

        return (
            "Backup WAN interface failure "
            "detected on "
            + router
            + "."
        )

    if incident_type == "BACKUP_BGP_FAILURE":

        return (
            "Backup WAN BGP session failure "
            "detected on "
            + router
            + "."
        )

    if incident_type == "NO_DEFAULT_ROUTE":

        return (
            "No default route is currently "
            "installed on "
            + router
            + "."
        )

    return (
        "Network incident detected on "
        + router
        + "."
    )


def detect_correlated_incident(
    health_record
):
    """
    Correlate multiple symptoms into one
    primary incident classification.
    """

    router = health_record.get(
        "router",
        "UNKNOWN"
    )

    availability = health_record.get(
        "availability",
        "UNKNOWN"
    )

    health = health_record.get(
        "health",
        "UNKNOWN"
    )

    active_path = health_record.get(
        "active_path",
        "UNKNOWN"
    )

    primary_interface = health_record.get(
        "primary_interface",
        "NOT_APPLICABLE"
    )

    primary_bgp = health_record.get(
        "primary_bgp",
        "NOT_APPLICABLE"
    )

    backup_interface = health_record.get(
        "backup_interface",
        "NOT_APPLICABLE"
    )

    backup_bgp = health_record.get(
        "backup_bgp",
        "NOT_APPLICABLE"
    )

    default_route = health_record.get(
        "default_route",
        "UNKNOWN"
    )

    if availability != "ONLINE":

        return {
            "incident_type":
                "DEVICE_OFFLINE",

            "symptoms": [
                "Router is not reachable."
            ]
        }

    if (
        health == "DEGRADED"
        and
        active_path == "BACKUP"
        and
        primary_interface == "DOWN"
        and
        primary_bgp == "NOT_ESTABLISHED"
    ):

        return {
            "incident_type":
                "PRIMARY_WAN_FAILURE",

            "symptoms": [
                "Primary WAN interface is down.",
                "Primary WAN BGP session is not established.",
                "Traffic is using the backup WAN path.",
                "Backup WAN path is carrying traffic."
            ]
        }

    if (
        primary_interface == "DOWN"
        and
        active_path == "BACKUP"
    ):

        return {
            "incident_type":
                "PRIMARY_WAN_FAILURE",

            "symptoms": [
                "Primary WAN interface is down.",
                "Traffic is using the backup WAN path."
            ]
        }

    if primary_bgp == "NOT_ESTABLISHED":

        return {
            "incident_type":
                "PRIMARY_BGP_FAILURE",

            "symptoms": [
                "Primary WAN BGP session is not established."
            ]
        }

    if backup_interface == "DOWN":

        return {
            "incident_type":
                "BACKUP_WAN_FAILURE",

            "symptoms": [
                "Backup WAN interface is not operational."
            ]
        }

    if backup_bgp == "NOT_ESTABLISHED":

        return {
            "incident_type":
                "BACKUP_BGP_FAILURE",

            "symptoms": [
                "Backup WAN BGP session is not established."
            ]
        }

    if (
        router in ["R1", "R3"]
        and
        default_route != "INSTALLED"
    ):

        return {
            "incident_type":
                "NO_DEFAULT_ROUTE",

            "symptoms": [
                "WAN edge has no installed default route."
            ]
        }

    return None


def find_active_router_incident(
    router,
    incident_type
):
    """
    Find an active incident in PostgreSQL.
    """

    return find_active_incident(
        router,
        incident_type
    )


def _persist_new_incident(
    incident,
    health_record
):
    """
    Persist a newly detected incident.

    The current incident_store.create_incident()
    returns the PostgreSQL database ID as an integer.
    """

    result = db_create_incident(
        incident
    )

    if not isinstance(
        result,
        int
    ):

        print(
            "Incident database creation failed: "
            + str(result)
        )

        return incident

    incident["database_id"] = result

    store_evidence(
        incident["database_id"],
        "HEALTH_SNAPSHOT",
        health_record
    )

    store_audit_event(
        incident["database_id"],
        "INCIDENT_CREATED",
        "NetPilot",
        {
            "incident_type":
                incident["incident_type"],

            "router":
                incident["router"],

            "description":
                incident["description"]
        }
    )

    return incident


def _persist_updated_incident(
    incident,
    health_record
):
    """
    Persist updates to an existing incident.
    """

    result = db_update_incident(
        incident
    )

    if (
        result is not None
        and
        isinstance(result, dict)
        and
        result.get("status") == "FAILED"
    ):

        print(
            "Incident database update failed: "
            + result.get(
                "error",
                "UNKNOWN"
            )
        )

        return incident

    database_id = (
        incident.get(
            "database_id"
        )
    )

    if database_id is not None:

        store_evidence(
            database_id,
            "HEALTH_SNAPSHOT",
            health_record
        )

        store_audit_event(
            database_id,
            "INCIDENT_UPDATED",
            "NetPilot",
            {
                "incident_type":
                    incident[
                        "incident_type"
                    ],

                "router":
                    incident[
                        "router"
                    ],

                "active_path":
                    health_record.get(
                        "active_path"
                    )
            }
        )

    return incident


def process_health_snapshot(
    health_snapshot
):
    """
    Process current network health.

    Incidents are persisted in PostgreSQL.
    """

    normalized = (
        normalize_health_snapshot(
            health_snapshot
        )
    )

    active_incidents = []

    resolved_incidents = []

    for health_record in normalized:

        router = health_record.get(
            "router"
        )

        correlation = (
            detect_correlated_incident(
                health_record
            )
        )

        if correlation is not None:

            incident_type = (
                correlation[
                    "incident_type"
                ]
            )

            existing = (
                find_active_router_incident(
                    router,
                    incident_type
                )
            )

            if existing is None:

                incident = create_incident(
                    router,
                    incident_type,
                    build_incident_description(
                        incident_type,
                        health_record
                    ),
                    health_record
                )

                incident["correlation"] = {
                    "symptoms":
                        correlation.get(
                            "symptoms",
                            []
                        )
                }

                incident = (
                    _persist_new_incident(
                        incident,
                        health_record
                    )
                )

            else:

                incident = {
                    "incident_id":
                        existing.get(
                            "incident_id"
                        ),

                    "database_id":
                        existing.get(
                            "database_id"
                        ),

                    "router":
                        existing.get(
                            "router"
                        ),

                    "incident_type":
                        existing.get(
                            "incident_type"
                        ),

                    "status":
                        existing.get(
                            "status",
                            "ACTIVE"
                        ),

                    "description":
                        existing.get(
                            "description"
                        ),

                    "impact":
                        existing.get(
                            "impact"
                        ),

                    "health":
                        existing.get(
                            "health"
                        ),

                    "active_path":
                        existing.get(
                            "active_path"
                        ),

                    "default_next_hop":
                        existing.get(
                            "default_next_hop"
                        ),

                    "created_at":
                        existing.get(
                            "created_at"
                        ),

                    "updated_at":
                        existing.get(
                            "updated_at"
                        ),

                    "resolved_at":
                        existing.get(
                            "resolved_at"
                        ),

                    "evidence":
                        {},

                    "correlation": {
                        "symptoms":
                            correlation.get(
                                "symptoms",
                                []
                            )
                    },

                    "ai_analysis":
                        None,

                    "approval": {
                        "status":
                            "NOT_STARTED"
                    },

                    "remediation": {
                        "status":
                            "NOT_STARTED"
                    },

                    "validation": {
                        "status":
                            "NOT_STARTED"
                    }
                }

                incident = update_incident(
                    incident,
                    health_record
                )

                incident = (
                    _persist_updated_incident(
                        incident,
                        health_record
                    )
                )

            active_incidents.append(
                incident
            )

        else:

            previous_incidents = (
                get_active_incidents()
            )

            for previous_incident in (
                previous_incidents
            ):

                if (
                    previous_incident.get(
                        "router"
                    ) != router
                ):
                    continue

                incident_type = (
                    previous_incident.get(
                        "incident_type"
                    )
                )

                resolved = (
                    resolve_incident_object(
                        previous_incident
                    )
                )

                resolve_result = (
                    db_resolve_incident(
                        resolved[
                            "incident_id"
                        ]
                    )
                )

                if (
                    resolve_result.get(
                        "status"
                    ) == "RESOLVED"
                ):

                    database_id = (
                        previous_incident.get(
                            "database_id"
                        )
                    )

                    if database_id:

                        store_audit_event(
                            database_id,
                            "INCIDENT_RESOLVED",
                            "NetPilot",
                            {
                                "router":
                                    router,

                                "incident_type":
                                    incident_type
                            }
                        )

                    resolved_incidents.append(
                        resolved
                    )

    database_active = (
        get_active_incidents()
    )

    return {
        "status":
            "COMPLETED",

        "active":
            active_incidents,

        "resolved":
            resolved_incidents,

        "active_count":
            len(database_active),

        "database_active":
            database_active,

        "collected":
            health_snapshot.get(
                "collected"
            )
    }


def display_incident_summary(
    incident_result
):
    """
    Display incident summary.
    """

    print()
    print("========================================")
    print("NETPILOT INCIDENT MANAGER")
    print("========================================")
    print()

    print(
        "Active incidents: "
        + str(
            incident_result.get(
                "active_count",
                0
            )
        )
    )

    for incident in (
        incident_result.get(
            "active",
            []
        )
    ):

        print()

        print(
            "Incident ID: "
            + str(
                incident.get(
                    "incident_id",
                    "UNKNOWN"
                )
            )
        )

        print(
            "Router: "
            + incident.get(
                "router",
                "UNKNOWN"
            )
        )

        print(
            "Type: "
            + incident.get(
                "incident_type",
                "UNKNOWN"
            )
        )

        print(
            "Status: "
            + incident.get(
                "status",
                "UNKNOWN"
            )
        )

        print(
            "Description: "
            + incident.get(
                "description",
                "UNKNOWN"
            )
        )

        print(
            "Impact: "
            + incident.get(
                "impact",
                "UNKNOWN"
            )
        )

        symptoms = (
            incident.get(
                "correlation",
                {}
            ).get(
                "symptoms",
                []
            )
        )

        if symptoms:

            print(
                "Correlated symptoms:"
            )

            for symptom in symptoms:

                print(
                    "  - "
                    + symptom
                )

    print()


if __name__ == "__main__":

    from app.monitoring import (
        collect_health_snapshot
    )

    snapshot = (
        collect_health_snapshot()
    )

    result = (
        process_health_snapshot(
            snapshot
        )
    )

    display_incident_summary(
        result
    )