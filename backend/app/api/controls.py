from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Control
from app.services.control_effectiveness import compute_control_effectiveness, compute_all_controls_effectiveness
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/controls", tags=["controls"])
ANY_ROLE = Depends(get_current_user)


@router.get("")
def list_controls(db: Session = Depends(get_db), _user=ANY_ROLE):
    controls = db.query(Control).all()
    return [{
        "control_id": c.control_id, "control_name": c.control_name, "control_type": c.control_type,
        "target_coverage": c.target_coverage, "actual_coverage": c.actual_coverage,
        "status": c.status, "owner": c.owner,
    } for c in controls]


@router.get("/effectiveness")
def all_effectiveness(db: Session = Depends(get_db), _user=ANY_ROLE):
    return compute_all_controls_effectiveness(db)


@router.get("/{control_id}")
def get_control(control_id: str, db: Session = Depends(get_db), _user=ANY_ROLE):
    c = db.query(Control).filter(Control.control_id == control_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Control not found.")
    return {
        "control_id": c.control_id, "control_name": c.control_name, "control_type": c.control_type,
        "description": c.description, "target_coverage": c.target_coverage,
        "actual_coverage": c.actual_coverage, "status": c.status,
        "implementation_date": c.implementation_date.isoformat() if c.implementation_date else None,
        "owner": c.owner,
    }


@router.get("/{control_id}/effectiveness")
def control_effectiveness(control_id: str, db: Session = Depends(get_db), _user=ANY_ROLE):
    result = compute_control_effectiveness(db, control_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Control not found.")
    return result
