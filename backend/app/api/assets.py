from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Asset, Vulnerability, Incident, ControlTelemetry, Control, Remediation
from app.risk_engine.engine import freshness_status
from app.services.risk_service import compute_asset_risk
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/assets", tags=["assets"])
ANY_ROLE = Depends(get_current_user)


@router.get("")
def list_assets(business_unit: str | None = None, criticality: str | None = None,
                 limit: int = 300, db: Session = Depends(get_db), _user=ANY_ROLE):
    q = db.query(Asset)
    if business_unit:
        q = q.filter(Asset.business_unit == business_unit)
    if criticality:
        q = q.filter(Asset.criticality == criticality.upper())
    rows = q.limit(limit).all()
    return [{
        "asset_id": a.asset_id, "asset_name": a.asset_name, "asset_type": a.asset_type,
        "business_unit": a.business_unit, "environment": a.environment, "criticality": a.criticality,
        "internet_exposed": a.internet_exposed, "operating_system": a.operating_system,
        "last_seen": a.last_seen.isoformat() if a.last_seen else None,
    } for a in rows]


@router.get("/{asset_id}/evidence")
def asset_evidence(asset_id: str, db: Session = Depends(get_db), _user=ANY_ROLE):
    """Full drill-down: Business Risk -> Asset -> Vulnerability/Incident -> Control -> Evidence."""
    asset = db.query(Asset).filter(Asset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    risk = compute_asset_risk(db, asset_id)

    vulns = db.query(Vulnerability).filter(Vulnerability.asset_id == asset_id).all()
    incidents = db.query(Incident).filter(Incident.asset_id == asset_id).all()
    telemetry = db.query(ControlTelemetry).filter(ControlTelemetry.asset_id == asset_id,
                                                    ControlTelemetry.period == "CURRENT").all()
    remediations = db.query(Remediation).filter(Remediation.asset_id == asset_id).all()
    controls_by_id = {c.control_id: c for c in db.query(Control).all()}

    now_status = lambda t: freshness_status(t.freshness_timestamp)

    return {
        "asset": {
            "asset_id": asset.asset_id, "asset_name": asset.asset_name, "asset_type": asset.asset_type,
            "criticality": asset.criticality, "business_unit": asset.business_unit,
            "environment": asset.environment, "owner": asset.owner,
            "internet_exposed": asset.internet_exposed, "operating_system": asset.operating_system,
            "last_seen": asset.last_seen.isoformat() if asset.last_seen else None,
        },
        "risk": risk,
        "vulnerabilities": [{
            "vulnerability_id": v.vulnerability_id, "cve_id": v.cve_id, "severity": v.severity,
            "cvss_score": v.cvss_score, "remediation_status": v.remediation_status,
            "exploit_available": v.exploit_available,
            "discovered_date": v.discovered_date.isoformat() if v.discovered_date else None,
        } for v in vulns],
        "incidents": [{
            "incident_id": i.incident_id, "incident_type": i.incident_type, "severity": i.severity,
            "status": i.status, "detected_at": i.detected_at.isoformat() if i.detected_at else None,
            "control_related": i.control_related, "root_cause": i.root_cause,
        } for i in incidents],
        "controls": [{
            "control_id": t.control_id,
            "control_name": controls_by_id[t.control_id].control_name if t.control_id in controls_by_id else t.control_id,
            "coverage_percentage": t.coverage_percentage, "compliance_percentage": t.compliance_percentage,
            "health_status": t.health_status, "data_quality": t.data_quality,
            "freshness_status": now_status(t),
            "freshness_timestamp": t.freshness_timestamp.isoformat() if t.freshness_timestamp else None,
        } for t in telemetry],
        "remediation_history": [{
            "remediation_id": r.remediation_id, "vulnerability_id": r.vulnerability_id,
            "status": r.status, "verification_status": r.verification_status,
            "completed_date": r.completed_date.isoformat() if r.completed_date else None,
        } for r in remediations],
    }
