from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import MigrationRequest, RollbackRequest
from app.services import legacy_service
from app.utils.auth import get_current_user, require_role
from app.models.models import User

router = APIRouter(prefix="/api/legacy", tags=["legacy"])

ANY_ROLE = Depends(get_current_user)
# Migration/rollback are state-changing actions -- restricted to management
# and security_engineer (SOC analysts consume evidence but do not perform
# platform migrations in this model; see docs/architecture.md).
WRITE_ROLE = Depends(require_role("management", "security_engineer"))


@router.get("/status")
def status(db: Session = Depends(get_db), _user: User = ANY_ROLE):
    return legacy_service.get_status(db)


@router.post("/migrate")
def migrate(payload: MigrationRequest, db: Session = Depends(get_db), user: User = WRITE_ROLE):
    return legacy_service.migrate(db, payload.case_ids, actor=user.username)


@router.post("/verify")
def verify(payload: MigrationRequest, db: Session = Depends(get_db), user: User = WRITE_ROLE):
    return legacy_service.verify(db, payload.case_ids, actor=user.username)


@router.post("/rollback")
def rollback(payload: RollbackRequest, db: Session = Depends(get_db), user: User = WRITE_ROLE):
    return legacy_service.rollback(db, payload.case_ids, actor=user.username, reason=payload.reason)


@router.get("/audit-log")
def audit_log(limit: int = 50, db: Session = Depends(get_db), _user: User = ANY_ROLE):
    return legacy_service.get_audit_log(db, limit=limit)
