-- ============================================================
-- NETPILOT DATABASE SCHEMA
-- ============================================================
-- Defines the current NetPilot PostgreSQL database.
-- This schema represents the current working NetPilot data model.
-- It is intended for initializing a fresh NetPilot database.


-- ============================================================
-- INCIDENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS incidents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id VARCHAR(32) NOT NULL UNIQUE,
    router VARCHAR(32) NOT NULL,
    incident_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    description TEXT,
    impact TEXT,
    health VARCHAR(32),
    active_path VARCHAR(32),
    default_next_hop VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    source_type VARCHAR(64),
    source_id BIGINT
);


-- ============================================================
-- INCIDENT EVIDENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS incident_evidence (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    evidence_type VARCHAR(64) NOT NULL,
    evidence JSONB NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_incident_evidence_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE CASCADE
);


-- ============================================================
-- AI INCIDENT ANALYSIS
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_analysis (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    root_cause TEXT,
    confidence VARCHAR(32),
    risk VARCHAR(32),
    analysis TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ai_analysis_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE CASCADE
);


-- ============================================================
-- ENGINEER APPROVALS
-- ============================================================

CREATE TABLE IF NOT EXISTS approvals (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    engineer VARCHAR(128),
    decision VARCHAR(32),
    notes TEXT,
    approved_at TIMESTAMPTZ,

    CONSTRAINT fk_approval_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE CASCADE
);


-- ============================================================
-- REMEDIATION
-- ============================================================

CREATE TABLE IF NOT EXISTS remediation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    plan JSONB,
    executed_at TIMESTAMPTZ,

    CONSTRAINT fk_remediation_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE CASCADE
);


-- ============================================================
-- VALIDATION
-- ============================================================

CREATE TABLE IF NOT EXISTS validation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    result JSONB,
    validated_at TIMESTAMPTZ,

    CONSTRAINT fk_validation_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE CASCADE
);


-- ============================================================
-- AUDIT EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id BIGINT,
    event_type VARCHAR(64) NOT NULL,
    actor VARCHAR(128),
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE SET NULL
);


-- ============================================================
-- INTERFACE TELEMETRY
-- ============================================================

CREATE TABLE IF NOT EXISTS interface_telemetry (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    router VARCHAR(32) NOT NULL,
    interface_name VARCHAR(128) NOT NULL,
    interface_status VARCHAR(32),
    protocol_status VARCHAR(32),
    input_rate_bps BIGINT,
    output_rate_bps BIGINT,
    input_packets BIGINT,
    output_packets BIGINT,
    input_errors BIGINT,
    output_errors BIGINT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- INTERFACE CAPACITY
-- ============================================================

CREATE TABLE IF NOT EXISTS interface_capacity (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    router VARCHAR(32) NOT NULL,
    interface_name VARCHAR(128) NOT NULL,
    bandwidth_bps BIGINT NOT NULL,
    source VARCHAR(64) NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT interface_capacity_router_interface_name_key
        UNIQUE (router, interface_name)
);


-- ============================================================
-- TELEMETRY ANOMALIES
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry_anomalies (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    router VARCHAR(32) NOT NULL,
    interface_name VARCHAR(128) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    anomaly_type VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    first_detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    resolved_at TIMESTAMPTZ
);


-- ============================================================
-- TELEMETRY CORRELATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry_correlations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    router VARCHAR(32) NOT NULL,
    interface_name VARCHAR(128) NOT NULL,
    correlation_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    summary TEXT NOT NULL,
    source_anomaly_ids JSONB NOT NULL,
    first_detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    resolved_at TIMESTAMPTZ
);


-- ============================================================
-- TELEMETRY AI ANALYSIS
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry_ai_analysis (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    correlation_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    assessment TEXT,
    likely_explanation TEXT,
    customer_impact TEXT,
    risk VARCHAR(32),
    confidence VARCHAR(32),
    observed_evidence JSONB,
    recommended_investigation JSONB,
    assumptions JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_telemetry_ai_correlation
        FOREIGN KEY (correlation_id)
        REFERENCES telemetry_correlations(id)
        ON DELETE CASCADE
);


