from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import DataQualityEvent, ControlTelemetry
from app.risk_engine.engine import freshness_status
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])
ANY_ROLE = Depends(get_current_user)


@router.get("")
def data_quality_overview(db: Session = Depends(get_db), _user=ANY_ROLE):
    events = db.query(DataQualityEvent).order_by(DataQualityEvent.detected_at.desc()).limit(300).all()
    by_type = {}
    for e in events:
        by_type[e.issue_type] = by_type.get(e.issue_type, 0) + 1

    now = datetime.utcnow()
    tel = db.query(ControlTelemetry).filter(ControlTelemetry.period == "CURRENT").all()
    freshness_counts = {"FRESH": 0, "AGING": 0, "STALE": 0, "MISSING": 0}
    for t in tel:
        freshness_counts[freshness_status(t.freshness_timestamp, now)] += 1

    return {
        "total_events": len(events),
        "by_issue_type": by_type,
        "telemetry_freshness_breakdown": freshness_counts,
        "recent_events": [{
            "event_id": e.event_id, "source_table": e.source_table, "record_id": e.record_id,
            "issue_type": e.issue_type, "detail": e.detail,
            "detected_at": e.detected_at.isoformat() if e.detected_at else None, "severity": e.severity,
        } for e in events[:100]],
    }
