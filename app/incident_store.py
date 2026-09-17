import json

from app.database import get_connection


def create_incident(incident):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO incidents (
                    incident_id,
                    router,
                    incident_type,
                    status,
                    description,
                    impact,
                    health,
                    active_path,
                    default_next_hop,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                RETURNING id
                """,
                (
                    incident["incident_id"],
                    incident["router"],
                    incident["incident_type"],
                    incident["status"],
                    incident["description"],
                    incident["impact"],
                    incident.get("health"),
                    incident.get("active_path"),
                    incident.get("default_next_hop"),
                    incident["created_at"],
                    incident["updated_at"],
                ),
            )

            database_id = cursor.fetchone()[0]

        connection.commit()

        return database_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def find_active_incident(
    router,
    incident_type
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    incident_id,
                    router,
                    incident_type,
                    status,
                    description,
                    impact,
                    health,
                    active_path,
                    default_next_hop,
                    created_at,
                    updated_at,
                    resolved_at
                FROM incidents
                WHERE router = %s
                  AND incident_type = %s
                  AND status = 'ACTIVE'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (
                    router,
                    incident_type,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "database_id": row[0],
                "incident_id": row[1],
                "router": row[2],
                "incident_type": row[3],
                "status": row[4],
                "description": row[5],
                "impact": row[6],
                "health": row[7],
                "active_path": row[8],
                "default_next_hop": row[9],
                "created_at": row[10],
                "updated_at": row[11],
                "resolved_at": row[12],
            }

    finally:
        connection.close()


def update_incident(incident):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE incidents
                SET
                    status=%s,
                    description=%s,
                    impact=%s,
                    health=%s,
                    active_path=%s,
                    default_next_hop=%s,
                    updated_at=%s
                WHERE id=%s
                """,
                (
                    incident["status"],
                    incident["description"],
                    incident["impact"],
                    incident.get("health"),
                    incident.get("active_path"),
                    incident.get("default_next_hop"),
                    incident["updated_at"],
                    incident["database_id"],
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def resolve_incident(
    incident_id
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE incidents
                SET
                    status='RESOLVED',
                    updated_at=NOW(),
                    resolved_at=NOW()
                WHERE incident_id=%s
                  AND status='ACTIVE'
                """,
                (
                    incident_id,
                ),
            )

        connection.commit()

        return {
            "status": "RESOLVED",
            "incident_id": incident_id,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def store_evidence(
    incident_database_id,
    evidence_type,
    evidence
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO incident_evidence (
                    incident_id,
                    evidence_type,
                    evidence
                )
                VALUES (
                    %s,
                    %s,
                    %s::jsonb
                )
                """,
                (
                    incident_database_id,
                    evidence_type,
                    json.dumps(
                        evidence,
                        default=str
                    ),
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_incident_evidence(
    incident_database_id
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    evidence_type,
                    evidence,
                    collected_at
                FROM incident_evidence
                WHERE incident_id=%s
                ORDER BY collected_at ASC, id ASC
                """,
                (
                    incident_database_id,
                ),
            )

            rows = cursor.fetchall()

            evidence = []

            for row in rows:
                evidence.append(
                    {
                        "id": row[0],
                        "evidence_type": row[1],
                        "evidence": row[2],
                        "collected_at": row[3],
                    }
                )

            return evidence

    finally:
        connection.close()


def store_ai_analysis(
    incident_database_id,
    model,
    root_cause,
    confidence,
    evidence,
    symptoms,
    customer_impact,
    recommended_action,
    risk,
    validation,
    assumptions,
    raw_response
):
    connection = get_connection()

    try:
        analysis_document = {
            "model": model,
            "evidence": evidence,
            "symptoms": symptoms,
            "customer_impact": customer_impact,
            "recommended_action": recommended_action,
            "validation": validation,
            "assumptions": assumptions,
            "raw_response": raw_response,
        }

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ai_analysis (
                    incident_id,
                    status,
                    root_cause,
                    confidence,
                    risk,
                    analysis
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (
                    incident_database_id,
                    "COMPLETED",
                    root_cause,
                    confidence,
                    risk,
                    json.dumps(
                        analysis_document,
                        default=str
                    ),
                ),
            )

            analysis_id = cursor.fetchone()[0]

        connection.commit()

        return analysis_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_latest_ai_analysis(
    incident_database_id
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    root_cause,
                    confidence,
                    risk,
                    analysis,
                    created_at
                FROM ai_analysis
                WHERE incident_id=%s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (
                    incident_database_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            analysis_document = row[5]

            if isinstance(
                analysis_document,
                str
            ):

                try:
                    analysis_document = json.loads(
                        analysis_document
                    )

                except json.JSONDecodeError:
                    analysis_document = {
                        "raw_analysis":
                            analysis_document
                    }

            if not isinstance(
                analysis_document,
                dict
            ):

                analysis_document = {}

            return {
                "id": row[0],
                "status": row[1],
                "root_cause": row[2],
                "confidence": row[3],
                "risk": row[4],
                "analysis": row[5],
                "created_at": row[6],
                "model":
                    analysis_document.get(
                        "model"
                    ),
                "evidence":
                    analysis_document.get(
                        "evidence",
                        []
                    ),
                "symptoms":
                    analysis_document.get(
                        "symptoms",
                        []
                    ),
                "customer_impact":
                    analysis_document.get(
                        "customer_impact"
                    ),
                "recommended_action":
                    analysis_document.get(
                        "recommended_action"
                    ),
                "validation":
                    analysis_document.get(
                        "validation"
                    ),
                "assumptions":
                    analysis_document.get(
                        "assumptions",
                        []
                    ),
                "raw_response":
                    analysis_document.get(
                        "raw_response"
                    ),
            }

    finally:
        connection.close()


def store_approval(
    incident_database_id,
    status,
    engineer,
    decision,
    notes=""
):
    """
    Persist an engineer approval decision.

    status:
        APPROVED
        REJECTED
        BLOCKED

    decision:
        APPROVE
        REJECT
        BLOCK

    This table is the system of record for
    engineer authorization.
    """

    connection = get_connection()

    try:
        approved_at = None

        if status == "APPROVED":
            approved_at = "NOW()"

        with connection.cursor() as cursor:

            if approved_at == "NOW()":

                cursor.execute(
                    """
                    INSERT INTO approvals (
                        incident_id,
                        status,
                        engineer,
                        decision,
                        notes,
                        approved_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        NOW()
                    )
                    RETURNING id
                    """,
                    (
                        incident_database_id,
                        status,
                        engineer,
                        decision,
                        notes,
                    ),
                )

            else:

                cursor.execute(
                    """
                    INSERT INTO approvals (
                        incident_id,
                        status,
                        engineer,
                        decision,
                        notes
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        incident_database_id,
                        status,
                        engineer,
                        decision,
                        notes,
                    ),
                )

            approval_id = cursor.fetchone()[0]

        connection.commit()

        return approval_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_latest_approval(
    incident_database_id
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    engineer,
                    decision,
                    notes,
                    approved_at
                FROM approvals
                WHERE incident_id=%s
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    incident_database_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "status": row[1],
                "engineer": row[2],
                "decision": row[3],
                "notes": row[4],
                "approved_at": row[5],
            }

    finally:
        connection.close()


def store_remediation(
    incident_database_id,
    status,
    plan=None
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO remediation (
                    incident_id,
                    status,
                    plan
                )
                VALUES (
                    %s,
                    %s,
                    %s::jsonb
                )
                RETURNING id
                """,
                (
                    incident_database_id,
                    status,
                    json.dumps(
                        plan or {},
                        default=str
                    ),
                ),
            )

            remediation_id = cursor.fetchone()[0]

        connection.commit()

        return remediation_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_latest_remediation(
    incident_database_id
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    plan,
                    executed_at
                FROM remediation
                WHERE incident_id=%s
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    incident_database_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "status": row[1],
                "plan": row[2],
                "executed_at": row[3],
            }

    finally:
        connection.close()


def store_validation(
    incident_database_id,
    status,
    result
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO validation (
                    incident_id,
                    status,
                    result
                )
                VALUES (
                    %s,
                    %s,
                    %s::jsonb
                )
                RETURNING id
                """,
                (
                    incident_database_id,
                    status,
                    json.dumps(
                        result or {},
                        default=str
                    ),
                ),
            )

            validation_id = cursor.fetchone()[0]

        connection.commit()

        return validation_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_latest_validation(
    incident_database_id
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    result,
                    validated_at
                FROM validation
                WHERE incident_id=%s
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    incident_database_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "status": row[1],
                "result": row[2],
                "validated_at": row[3],
            }

    finally:
        connection.close()


def store_audit_event(
    incident_database_id,
    event_type,
    actor,
    details
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_events (
                    incident_id,
                    event_type,
                    actor,
                    details
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s::jsonb
                )
                """,
                (
                    incident_database_id,
                    event_type,
                    actor,
                    json.dumps(
                        details,
                        default=str
                    ),
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_active_incidents():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    incident_id,
                    router,
                    incident_type,
                    status,
                    description,
                    impact,
                    health,
                    active_path,
                    default_next_hop,
                    created_at,
                    updated_at,
                    resolved_at
                FROM incidents
                WHERE status='ACTIVE'
                ORDER BY created_at ASC
                """
            )

            rows = cursor.fetchall()

            incidents = []

            for row in rows:

                incidents.append(
                    {
                        "database_id": row[0],
                        "incident_id": row[1],
                        "router": row[2],
                        "incident_type": row[3],
                        "status": row[4],
                        "description": row[5],
                        "impact": row[6],
                        "health": row[7],
                        "active_path": row[8],
                        "default_next_hop": row[9],
                        "created_at": row[10],
                        "updated_at": row[11],
                        "resolved_at": row[12],
                    }
                )

            return incidents

    finally:
        connection.close()


def get_incident_history(
    limit=50
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    incident_id,
                    router,
                    incident_type,
                    status,
                    description,
                    impact,
                    health,
                    active_path,
                    default_next_hop,
                    created_at,
                    updated_at,
                    resolved_at
                FROM incidents
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (
                    limit,
                ),
            )

            rows = cursor.fetchall()

            incidents = []

            for row in rows:

                incidents.append(
                    {
                        "database_id": row[0],
                        "incident_id": row[1],
                        "router": row[2],
                        "incident_type": row[3],
                        "status": row[4],
                        "description": row[5],
                        "impact": row[6],
                        "health": row[7],
                        "active_path": row[8],
                        "default_next_hop": row[9],
                        "created_at": row[10],
                        "updated_at": row[11],
                        "resolved_at": row[12],
                    }
                )

            return incidents

    finally:
        connection.close()