-- ============================================================
-- WORKFLOW RUNS
-- ============================================================

CREATE TABLE IF NOT EXISTS workflow_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL UNIQUE,
    workflow_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    duration_ms BIGINT,
    stages_completed INTEGER NOT NULL DEFAULT 0,
    stages_failed INTEGER NOT NULL DEFAULT 0,
    summary JSONB,
    error TEXT
);


-- ============================================================
-- INCIDENT INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_incidents_router
    ON incidents(router);

CREATE INDEX IF NOT EXISTS idx_incidents_status
    ON incidents(status);

CREATE INDEX IF NOT EXISTS idx_incidents_created_at
    ON incidents(created_at);

CREATE INDEX IF NOT EXISTS idx_incidents_source
    ON incidents(source_type, source_id);


-- ============================================================
-- INCIDENT CHILD-TABLE INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_evidence_incident
    ON incident_evidence(incident_id);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_incident
    ON ai_analysis(incident_id);

CREATE INDEX IF NOT EXISTS idx_approval_incident
    ON approvals(incident_id);

CREATE INDEX IF NOT EXISTS idx_remediation_incident
    ON remediation(incident_id);

CREATE INDEX IF NOT EXISTS idx_validation_incident
    ON validation(incident_id);

CREATE INDEX IF NOT EXISTS idx_audit_incident
    ON audit_events(incident_id);

CREATE INDEX IF NOT EXISTS idx_audit_created_at
    ON audit_events(created_at);


-- ============================================================
-- INTERFACE CAPACITY INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_interface_capacity_router
    ON interface_capacity(router);

CREATE INDEX IF NOT EXISTS idx_interface_capacity_interface
    ON interface_capacity(interface_name);


-- ============================================================
-- INTERFACE TELEMETRY INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_interface_telemetry_router
    ON interface_telemetry(router);

CREATE INDEX IF NOT EXISTS idx_interface_telemetry_interface
    ON interface_telemetry(interface_name);

CREATE INDEX IF NOT EXISTS idx_interface_telemetry_collected_at
    ON interface_telemetry(collected_at);


-- ============================================================
-- TELEMETRY ANOMALY INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_telemetry_anomalies_router
    ON telemetry_anomalies(router);

CREATE INDEX IF NOT EXISTS idx_telemetry_anomalies_interface
    ON telemetry_anomalies(interface_name);

CREATE INDEX IF NOT EXISTS idx_telemetry_anomalies_detected_at
    ON telemetry_anomalies(detected_at);

CREATE INDEX IF NOT EXISTS idx_telemetry_anomalies_status
    ON telemetry_anomalies(status);

CREATE INDEX IF NOT EXISTS idx_telemetry_anomalies_active
    ON telemetry_anomalies(
        router,
        interface_name,
        anomaly_type,
        status
    );


-- ============================================================
-- TELEMETRY CORRELATION INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_telemetry_correlations_router
    ON telemetry_correlations(router);

CREATE INDEX IF NOT EXISTS idx_telemetry_correlations_interface
    ON telemetry_correlations(interface_name);

CREATE INDEX IF NOT EXISTS idx_telemetry_correlations_detected_at
    ON telemetry_correlations(last_detected_at);

CREATE INDEX IF NOT EXISTS idx_telemetry_correlations_status
    ON telemetry_correlations(status);


-- ============================================================
-- TELEMETRY AI INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_telemetry_ai_correlation
    ON telemetry_ai_analysis(correlation_id);

CREATE INDEX IF NOT EXISTS idx_telemetry_ai_created_at
    ON telemetry_ai_analysis(created_at);

CREATE INDEX IF NOT EXISTS idx_telemetry_ai_status
    ON telemetry_ai_analysis(status);


-- ============================================================
-- WORKFLOW INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_workflow_runs_started_at
    ON workflow_runs(started_at);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_status
    ON workflow_runs(status);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow
    ON workflow_runs(workflow_name);