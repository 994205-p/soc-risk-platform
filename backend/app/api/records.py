"""Read endpoints for vulnerabilities, incidents, and remediation records."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Vulnerability, Incident, Remediation
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api", tags=["records"])
ANY_ROLE = Depends(get_current_user)


@router.get("/vulnerabilities")
def list_vulnerabilities(severity: str | None = None, status: str | None = Query(None, alias="status"),
                          asset_id: str | None = None, limit: int = 200, db: Session = Depends(get_db), _user=ANY_ROLE):
    q = db.query(Vulnerability)
    if severity:
        q = q.filter(Vulnerability.severity == severity.upper())
    if status:
        q = q.filter(Vulnerability.remediation_status == status.upper())
    if asset_id:
        q = q.filter(Vulnerability.asset_id == asset_id)
    rows = q.limit(limit).all()
    return [{
        "vulnerability_id": v.vulnerability_id, "asset_id": v.asset_id, "cve_id": v.cve_id,
        "severity": v.severity, "cvss_score": v.cvss_score,
        "discovered_date": v.discovered_date.isoformat() if v.discovered_date else None,
        "remediation_status": v.remediation_status, "exploit_available": v.exploit_available,
        "internet_exposed": v.internet_exposed, "business_impact": v.business_impact,
    } for v in rows]


@router.get("/incidents")
def list_incidents(severity: str | None = None, status: str | None = None, limit: int = 200,
                    db: Session = Depends(get_db), _user=ANY_ROLE):
    q = db.query(Incident)
    if severity:
        q = q.filter(Incident.severity == severity.upper())
    if status:
        q = q.filter(Incident.status == status.upper())
    rows = q.order_by(Incident.detected_at.desc()).limit(limit).all()
    return [{
        "incident_id": i.incident_id, "asset_id": i.asset_id, "incident_type": i.incident_type,
        "severity": i.severity, "detected_at": i.detected_at.isoformat() if i.detected_at else None,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None, "status": i.status,
        "root_cause": i.root_cause, "control_related": i.control_related,
        "financial_impact_estimate": i.financial_impact_estimate,
    } for i in rows]


@router.get("/remediation")
def list_remediation(status: str | None = None, limit: int = 200, db: Session = Depends(get_db), _user=ANY_ROLE):
    q = db.query(Remediation)
    if status:
        q = q.filter(Remediation.status == status.upper())
    rows = q.limit(limit).all()
    return [{
        "remediation_id": r.remediation_id, "vulnerability_id": r.vulnerability_id, "asset_id": r.asset_id,
        "assigned_to": r.assigned_to, "due_date": r.due_date.isoformat() if r.due_date else None,
        "completed_date": r.completed_date.isoformat() if r.completed_date else None,
        "status": r.status, "verification_status": r.verification_status,
    } for r in rows]
