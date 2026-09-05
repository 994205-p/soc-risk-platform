"""
Data ingestion pipeline: loads generated CSVs (data/processed/*.csv) into the
database, running validation as it goes. Invalid values are NOT silently
accepted -- they are flagged into data_quality_events and clamped/nulled so
they cannot crash downstream calculations (per project requirement: "Do not
allow these problems to crash the application").
"""
import csv
import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (Asset, Control, ControlTelemetry, Vulnerability,
                                Incident, Remediation, LegacyCase, DataQualityEvent, Role, User)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed")


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _parse_date(s):
    dt = _parse_dt(s)
    return dt.date() if dt else None


def _parse_bool(s):
    return str(s).strip().lower() in ("true", "1", "yes")


def _clamp_pct(value, record_id, table, db_events):
    """Percentages must be within [0, 100]. Anything else is flagged and clamped."""
    if value in (None, ""):
        db_events.append(DataQualityEvent(source_table=table, record_id=record_id,
                                           issue_type="MISSING", detail="percentage value missing",
                                           detected_at=datetime.utcnow(), severity="MEDIUM"))
        return None
    try:
        v = float(value)
    except (ValueError, TypeError):
        db_events.append(DataQualityEvent(source_table=table, record_id=record_id,
                                           issue_type="INVALID", detail=f"non-numeric percentage: {value}",
                                           detected_at=datetime.utcnow(), severity="HIGH"))
        return None
    if v < 0 or v > 100:
        db_events.append(DataQualityEvent(source_table=table, record_id=record_id,
                                           issue_type="INVALID", detail=f"percentage out of range: {v}",
                                           detected_at=datetime.utcnow(), severity="HIGH"))
        return max(0.0, min(100.0, v))
    return v


