from sqlalchemy import (Column, Integer, String, Float, Boolean, DateTime, Date,
                         ForeignKey, Text, Numeric)
from sqlalchemy.orm import relationship

from app.database import Base


class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(150), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = relationship("Role")


class Asset(Base):
    __tablename__ = "assets"
    asset_id = Column(String(30), primary_key=True)
    asset_name = Column(String(150))
    asset_type = Column(String(50))
    business_unit = Column(String(100))
    environment = Column(String(30))
    owner = Column(String(100))
    criticality = Column(String(20))
    criticality_score = Column(Float)
    internet_exposed = Column(Boolean, default=False)
    operating_system = Column(String(100))
    last_seen = Column(DateTime)


class Control(Base):
    __tablename__ = "controls"
    control_id = Column(String(30), primary_key=True)
    control_name = Column(String(150))
    control_type = Column(String(50))
    description = Column(Text)
    target_coverage = Column(Float)
    actual_coverage = Column(Float)
    status = Column(String(30))
    implementation_date = Column(Date)
    owner = Column(String(100))


class ControlTelemetry(Base):
    __tablename__ = "control_telemetry"
    telemetry_id = Column(String(40), primary_key=True)
    control_id = Column(String(30), ForeignKey("controls.control_id"))
    asset_id = Column(String(30), ForeignKey("assets.asset_id"))
    timestamp = Column(DateTime)
    coverage_percentage = Column(Float)
    compliance_percentage = Column(Float)
    health_status = Column(String(30))
    event_count = Column(Integer)
    source = Column(String(50))
    data_quality = Column(String(30))
    freshness_timestamp = Column(DateTime)
    period = Column(String(20))  # BASELINE / CURRENT (assumption: added for experiment tracking)


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    vulnerability_id = Column(String(40), primary_key=True)
    asset_id = Column(String(30), ForeignKey("assets.asset_id"))
    cve_id = Column(String(30))
    severity = Column(String(20))
    cvss_score = Column(Float)
    discovered_date = Column(Date)
    due_date = Column(Date)
    remediation_status = Column(String(30))
    remediation_date = Column(Date, nullable=True)
    exploit_available = Column(Boolean, default=False)
    internet_exposed = Column(Boolean, default=False)
    business_impact = Column(String(20))


class Incident(Base):
    __tablename__ = "incidents"
    incident_id = Column(String(40), primary_key=True)
    asset_id = Column(String(30), ForeignKey("assets.asset_id"))
    incident_type = Column(String(60))
    severity = Column(String(20))
    detected_at = Column(DateTime)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String(30))
    root_cause = Column(Text)
    control_related = Column(String(30), ForeignKey("controls.control_id"), nullable=True)
    business_impact = Column(String(20))
    financial_impact_estimate = Column(Float)
    period = Column(String(20))


class Remediation(Base):
    __tablename__ = "remediation"
    remediation_id = Column(String(40), primary_key=True)
    vulnerability_id = Column(String(40), ForeignKey("vulnerabilities.vulnerability_id"))
    asset_id = Column(String(30), ForeignKey("assets.asset_id"))
    assigned_to = Column(String(100))
    assigned_date = Column(Date)
    due_date = Column(Date)
    completed_date = Column(Date, nullable=True)
    status = Column(String(30))
    verification_status = Column(String(30))


class LegacyCase(Base):
    __tablename__ = "legacy_cases"
    legacy_case_id = Column(String(40), primary_key=True)
    alert_id = Column(String(40))
    created_at = Column(DateTime)
    severity = Column(String(20))
    analyst = Column(String(100))
    status = Column(String(30))
    resolution = Column(Text)
    migrated = Column(Boolean, default=False)
    migration_timestamp = Column(DateTime, nullable=True)
    # migration_status: NOT_MIGRATED / MIGRATED / VERIFIED / ROLLED_BACK
    migration_status = Column(String(20), default="NOT_MIGRATED")


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    scope_type = Column(String(30))
    scope_id = Column(String(60))
    snapshot_time = Column(DateTime)
    period_label = Column(String(30))
    risk_score = Column(Float)
    risk_band = Column(String(20))
    vulnerability_component = Column(Float)
    incident_component = Column(Float)
    control_gap_component = Column(Float)
    asset_criticality_component = Column(Float)
    confidence = Column(Float)
    data_status = Column(String(20))
    explanation = Column(Text)


class ControlEffectiveness(Base):
    __tablename__ = "control_effectiveness"
    effectiveness_id = Column(Integer, primary_key=True, autoincrement=True)
    control_id = Column(String(30), ForeignKey("controls.control_id"))
    period_start = Column(Date)
    period_end = Column(Date)
    target_coverage = Column(Float)
    actual_coverage = Column(Float)
    compliance = Column(Float)
    affected_assets = Column(Integer)
    incidents_before = Column(Integer)
    incidents_after = Column(Integer)
    vulnerabilities_before = Column(Integer)
    vulnerabilities_after = Column(Integer)
    risk_before = Column(Float)
    risk_after = Column(Float)
    risk_reduction_pct = Column(Float)
    effectiveness_score = Column(Float)
    confidence = Column(Float)


class DataQualityEvent(Base):
    __tablename__ = "data_quality_events"
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    source_table = Column(String(60))
    record_id = Column(String(60))
    issue_type = Column(String(50))
    detail = Column(Text)
    detected_at = Column(DateTime)
    severity = Column(String(20))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(100))
    action = Column(String(100))
    entity = Column(String(60))
    entity_id = Column(String(60))
    previous_state = Column(String(60))
    new_state = Column(String(60))
    timestamp = Column(DateTime)
    detail = Column(Text)
