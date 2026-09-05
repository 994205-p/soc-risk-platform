"""
Legacy SOC workflow coexistence + migration/rollback demonstration.

migration_status lifecycle: NOT_MIGRATED -> MIGRATED -> VERIFIED
                                                 -> ROLLED_BACK (from MIGRATED or VERIFIED)
Every transition is written to audit_logs with previous/new state and a
timestamp, so the rollback demo has a visible, inspectable audit trail.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import LegacyCase, AuditLog


def get_status(db: Session) -> dict:
    total = db.query(LegacyCase).count()
    migrated = db.query(LegacyCase).filter(LegacyCase.migration_status.in_(["MIGRATED", "VERIFIED"])).count()
    verified = db.query(LegacyCase).filter(LegacyCase.migration_status == "VERIFIED").count()
    rolled_back = db.query(LegacyCase).filter(LegacyCase.migration_status == "ROLLED_BACK").count()
    return {
        "total_cases": total,
        "not_migrated": total - migrated - rolled_back,
        "migrated": migrated - verified,
        "verified": verified,
        "rolled_back": rolled_back,
    }


def migrate(db: Session, case_ids: list[str] | None, actor: str = "system") -> dict:
    q = db.query(LegacyCase).filter(LegacyCase.migration_status == "NOT_MIGRATED")
    if case_ids:
        q = q.filter(LegacyCase.legacy_case_id.in_(case_ids))
    cases = q.all()
    now = datetime.utcnow()
    for c in cases:
        prev = c.migration_status
        c.migration_status = "MIGRATED"
        c.migrated = True
        c.migration_timestamp = now
        db.add(AuditLog(actor=actor, action="MIGRATE", entity="legacy_case", entity_id=c.legacy_case_id,
                         previous_state=prev, new_state="MIGRATED", timestamp=now,
                         detail="Case enriched into new risk platform."))
    db.commit()
    return {"migrated_count": len(cases), "case_ids": [c.legacy_case_id for c in cases]}


def verify(db: Session, case_ids: list[str] | None, actor: str = "system") -> dict:
    q = db.query(LegacyCase).filter(LegacyCase.migration_status == "MIGRATED")
    if case_ids:
        q = q.filter(LegacyCase.legacy_case_id.in_(case_ids))
    cases = q.all()
    now = datetime.utcnow()
    for c in cases:
        prev = c.migration_status
        c.migration_status = "VERIFIED"
        db.add(AuditLog(actor=actor, action="VERIFY", entity="legacy_case", entity_id=c.legacy_case_id,
                         previous_state=prev, new_state="VERIFIED", timestamp=now, detail="Migration verified."))
    db.commit()
    return {"verified_count": len(cases)}


def rollback(db: Session, case_ids: list[str] | None, actor: str = "system", reason: str = "manual rollback") -> dict:
    q = db.query(LegacyCase).filter(LegacyCase.migration_status.in_(["MIGRATED", "VERIFIED"]))
    if case_ids:
        q = q.filter(LegacyCase.legacy_case_id.in_(case_ids))
    cases = q.all()
    now = datetime.utcnow()
    for c in cases:
        prev = c.migration_status
        c.migration_status = "ROLLED_BACK"
        c.migrated = False
        db.add(AuditLog(actor=actor, action="ROLLBACK", entity="legacy_case", entity_id=c.legacy_case_id,
                         previous_state=prev, new_state="ROLLED_BACK", timestamp=now, detail=reason))
    db.commit()
    return {"rolled_back_count": len(cases), "reason": reason}


def get_audit_log(db: Session, limit: int = 50) -> list[dict]:
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [{
        "audit_id": l.audit_id, "actor": l.actor, "action": l.action, "entity": l.entity,
        "entity_id": l.entity_id, "previous_state": l.previous_state, "new_state": l.new_state,
        "timestamp": l.timestamp.isoformat(), "detail": l.detail,
    } for l in logs]