def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ingest_all(db: Session) -> dict:
    events: list[DataQualityEvent] = []
    summary = {}

    # --- roles / demo users -------------------------------------------------
    if db.query(Role).count() == 0:
        roles = [Role(role_name=r) for r in ("management", "soc_analyst", "security_engineer")]
        db.add_all(roles)
        db.commit()

    # --- assets ---------------------------------------------------------
    seen_asset_ids = set()
    assets_loaded = 0
    for row in load_csv("assets.csv"):
        aid = row["asset_id"]
        if aid in seen_asset_ids:
            events.append(DataQualityEvent(source_table="assets", record_id=aid, issue_type="DUPLICATE",
                                            detail="duplicate asset_id in source file",
                                            detected_at=datetime.utcnow(), severity="MEDIUM"))
            continue
        seen_asset_ids.add(aid)
        db.merge(Asset(
            asset_id=aid, asset_name=row.get("asset_name"), asset_type=row.get("asset_type"),
            business_unit=row.get("business_unit"), environment=row.get("environment"),
            owner=row.get("owner"), criticality=row.get("criticality") or "LOW",
            criticality_score=float(row["criticality_score"]) if row.get("criticality_score") else None,
            internet_exposed=_parse_bool(row.get("internet_exposed")),
            operating_system=row.get("operating_system"), last_seen=_parse_dt(row.get("last_seen")),
        ))
        assets_loaded += 1
    summary["assets"] = assets_loaded

    # --- controls ---------------------------------------------------------
    controls_loaded = 0
    for row in load_csv("controls.csv"):
        db.merge(Control(
            control_id=row["control_id"], control_name=row.get("control_name"),
            control_type=row.get("control_type"), description=row.get("description"),
            target_coverage=float(row["target_coverage"]) if row.get("target_coverage") else 95.0,
            actual_coverage=float(row["actual_coverage"]) if row.get("actual_coverage") else None,
            status=row.get("status"), implementation_date=_parse_date(row.get("implementation_date")),
            owner=row.get("owner"),
        ))
        controls_loaded += 1
    summary["controls"] = controls_loaded

    # --- control telemetry (validated) -------------------------------------
    tel_loaded = 0
    seen_tel_ids = set()
    for row in load_csv("control_telemetry.csv"):
        tid = row["telemetry_id"]
        if tid in seen_tel_ids:
            continue
        seen_tel_ids.add(tid)
        coverage = _clamp_pct(row.get("coverage_percentage"), tid, "control_telemetry", events)
        compliance = _clamp_pct(row.get("compliance_percentage"), tid, "control_telemetry", events)
        ts = _parse_dt(row.get("timestamp"))
        freshness = _parse_dt(row.get("freshness_timestamp")) or ts
        if freshness and (datetime.utcnow() - freshness) > timedelta(days=7):
            events.append(DataQualityEvent(source_table="control_telemetry", record_id=tid, issue_type="STALE",
                                            detail=f"freshness_timestamp older than 7 days ({freshness})",
                                            detected_at=datetime.utcnow(), severity="MEDIUM"))
        db.merge(ControlTelemetry(
            telemetry_id=tid, control_id=row.get("control_id"), asset_id=row.get("asset_id"),
            timestamp=ts, coverage_percentage=coverage, compliance_percentage=compliance,
            health_status=row.get("health_status"), event_count=int(row["event_count"]) if row.get("event_count") else 0,
            source=row.get("source"), data_quality=row.get("data_quality"), freshness_timestamp=freshness,
            period=row.get("period"),
        ))
        tel_loaded += 1
    summary["control_telemetry"] = tel_loaded

    # --- vulnerabilities -----------------------------------------------
    vuln_loaded = 0
    for row in load_csv("vulnerabilities.csv"):
        vid = row["vulnerability_id"]
        cvss = row.get("cvss_score")
        try:
            cvss_val = float(cvss) if cvss not in (None, "") else None
            if cvss_val is not None and (cvss_val < 0 or cvss_val > 10):
                events.append(DataQualityEvent(source_table="vulnerabilities", record_id=vid, issue_type="INVALID",
                                                detail=f"cvss_score out of range: {cvss_val}",
                                                detected_at=datetime.utcnow(), severity="HIGH"))
                cvss_val = max(0.0, min(10.0, cvss_val))
        except ValueError:
            cvss_val = None
        if not row.get("asset_id"):
            events.append(DataQualityEvent(source_table="vulnerabilities", record_id=vid, issue_type="MISSING",
                                            detail="missing asset_id reference",
                                            detected_at=datetime.utcnow(), severity="HIGH"))
            continue
        db.merge(Vulnerability(
            vulnerability_id=vid, asset_id=row.get("asset_id"), cve_id=row.get("cve_id"),
            severity=row.get("severity") or "LOW", cvss_score=cvss_val,
            discovered_date=_parse_date(row.get("discovered_date")), due_date=_parse_date(row.get("due_date")),
            remediation_status=row.get("remediation_status") or "OPEN",
            remediation_date=_parse_date(row.get("remediation_date")),
            exploit_available=_parse_bool(row.get("exploit_available")),
            internet_exposed=_parse_bool(row.get("internet_exposed")),
            business_impact=row.get("business_impact"),
        ))
        vuln_loaded += 1
    summary["vulnerabilities"] = vuln_loaded

    # --- incidents (with duplicate detection) -------------------------------
    inc_loaded = 0
    seen_inc_ids = set()
    for row in load_csv("incidents.csv"):
        iid = row["incident_id"]
        if iid in seen_inc_ids:
            events.append(DataQualityEvent(source_table="incidents", record_id=iid, issue_type="DUPLICATE",
                                            detail="duplicate incident_id in source file",
                                            detected_at=datetime.utcnow(), severity="LOW"))
            continue
        seen_inc_ids.add(iid)
        db.merge(Incident(
            incident_id=iid, asset_id=row.get("asset_id"), incident_type=row.get("incident_type"),
            severity=row.get("severity") or "LOW", detected_at=_parse_dt(row.get("detected_at")),
            resolved_at=_parse_dt(row.get("resolved_at")), status=row.get("status") or "OPEN",
            root_cause=row.get("root_cause"), control_related=row.get("control_related") or None,
            business_impact=row.get("business_impact"),
            financial_impact_estimate=float(row["financial_impact_estimate"]) if row.get("financial_impact_estimate") else 0.0,
            period=row.get("period"),
        ))
        inc_loaded += 1
    summary["incidents"] = inc_loaded

    # --- remediation ---------------------------------------------------
    rem_loaded = 0
    for row in load_csv("remediation.csv"):
        db.merge(Remediation(
            remediation_id=row["remediation_id"], vulnerability_id=row.get("vulnerability_id"),
            asset_id=row.get("asset_id"), assigned_to=row.get("assigned_to"),
            assigned_date=_parse_date(row.get("assigned_date")), due_date=_parse_date(row.get("due_date")),
            completed_date=_parse_date(row.get("completed_date")), status=row.get("status"),
            verification_status=row.get("verification_status"),
        ))
        rem_loaded += 1
    summary["remediation"] = rem_loaded

    # --- legacy cases ----------------------------------------------------
    leg_loaded = 0
    for row in load_csv("legacy_cases.csv"):
        migrated = _parse_bool(row.get("migrated"))
        db.merge(LegacyCase(
            legacy_case_id=row["legacy_case_id"], alert_id=row.get("alert_id"),
            created_at=_parse_dt(row.get("created_at")), severity=row.get("severity"),
            analyst=row.get("analyst"), status=row.get("status"), resolution=row.get("resolution"),
            migrated=migrated, migration_timestamp=_parse_dt(row.get("migration_timestamp")),
            migration_status="MIGRATED" if migrated else "NOT_MIGRATED",
        ))
        leg_loaded += 1
    summary["legacy_cases"] = leg_loaded

    if events:
        db.add_all(events)
    db.commit()
    summary["data_quality_events_logged"] = len(events)
    return summary
