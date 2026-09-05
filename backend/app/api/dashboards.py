from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Asset, Vulnerability, Incident, Control
from app.services.risk_service import compute_org_risk, get_risk_trend
from app.services.control_effectiveness import compute_all_controls_effectiveness
from app.services.legacy_service import get_status as legacy_status
from app.utils.auth import require_role

router = APIRouter(prefix="/api/dashboard", tags=["dashboards"])

# Organisation-wide target risk reduction used as the experiment's goal.
# Documented assumption (see docs/risk_methodology.md): mirrors the worked
# example in the original brief (20% target reduction).
TARGET_REDUCTION_PCT = 20.0


@router.get("/management")
def management_dashboard(db: Session = Depends(get_db), _user=Depends(require_role("management"))):
    risk = compute_org_risk(db)
    trend = get_risk_trend(db, limit=20)
    effectiveness = compute_all_controls_effectiveness(db)

    open_incidents = db.query(Incident).filter(Incident.status != "RESOLVED", Incident.period == "CURRENT").count()
    critical_vulns = db.query(Vulnerability).filter(
        Vulnerability.severity == "CRITICAL",
        Vulnerability.remediation_status.in_(["OPEN", "IN_PROGRESS"])).count()

    # top business risk = business units ranked by count of critical assets w/ open critical vulns
    assets = db.query(Asset).all()
    bu_risk = {}
    crit_asset_ids = {v.asset_id for v in db.query(Vulnerability).filter(
        Vulnerability.severity.in_(["HIGH", "CRITICAL"]),
        Vulnerability.remediation_status.in_(["OPEN", "IN_PROGRESS"])).all()}
    for a in assets:
        if a.asset_id in crit_asset_ids:
            bu_risk[a.business_unit] = bu_risk.get(a.business_unit, 0) + 1
    top_risks = sorted(bu_risk.items(), key=lambda x: x[1], reverse=True)[:5]

    avg_effectiveness = round(sum(e.get("effectiveness_score", 0) for e in effectiveness) / len(effectiveness), 1) \
        if effectiveness else 0.0
    avg_reduction = round(sum(e.get("risk_reduction_pct", 0) for e in effectiveness) / len(effectiveness), 1) \
        if effectiveness else 0.0

    # Baseline / target / measured result, derived from the actual control
    # effectiveness computations -- never hardcoded (per spec section 6).
    baseline_scores = [e["risk_before"] for e in effectiveness if e.get("risk_before") is not None]
    measured_scores = [e["risk_after"] for e in effectiveness if e.get("risk_after") is not None]
    baseline_risk = round(sum(baseline_scores) / len(baseline_scores), 1) if baseline_scores else None
    measured_risk = round(sum(measured_scores) / len(measured_scores), 1) if measured_scores else None
    target_achieved = avg_reduction >= TARGET_REDUCTION_PCT if effectiveness else None
    overall_confidence = round(sum(e.get("confidence", 0) for e in effectiveness) / len(effectiveness), 1) \
        if effectiveness else 0.0

    return {
        "current_risk": risk,
        "risk_trend": trend,
        "experiment_summary": {
            "baseline_risk": baseline_risk,
            "target_reduction_pct": TARGET_REDUCTION_PCT,
            "measured_risk": measured_risk,
            "measured_reduction_pct": avg_reduction,
            "target_achieved": target_achieved,
            "confidence": overall_confidence,
        },
        "kpis": {
            "current_risk_score": risk["risk_score"],
            "avg_risk_reduction_pct": avg_reduction,
            "critical_vulnerabilities": critical_vulns,
            "open_incidents": open_incidents,
            "avg_control_effectiveness": avg_effectiveness,
            "total_assets": len(assets),
        },
        "control_effectiveness_summary": [{
            "control_id": e["control_id"], "control_name": e.get("control_name"),
            "coverage": e.get("actual_coverage"), "effectiveness_score": e.get("effectiveness_score"),
            "risk_reduction_pct": e.get("risk_reduction_pct"), "status": e.get("status"),
            "attribution_confidence": e.get("attribution_confidence"),
        } for e in effectiveness],
        "top_business_risks": [{"business_unit": bu, "high_risk_asset_count": count} for bu, count in top_risks],
    }


