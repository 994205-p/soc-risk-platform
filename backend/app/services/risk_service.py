"""
Aggregates data at organisation / asset scope and calls the risk engine.
Also implements the FALLBACK mechanism: if the "current" telemetry required
for a fresh calculation cannot be found, the service falls back to the most
recent verified risk_snapshot and marks the result as FALLBACK -- it never
silently pretends a stale result is fresh.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import Asset, Vulnerability, Incident, ControlTelemetry, Control, RiskSnapshot
from app.risk_engine.engine import calculate_risk, freshness_status
from app.risk_engine.explain import build_explanation
from app.risk_engine.llm_explainer import get_ai_explanation


def _as_dicts(objs, fields):
    return [{f: getattr(o, f, None) for f in fields} for o in objs]


def compute_org_risk(db: Session, scope_asset_ids: list[str] | None = None) -> dict:
    """Compute a live org-wide (or filtered) risk score. Returns dict with
    score, band, components, confidence, data_status, explanation, and
    whether a FALLBACK snapshot had to be used."""

    asset_q = db.query(Asset)
    if scope_asset_ids:
        asset_q = asset_q.filter(Asset.asset_id.in_(scope_asset_ids))
    assets = asset_q.all()
    asset_ids = [a.asset_id for a in assets] or [a.asset_id for a in db.query(Asset).all()]

    if not asset_ids:
        return _fallback_or_missing(db, "No assets found in database.")

    vulns = db.query(Vulnerability).filter(Vulnerability.asset_id.in_(asset_ids),
                                            Vulnerability.remediation_status.in_(
                                                ["OPEN", "IN_PROGRESS", "ACCEPTED_RISK"])).all()
    incidents = db.query(Incident).filter(Incident.asset_id.in_(asset_ids),
                                           Incident.period == "CURRENT").all()
    tel = db.query(ControlTelemetry).filter(ControlTelemetry.asset_id.in_(asset_ids),
                                             ControlTelemetry.period == "CURRENT").all()
    controls_by_id = {c.control_id: c for c in db.query(Control).all()}

    if not tel:
        return _fallback_or_missing(db, "No current control telemetry available for this scope.")

    tel_dicts = []
    freshness_list = []
    now = datetime.utcnow()
    for t in tel:
        ctrl = controls_by_id.get(t.control_id)
        tel_dicts.append({
            "target_coverage": ctrl.target_coverage if ctrl else 95.0,
            "coverage_percentage": t.coverage_percentage,
            "compliance_percentage": t.compliance_percentage,
            "health_status": t.health_status,
        })
        freshness_list.append(freshness_status(t.freshness_timestamp, now))

    asset_dicts = _as_dicts(assets, ["criticality"])
    vuln_dicts = _as_dicts(vulns, ["severity", "remediation_status", "exploit_available", "internet_exposed"])
    inc_dicts = _as_dicts(incidents, ["severity", "status"])

    components = calculate_risk(asset_dicts, vuln_dicts, inc_dicts, tel_dicts, freshness_list)

    # find prior snapshot for trend comparison
    prior = (db.query(RiskSnapshot)
             .filter(RiskSnapshot.scope_type == "ORG", RiskSnapshot.scope_id == "ALL")
             .order_by(RiskSnapshot.snapshot_time.desc()).first())
    prior_score = prior.risk_score if prior else None

    explanation = build_explanation(components, "the organisation" if not scope_asset_ids else "this scope",
                                     previous_score=prior_score)

    # Optional AI-assisted rewording -- grounded strictly in the evidence
    # below; falls back to the deterministic text on any failure or when
    # disabled (see app/risk_engine/llm_explainer.py and docs/responsible_ai.md).
    evidence = {
        "risk_score": components.total, "risk_band": components.band,
        "vulnerability_component": components.vulnerability_component,
        "incident_component": components.incident_component,
        "control_gap_component": components.control_gap_component,
        "asset_criticality_component": components.asset_criticality_component,
        "confidence": components.confidence, "data_status": components.data_status,
        "notes": components.notes, "previous_score": prior_score,
    }
    ai_result = get_ai_explanation(explanation, evidence)

    snapshot = RiskSnapshot(
        scope_type="ORG" if not scope_asset_ids else "FILTERED",
        scope_id="ALL" if not scope_asset_ids else ",".join(scope_asset_ids[:5]),
        snapshot_time=now, period_label="CURRENT",
        risk_score=components.total, risk_band=components.band,
        vulnerability_component=components.vulnerability_component,
        incident_component=components.incident_component,
        control_gap_component=components.control_gap_component,
        asset_criticality_component=components.asset_criticality_component,
        confidence=components.confidence, data_status=components.data_status,
        explanation=explanation,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "risk_score": components.total,
        "risk_band": components.band,
        "components": {
            "vulnerability_component": components.vulnerability_component,
            "incident_component": components.incident_component,
            "control_gap_component": components.control_gap_component,
            "asset_criticality_component": components.asset_criticality_component,
        },
        "confidence": components.confidence,
        "data_status": components.data_status,
        "explanation": ai_result["text"],
        "explanation_source": ai_result["source"],
        "explanation_label": ai_result["label"],
        "deterministic_explanation": explanation,
        "fallback": False,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_time": snapshot.snapshot_time.isoformat(),
        "asset_count": len(asset_ids),
    }


def _fallback_or_missing(db: Session, reason: str) -> dict:
    """Try to fall back to the last verified snapshot; otherwise report MISSING explicitly."""
    prior = (db.query(RiskSnapshot)
             .filter(RiskSnapshot.scope_type == "ORG", RiskSnapshot.scope_id == "ALL")
             .order_by(RiskSnapshot.snapshot_time.desc()).first())
    if prior:
        age = datetime.utcnow() - prior.snapshot_time
        return {
            "risk_score": prior.risk_score,
            "risk_band": prior.risk_band,
            "components": {
                "vulnerability_component": prior.vulnerability_component,
                "incident_component": prior.incident_component,
                "control_gap_component": prior.control_gap_component,
                "asset_criticality_component": prior.asset_criticality_component,
            },
            "confidence": max(10.0, prior.confidence - 15),
            "data_status": "FALLBACK",
            "explanation": (f"{reason} FALLBACK — showing last verified snapshot from "
                             f"{int(age.total_seconds() // 3600)} hour(s) ago. Confidence reduced."),
            "explanation_source": "deterministic",
            "explanation_label": "Evidence-based deterministic explanation",
            "deterministic_explanation": None,
            "fallback": True,
            "snapshot_id": prior.snapshot_id,
            "snapshot_time": prior.snapshot_time.isoformat(),
            "asset_count": None,
        }
    return {
        "risk_score": None,
        "risk_band": None,
        "components": None,
        "confidence": 0.0,
        "data_status": "MISSING",
        "explanation": f"{reason} No prior verified snapshot is available either — risk cannot be calculated.",
        "explanation_source": "deterministic",
        "explanation_label": "Evidence-based deterministic explanation",
        "deterministic_explanation": None,
        "fallback": False,
        "snapshot_id": None,
        "snapshot_time": None,
        "asset_count": 0,
    }


def compute_asset_risk(db: Session, asset_id: str) -> dict:
    asset = db.query(Asset).filter(Asset.asset_id == asset_id).first()
    if not asset:
        return {"error": "asset_not_found"}
    result = compute_org_risk(db, scope_asset_ids=[asset_id])
    result["asset"] = {
        "asset_id": asset.asset_id, "asset_name": asset.asset_name, "asset_type": asset.asset_type,
        "criticality": asset.criticality, "business_unit": asset.business_unit,
        "internet_exposed": asset.internet_exposed,
    }
    return result


def get_risk_trend(db: Session, limit: int = 30) -> list[dict]:
    snapshots = (db.query(RiskSnapshot)
                 .filter(RiskSnapshot.scope_type == "ORG")
                 .order_by(RiskSnapshot.snapshot_time.desc()).limit(limit).all())
    return [{
        "snapshot_time": s.snapshot_time.isoformat(),
        "risk_score": s.risk_score,
        "risk_band": s.risk_band,
        "confidence": s.confidence,
        "data_status": s.data_status,
    } for s in reversed(snapshots)]
