"""
Control-effectiveness calculation.

Compares a BASELINE period against a CURRENT/POST-CONTROL period for each
control, using the same risk engine so "before" and "after" risk scores are
computed with an identical, documented method (methodology consistency is
what makes the comparison meaningful -- see docs/risk_methodology.md).
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.models import (Control, ControlTelemetry, Vulnerability, Incident, Asset, Remediation)
from app.risk_engine.engine import calculate_risk, freshness_status
from datetime import datetime


def _avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def compute_attribution(db: Session, control: Control, asset_ids: list[str],
                         baseline_tel: list, current_tel: list,
                         vulns_before_count: int, vulns_after_count: int,
                         incidents_before_count: int, incidents_after_count: int,
                         related_vuln_ids: list[str]) -> dict:
    """
    Evidence-based attribution/confidence score (0-100) for how much of the
    observed risk change can plausibly be attributed to THIS control, as
    opposed to unrelated factors. This is explicitly a CORRELATION-based
    heuristic, not a causal inference method -- see docs/error_analysis.md.

    Positive evidence (increases confidence):
      - coverage clearly improved (>=5 points)
      - compliance clearly improved (>=5 points)
      - related vulnerabilities decreased
      - related incidents decreased
      - current telemetry is FRESH (not stale/missing)
      - remediation work tied to this control's assets was completed+verified

    Negative evidence (decreases confidence / confounding):
      - current telemetry is STALE or MISSING
      - one or more OTHER controls covering the same assets also changed
        coverage significantly in the same window (confounding: cannot
        isolate which control drove the change)
      - incident volume changed but most incidents are not tagged as
        related to this control (change may be driven by unrelated causes)
    """
    baseline_coverage = _avg([t.coverage_percentage for t in baseline_tel])
    current_coverage = _avg([t.coverage_percentage for t in current_tel])
    baseline_compliance = _avg([t.compliance_percentage for t in baseline_tel])
    current_compliance = _avg([t.compliance_percentage for t in current_tel])

    evidence = []
    confounders = []
    score = 50.0  # start neutral; evidence moves it up or down

    if baseline_coverage is not None and current_coverage is not None:
        if current_coverage - baseline_coverage >= 5:
            score += 15
            evidence.append(f"Coverage improved {round(baseline_coverage,1)}% -> {round(current_coverage,1)}%.")
        elif current_coverage - baseline_coverage <= -5:
            score -= 10
            evidence.append(f"Coverage declined {round(baseline_coverage,1)}% -> {round(current_coverage,1)}%.")

    if baseline_compliance is not None and current_compliance is not None:
        if current_compliance - baseline_compliance >= 5:
            score += 10
            evidence.append(f"Compliance improved {round(baseline_compliance,1)}% -> {round(current_compliance,1)}%.")

    if vulns_after_count < vulns_before_count:
        score += 10
        evidence.append(f"Related vulnerabilities decreased ({vulns_before_count} -> {vulns_after_count}).")
    elif vulns_after_count > vulns_before_count:
        score -= 5
        evidence.append(f"Related vulnerabilities increased ({vulns_before_count} -> {vulns_after_count}).")

    if incidents_after_count < incidents_before_count:
        score += 10
        evidence.append(f"Related incidents decreased ({incidents_before_count} -> {incidents_after_count}).")

    # Telemetry freshness
    now = datetime.utcnow()
    freshness_statuses = [freshness_status(t.freshness_timestamp, now) for t in current_tel]
    worst = "MISSING"
    if freshness_statuses:
        order = ["INVALID", "MISSING", "STALE", "AGING", "FRESH"]
        worst = min(freshness_statuses, key=lambda s: order.index(s) if s in order else 0)
    if worst == "FRESH":
        score += 10
        evidence.append("Current telemetry is FRESH.")
    elif worst in ("STALE", "MISSING", "INVALID"):
        score -= 15
        confounders.append(f"Current telemetry is {worst} -- reduces confidence in the measured comparison.")

    # Remediation completion tied to this control's related vulnerabilities
    if related_vuln_ids:
        completed = db.query(Remediation).filter(
            Remediation.vulnerability_id.in_(related_vuln_ids),
            Remediation.status == "COMPLETE",
            Remediation.verification_status == "VERIFIED",
        ).count()
        if completed > 0:
            score += 10
            evidence.append(f"{completed} related remediation(s) completed and verified.")

    # Confounding: other controls covering the same assets also changed
    # coverage significantly in the same window -- we cannot cleanly
    # attribute the risk change to this control alone.
    if asset_ids:
        other_tel = db.query(ControlTelemetry).filter(
            ControlTelemetry.asset_id.in_(asset_ids),
            ControlTelemetry.control_id != control.control_id,
        ).all()
        by_control: dict[str, dict[str, list]] = {}
        for t in other_tel:
            by_control.setdefault(t.control_id, {"BASELINE": [], "CURRENT": []})
            if t.period in ("BASELINE", "CURRENT"):
                by_control[t.control_id][t.period].append(t.coverage_percentage)
        confounding_controls = []
        for other_id, periods in by_control.items():
            b = _avg(periods["BASELINE"])
            c = _avg(periods["CURRENT"])
            if b is not None and c is not None and abs(c - b) >= 10:
                confounding_controls.append(other_id)
        if confounding_controls:
            score -= min(20, 5 * len(confounding_controls))
            confounders.append(
                f"{len(confounding_controls)} other control(s) covering the same assets "
                f"also changed coverage significantly in the same window: {', '.join(confounding_controls)}."
            )

    score = round(max(0.0, min(100.0, score)), 1)
    return {
        "attribution_confidence": score,
        "attribution_evidence": evidence,
        "confounding_factors": confounders,
        "baseline_coverage": round(baseline_coverage, 1) if baseline_coverage is not None else None,
        "current_coverage_avg": round(current_coverage, 1) if current_coverage is not None else None,
        "baseline_compliance": round(baseline_compliance, 1) if baseline_compliance is not None else None,
        "current_compliance_avg": round(current_compliance, 1) if current_compliance is not None else None,
        "telemetry_freshness": worst,
    }


def compute_control_effectiveness(db: Session, control_id: str) -> dict:
    control = db.query(Control).filter(Control.control_id == control_id).first()
    if not control:
        return {"error": "control_not_found"}

    baseline_tel = db.query(ControlTelemetry).filter(
        and_(ControlTelemetry.control_id == control_id, ControlTelemetry.period == "BASELINE")
    ).all()
    current_tel = db.query(ControlTelemetry).filter(
        and_(ControlTelemetry.control_id == control_id, ControlTelemetry.period == "CURRENT")
    ).all()

    asset_ids = list({t.asset_id for t in baseline_tel + current_tel})
    assets = db.query(Asset).filter(Asset.asset_id.in_(asset_ids)).all() if asset_ids else []

    vulns = db.query(Vulnerability).filter(Vulnerability.asset_id.in_(asset_ids)).all() if asset_ids else []
    vulns_before = [v for v in vulns if v.discovered_date and str(v.remediation_status) in
                     ("OPEN", "IN_PROGRESS", "ACCEPTED_RISK")] if vulns else []
    # "before" state approximated as: vulns that existed and were still open at baseline
    # (i.e. not yet remediated); "after" = vulns still open now. Documented assumption:
    # since our synthetic data does not carry a point-in-time snapshot table for vulns,
    # we treat REMEDIATED vulns as resolved-by-current and everything else as currently open.
    vulns_after = [v for v in vulns if str(v.remediation_status) in ("OPEN", "IN_PROGRESS", "ACCEPTED_RISK")]
    vulns_before_count = len(vulns)  # all discovered vulns were "present" at baseline
    vulns_after_count = len(vulns_after)

    incidents = db.query(Incident).filter(Incident.asset_id.in_(asset_ids)).all() if asset_ids else []
    incidents_before = [i for i in incidents if i.period == "BASELINE"]
    incidents_after = [i for i in incidents if i.period == "CURRENT"]

    def as_dicts(objs, fields):
        return [{f: getattr(o, f, None) for f in fields} for o in objs]

    asset_dicts = as_dicts(assets, ["criticality"])
    vuln_dicts_before = as_dicts(vulns, ["severity", "remediation_status", "exploit_available", "internet_exposed"])
    vuln_dicts_after = as_dicts(vulns_after, ["severity", "remediation_status", "exploit_available", "internet_exposed"])
    inc_dicts_before = as_dicts(incidents_before, ["severity", "status"])
    inc_dicts_after = as_dicts(incidents_after, ["severity", "status"])

    baseline_tel_dicts = [{"target_coverage": control.target_coverage,
                            "coverage_percentage": t.coverage_percentage,
                            "compliance_percentage": t.compliance_percentage,
                            "health_status": t.health_status} for t in baseline_tel]
    current_tel_dicts = [{"target_coverage": control.target_coverage,
                           "coverage_percentage": t.coverage_percentage,
                           "compliance_percentage": t.compliance_percentage,
                           "health_status": t.health_status} for t in current_tel]

    risk_before = calculate_risk(asset_dicts, vuln_dicts_before, inc_dicts_before, baseline_tel_dicts,
                                  ["FRESH"] * max(1, len(baseline_tel)))
    risk_after = calculate_risk(asset_dicts, vuln_dicts_after, inc_dicts_after, current_tel_dicts,
                                 ["FRESH"] * max(1, len(current_tel)))

    reduction_abs = round(risk_before.total - risk_after.total, 2)
    reduction_pct = round((reduction_abs / risk_before.total) * 100, 1) if risk_before.total > 0 else 0.0

    avg_actual_coverage_current = (sum(t.coverage_percentage or 0 for t in current_tel) / len(current_tel)
                                    if current_tel else control.actual_coverage or 0)
    avg_compliance_current = (sum(t.compliance_percentage or 0 for t in current_tel) / len(current_tel)
                               if current_tel else 0)

    # Effectiveness score: blends risk reduction with how close actual coverage got to target.
    coverage_attainment = min(1.0, (avg_actual_coverage_current / control.target_coverage)
                               if control.target_coverage else 0)
    effectiveness_score = round(min(100.0, max(0.0, reduction_pct * 0.7 + coverage_attainment * 100 * 0.3)), 1)

    confidence = round(min(risk_before.confidence, risk_after.confidence), 1)

    # Evidence-based attribution/confidence -- explicitly correlation-based,
    # not causal proof (see docs/error_analysis.md).
    related_vuln_ids = [v.vulnerability_id for v in vulns]
    attribution = compute_attribution(
        db, control, asset_ids, baseline_tel, current_tel,
        vulns_before_count, vulns_after_count, len(incidents_before), len(incidents_after),
        related_vuln_ids,
    )

    TARGET_REDUCTION_PCT = 20.0

    return {
        "control_id": control_id,
        "control_name": control.control_name,
        "target_coverage": control.target_coverage,
        "baseline_coverage": attribution["baseline_coverage"],
        "actual_coverage": round(avg_actual_coverage_current, 1),
        "baseline_compliance": attribution["baseline_compliance"],
        "compliance": round(avg_compliance_current, 1),
        "affected_assets": len(asset_ids),
        "incidents_before": len(incidents_before),
        "incidents_after": len(incidents_after),
        "vulnerabilities_before": vulns_before_count,
        "vulnerabilities_after": vulns_after_count,
        "risk_before": risk_before.total,
        "risk_after": risk_after.total,
        "risk_reduction_abs": reduction_abs,
        "risk_reduction_pct": reduction_pct,
        "target_reduction_pct": TARGET_REDUCTION_PCT,
        "target_achieved": reduction_pct >= TARGET_REDUCTION_PCT,
        "effectiveness_score": effectiveness_score,
        "confidence": confidence,
        "attribution_confidence": attribution["attribution_confidence"],
        "attribution_evidence": attribution["attribution_evidence"],
        "confounding_factors": attribution["confounding_factors"],
        "telemetry_freshness": attribution["telemetry_freshness"],
        "causation_disclaimer": (
            "This reflects correlation between the control's improved coverage/compliance "
            "and a measured risk reduction over the same period. It is NOT proof that the "
            "control caused all of the observed change -- see confounding_factors and "
            "docs/error_analysis.md."
        ),
        "risk_before_components": {
            "vulnerability_component": risk_before.vulnerability_component,
            "incident_component": risk_before.incident_component,
            "control_gap_component": risk_before.control_gap_component,
            "asset_criticality_component": risk_before.asset_criticality_component,
        },
        "risk_after_components": {
            "vulnerability_component": risk_after.vulnerability_component,
            "incident_component": risk_after.incident_component,
            "control_gap_component": risk_after.control_gap_component,
            "asset_criticality_component": risk_after.asset_criticality_component,
        },
        "status": control.status,
    }


def compute_all_controls_effectiveness(db: Session) -> list[dict]:
    controls = db.query(Control).all()
    return [compute_control_effectiveness(db, c.control_id) for c in controls]