@router.get("/soc")
def soc_dashboard(db: Session = Depends(get_db), _user=Depends(require_role("soc_analyst", "management"))):
    from app.models.models import Remediation, ControlTelemetry, Asset
    from app.risk_engine.engine import freshness_status
    from datetime import datetime

    open_incidents = db.query(Incident).filter(Incident.status != "RESOLVED").order_by(
        Incident.detected_at.desc()).limit(50).all()
    open_vulns = db.query(Vulnerability).filter(
        Vulnerability.remediation_status.in_(["OPEN", "IN_PROGRESS"])).order_by(
        Vulnerability.cvss_score.desc()).limit(50).all()

    asset_by_id = {a.asset_id: a for a in db.query(Asset).all()}
    critical_incidents = [i for i in open_incidents if i.severity == "CRITICAL"]
    critical_assets = [a for a in asset_by_id.values() if a.criticality == "CRITICAL"]

    remediation_backlog = db.query(Remediation).filter(Remediation.status != "COMPLETE").count()

    now = datetime.utcnow()
    current_tel = db.query(ControlTelemetry).filter(ControlTelemetry.period == "CURRENT").all()
    stale_telemetry_count = sum(
        1 for t in current_tel if freshness_status(t.freshness_timestamp, now) in ("STALE", "MISSING", "INVALID")
    )
    control_failures = sum(1 for t in current_tel if t.health_status == "FAILED")

    return {
        "active_incidents": [{
            "incident_id": i.incident_id, "asset_id": i.asset_id, "incident_type": i.incident_type,
            "severity": i.severity, "detected_at": i.detected_at.isoformat() if i.detected_at else None,
            "status": i.status, "control_related": i.control_related,
            "asset_criticality": asset_by_id[i.asset_id].criticality if i.asset_id in asset_by_id else None,
        } for i in open_incidents],
        "open_vulnerabilities": [{
            "vulnerability_id": v.vulnerability_id, "asset_id": v.asset_id, "severity": v.severity,
            "cvss_score": v.cvss_score, "exploit_available": v.exploit_available,
            "internet_exposed": v.internet_exposed, "remediation_status": v.remediation_status,
        } for v in open_vulns],
        "critical_assets": [{
            "asset_id": a.asset_id, "asset_name": a.asset_name, "business_unit": a.business_unit,
            "internet_exposed": a.internet_exposed,
        } for a in critical_assets[:20]],
        "counts": {
            "open_incidents": len(open_incidents),
            "critical_incidents": len(critical_incidents),
            "critical_assets": len(critical_assets),
            "remediation_backlog": remediation_backlog,
            "stale_telemetry_sources": stale_telemetry_count,
            "control_failures": control_failures,
            "open_vulnerabilities": db.query(Vulnerability).filter(
                Vulnerability.remediation_status.in_(["OPEN", "IN_PROGRESS"])).count(),
        },
    }


@router.get("/engineering")
def engineering_dashboard(db: Session = Depends(get_db),
                           _user=Depends(require_role("security_engineer", "management"))):
    effectiveness = compute_all_controls_effectiveness(db)
    controls = db.query(Control).all()

    from app.models.models import ControlTelemetry, Vulnerability, Remediation
    from app.risk_engine.engine import freshness_status
    from datetime import datetime

    now = datetime.utcnow()
    current_tel = db.query(ControlTelemetry).filter(ControlTelemetry.period == "CURRENT").all()
    freshness_counts = {"FRESH": 0, "AGING": 0, "STALE": 0, "MISSING": 0, "INVALID": 0}
    for t in current_tel:
        freshness_counts[freshness_status(t.freshness_timestamp, now)] += 1

    total_vulns = db.query(Vulnerability).count()
    open_vulns = db.query(Vulnerability).filter(
        Vulnerability.remediation_status.in_(["OPEN", "IN_PROGRESS", "ACCEPTED_RISK"])).count()
    patch_compliance_pct = round(100 * (total_vulns - open_vulns) / total_vulns, 1) if total_vulns else None

    remediation_pending = db.query(Remediation).filter(Remediation.status != "COMPLETE").count()

    return {
        "controls": [{
            "control_id": c.control_id, "control_name": c.control_name,
            "target_coverage": c.target_coverage, "actual_coverage": c.actual_coverage,
            "status": c.status,
        } for c in controls],
        "effectiveness": effectiveness,
        "failed_controls": [e for e in effectiveness if (e.get("actual_coverage") or 0) < (e.get("target_coverage") or 100) - 15],
        "telemetry_freshness": freshness_counts,
        "patch_compliance_pct": patch_compliance_pct,
        "remediation_pending": remediation_pending,
    }


@router.get("/legacy-summary")
def legacy_summary(db: Session = Depends(get_db),
                    _user=Depends(require_role("management", "soc_analyst", "security_engineer"))):
    return legacy_status(db)
