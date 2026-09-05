-- SOC Control Effectiveness & Business Risk Platform
-- PostgreSQL normalized schema

CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL  -- management | soc_analyst | security_engineer
);

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(role_id),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id VARCHAR(30) PRIMARY KEY,
    asset_name VARCHAR(150) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    business_unit VARCHAR(100),
    environment VARCHAR(30),
    owner VARCHAR(100),
    criticality VARCHAR(20) NOT NULL,       -- LOW/MEDIUM/HIGH/CRITICAL
    criticality_score NUMERIC(5,2),
    internet_exposed BOOLEAN DEFAULT false,
    operating_system VARCHAR(100),
    last_seen TIMESTAMP
);

CREATE TABLE IF NOT EXISTS controls (
    control_id VARCHAR(30) PRIMARY KEY,
    control_name VARCHAR(150) NOT NULL,
    control_type VARCHAR(50),
    description TEXT,
    target_coverage NUMERIC(5,2),
    actual_coverage NUMERIC(5,2),
    status VARCHAR(30),
    implementation_date DATE,
    owner VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS control_telemetry (
    telemetry_id VARCHAR(40) PRIMARY KEY,
    control_id VARCHAR(30) REFERENCES controls(control_id),
    asset_id VARCHAR(30) REFERENCES assets(asset_id),
    timestamp TIMESTAMP,
    coverage_percentage NUMERIC(6,2),
    compliance_percentage NUMERIC(6,2),
    health_status VARCHAR(30),
    event_count INTEGER,
    source VARCHAR(50),
    data_quality VARCHAR(30),               -- GOOD/DEGRADED/BAD
    freshness_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vulnerabilities (
    vulnerability_id VARCHAR(40) PRIMARY KEY,
    asset_id VARCHAR(30) REFERENCES assets(asset_id),
    cve_id VARCHAR(30),
    severity VARCHAR(20),
    cvss_score NUMERIC(4,1),
    discovered_date DATE,
    due_date DATE,
    remediation_status VARCHAR(30),
    remediation_date DATE,
    exploit_available BOOLEAN DEFAULT false,
    internet_exposed BOOLEAN DEFAULT false,
    business_impact VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id VARCHAR(40) PRIMARY KEY,
    asset_id VARCHAR(30) REFERENCES assets(asset_id),
    incident_type VARCHAR(60),
    severity VARCHAR(20),
    detected_at TIMESTAMP,
    resolved_at TIMESTAMP,
    status VARCHAR(30),
    root_cause TEXT,
    control_related VARCHAR(30) REFERENCES controls(control_id),
    business_impact VARCHAR(20),
    financial_impact_estimate NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS remediation (
    remediation_id VARCHAR(40) PRIMARY KEY,
    vulnerability_id VARCHAR(40) REFERENCES vulnerabilities(vulnerability_id),
    asset_id VARCHAR(30) REFERENCES assets(asset_id),
    assigned_to VARCHAR(100),
    assigned_date DATE,
    due_date DATE,
    completed_date DATE,
    status VARCHAR(30),
    verification_status VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS legacy_cases (
    legacy_case_id VARCHAR(40) PRIMARY KEY,
    alert_id VARCHAR(40),
    created_at TIMESTAMP,
    severity VARCHAR(20),
    analyst VARCHAR(100),
    status VARCHAR(30),
    resolution TEXT,
    migrated BOOLEAN DEFAULT false,
    migration_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    scope_type VARCHAR(30) NOT NULL,        -- ORG / BUSINESS_UNIT / ASSET
    scope_id VARCHAR(60) NOT NULL,
    snapshot_time TIMESTAMP DEFAULT now(),
    period_label VARCHAR(30),               -- BASELINE / CURRENT / POST_CONTROL
    risk_score NUMERIC(5,2),
    risk_band VARCHAR(20),
    vulnerability_component NUMERIC(6,2),
    incident_component NUMERIC(6,2),
    control_gap_component NUMERIC(6,2),
    asset_criticality_component NUMERIC(6,2),
    confidence NUMERIC(5,2),
    data_status VARCHAR(20),                -- FRESH/AGING/STALE/MISSING/FALLBACK
    explanation TEXT
);

CREATE TABLE IF NOT EXISTS control_effectiveness (
    effectiveness_id SERIAL PRIMARY KEY,
    control_id VARCHAR(30) REFERENCES controls(control_id),
    period_start DATE,
    period_end DATE,
    target_coverage NUMERIC(5,2),
    actual_coverage NUMERIC(5,2),
    compliance NUMERIC(5,2),
    affected_assets INTEGER,
    incidents_before INTEGER,
    incidents_after INTEGER,
    vulnerabilities_before INTEGER,
    vulnerabilities_after INTEGER,
    risk_before NUMERIC(5,2),
    risk_after NUMERIC(5,2),
    risk_reduction_pct NUMERIC(5,2),
    effectiveness_score NUMERIC(5,2),
    confidence NUMERIC(5,2)
);

CREATE TABLE IF NOT EXISTS data_quality_events (
    event_id SERIAL PRIMARY KEY,
    source_table VARCHAR(60),
    record_id VARCHAR(60),
    issue_type VARCHAR(50),                 -- MISSING/STALE/INVALID/DUPLICATE/INCONSISTENT
    detail TEXT,
    detected_at TIMESTAMP DEFAULT now(),
    severity VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id SERIAL PRIMARY KEY,
    actor VARCHAR(100),
    action VARCHAR(100),
    entity VARCHAR(60),
    entity_id VARCHAR(60),
    previous_state VARCHAR(60),
    new_state VARCHAR(60),
    timestamp TIMESTAMP DEFAULT now(),
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_vuln_asset ON vulnerabilities(asset_id);
CREATE INDEX IF NOT EXISTS idx_incident_asset ON incidents(asset_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_control ON control_telemetry(control_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_asset ON control_telemetry(asset_id);
CREATE INDEX IF NOT EXISTS idx_remediation_vuln ON remediation(vulnerability_id);
