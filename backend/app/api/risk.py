from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import risk_service
from app.models.models import RiskSnapshot
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/risk", tags=["risk"])

# Risk/evidence data is shared across all three internal SOC roles (see
# docs/architecture.md "Authorization model" for the documented rationale) --
# unauthenticated requests are rejected, but any logged-in role may read it.
ANY_ROLE = Depends(get_current_user)


@router.get("/current")
def current_risk(db: Session = Depends(get_db), _user=ANY_ROLE):
    return risk_service.compute_org_risk(db)


@router.get("/trend")
def risk_trend(limit: int = 30, db: Session = Depends(get_db), _user=ANY_ROLE):
    return risk_service.get_risk_trend(db, limit=limit)


@router.get("/assets/{asset_id}")
def asset_risk(asset_id: str, db: Session = Depends(get_db), _user=ANY_ROLE):
    result = risk_service.compute_asset_risk(db, asset_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return result


@router.get("/explanations/{snapshot_id}")
def explanation_for_snapshot(snapshot_id: int, db: Session = Depends(get_db), _user=ANY_ROLE):
    snap = db.query(RiskSnapshot).filter(RiskSnapshot.snapshot_id == snapshot_id).first()
    if not snap:
        raise HTTPException(status_code=404, detail="Risk snapshot not found.")
    return {
        "snapshot_id": snap.snapshot_id,
        "risk_score": snap.risk_score,
        "risk_band": snap.risk_band,
        "explanation": snap.explanation,
        "confidence": snap.confidence,
        "data_status": snap.data_status,
        "components": {
            "vulnerability_component": snap.vulnerability_component,
            "incident_component": snap.incident_component,
            "control_gap_component": snap.control_gap_component,
            "asset_criticality_component": snap.asset_criticality_component,
        },
    }
