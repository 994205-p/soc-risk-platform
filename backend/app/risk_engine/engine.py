"""
Transparent, explainable business-risk scoring engine.

DESIGN PRINCIPLE: no black-box ML score. Every number that goes into the
final risk score is stored so a user can trace exactly how it was produced.
See docs/risk_methodology.md for the full write-up of this formula and the
reasoning behind the chosen weights.

--------------------------------------------------------------------------
FORMULA (documented)
--------------------------------------------------------------------------
Risk (0-100) = Vulnerability Risk (0-35)
             + Incident Risk       (0-25)
             + Control Gap Risk    (0-25)
             + Asset Criticality   (0-15)

Each component is independently capped so no single factor can dominate
in a way that is not visible in the breakdown. The weights (35/25/25/15)
reflect a judgment call, documented here, that:
  - unresolved technical exposure (vulnerabilities) is the single largest
    driver of business risk because it is the most directly exploitable,
  - realized harm (incidents) is weighted second because it is evidence
    that exposure has already been acted upon,
  - control gaps are weighted equally to incidents because a coverage/
    compliance gap is a leading indicator of future incidents,
  - asset criticality is a smaller, multiplicative-in-spirit but additively
    implemented factor here for transparency (a simple weighted sum is
    easier to audit than a multiplicative model, at the cost of some
    nuance -- documented as a known limitation).

CONFIDENCE / DATA QUALITY:
The engine also computes a confidence score (0-100) based on how much of
the required input data is FRESH vs AGING/STALE/MISSING. Confidence is
reported alongside the score and never silently hidden. If confidence is
very low the score is still shown but explicitly flagged as low-confidence
per the "never pretend data is fresh" requirement.
--------------------------------------------------------------------------
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

FRESH_HOURS = 24
AGING_HOURS = 72


def freshness_status(timestamp: Optional[datetime], now: Optional[datetime] = None) -> str:
    """Classify a data point's freshness.
    Returns one of: FRESH / AGING / STALE / MISSING / INVALID.
    INVALID is used for timestamps that are logically impossible (e.g. in
    the future due to clock skew or data corruption) -- this is kept
    distinct from STALE because it signals a data-quality defect, not
    merely an old-but-legitimate reading."""
    if timestamp is None:
        return "MISSING"
    now = now or datetime.utcnow()
    age_hours = (now - timestamp).total_seconds() / 3600
    if age_hours < 0:
        # clock skew / corrupted future timestamp -- distinct INVALID state,
        # never silently treated as fresh or lumped in with ordinary staleness.
        return "INVALID"
    if age_hours <= FRESH_HOURS:
        return "FRESH"
    if age_hours <= AGING_HOURS:
        return "AGING"
    return "STALE"


@dataclass
class RiskComponents:
    vulnerability_component: float = 0.0
    incident_component: float = 0.0
    control_gap_component: float = 0.0
    asset_criticality_component: float = 0.0
    confidence: float = 100.0
    data_status: str = "FRESH"
    notes: list = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(min(100.0, self.vulnerability_component + self.incident_component
                          + self.control_gap_component + self.asset_criticality_component), 2)

    @property
    def band(self) -> str:
        score = self.total
        if score <= 20:
            return "VERY_LOW"
        if score <= 40:
            return "LOW"
        if score <= 60:
            return "MODERATE"
        if score <= 80:
            return "HIGH"
        return "CRITICAL"


CRITICALITY_WEIGHT = {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0}
SEVERITY_WEIGHT = {"LOW": 0.15, "MEDIUM": 0.4, "HIGH": 0.7, "CRITICAL": 1.0}


def score_vulnerabilities(vulns: list, max_points: float = 35.0) -> tuple[float, list]:
    """
    Each open/unremediated vulnerability contributes points scaled by severity,
    boosted if an exploit is publicly available or the asset is internet-exposed.
    Remediated vulnerabilities contribute a small residual (they still indicate
    historical exposure) but far less than open ones.
    """
    if not vulns:
        return 0.0, ["No vulnerability data available for this scope."]

    raw = 0.0
    notes = []
    open_count = 0
    for v in vulns:
        sev_weight = SEVERITY_WEIGHT.get(v.get("severity", "LOW"), 0.15)
        is_open = v.get("remediation_status") in ("OPEN", "IN_PROGRESS", "ACCEPTED_RISK", None)
        base = sev_weight * (10 if is_open else 2)
        if v.get("exploit_available"):
            base *= 1.4
        if v.get("internet_exposed"):
            base *= 1.25
        raw += base
        if is_open:
            open_count += 1

    # normalize with diminishing returns (sqrt) so 100 open vulns doesn't
    # instantly max the component -- each additional vuln matters less.
    normalized = min(max_points, (raw ** 0.5) * 2.1)
    notes.append(f"{open_count} open/unremediated vulnerabilities out of {len(vulns)} tracked.")
    return round(normalized, 2), notes


def score_incidents(incidents: list, max_points: float = 25.0) -> tuple[float, list]:
    """Recent, unresolved, and higher-severity incidents contribute more."""
    if not incidents:
        return 0.0, ["No incident data available for this scope."]

    raw = 0.0
    notes = []
    open_count = 0
    for inc in incidents:
        sev_weight = SEVERITY_WEIGHT.get(inc.get("severity", "LOW"), 0.15)
        is_open = inc.get("status") != "RESOLVED"
        base = sev_weight * (8 if is_open else 3)
        raw += base
        if is_open:
            open_count += 1

    normalized = min(max_points, (raw ** 0.5) * 1.9)
    notes.append(f"{open_count} open incidents out of {len(incidents)} tracked in scope/period.")
    return round(normalized, 2), notes


def score_control_gap(controls_telemetry: list, max_points: float = 25.0) -> tuple[float, list]:
    """
    Gap = (target_coverage - actual_coverage) and (100 - compliance), averaged
    across relevant controls. A larger gap = more risk. Degraded/failed control
    health status increases the gap contribution.
    """
    if not controls_telemetry:
        return max_points * 0.5, ["No control telemetry available -- gap risk defaulted to moderate (50%) due to missing evidence."]

    gap_scores = []
    notes = []
    failed = 0
    for t in controls_telemetry:
        target = t.get("target_coverage", 95.0) or 95.0
        actual = t.get("coverage_percentage", 0.0) or 0.0
        compliance = t.get("compliance_percentage", 0.0) or 0.0
        coverage_gap = max(0.0, target - actual)
        compliance_gap = max(0.0, 100.0 - compliance)
        gap = (coverage_gap * 0.6 + compliance_gap * 0.4) / 100.0  # 0..1
        if t.get("health_status") == "FAILED":
            gap = min(1.0, gap + 0.3)
            failed += 1
        elif t.get("health_status") == "DEGRADED":
            gap = min(1.0, gap + 0.15)
        gap_scores.append(gap)

    avg_gap = sum(gap_scores) / len(gap_scores)
    normalized = round(avg_gap * max_points, 2)
    notes.append(f"Average control coverage/compliance gap: {round(avg_gap * 100, 1)}%.")
    if failed:
        notes.append(f"{failed} control telemetry record(s) report FAILED health status.")
    return normalized, notes


def score_asset_criticality(assets: list, max_points: float = 15.0) -> tuple[float, list]:
    if not assets:
        return 0.0, ["No asset data available for this scope."]
    weights = [CRITICALITY_WEIGHT.get(a.get("criticality", "LOW"), 0.25) for a in assets]
    avg_weight = sum(weights) / len(weights)
    normalized = round(avg_weight * max_points, 2)
    crit_count = sum(1 for a in assets if a.get("criticality") == "CRITICAL")
    return normalized, [f"{crit_count} of {len(assets)} assets in scope are rated CRITICAL."]


def compute_confidence(freshness_statuses: list[str]) -> tuple[float, str]:
    """
    Confidence starts at 100 and is reduced for every non-fresh input.
    Overall data_status reflects the worst status seen (never hide staleness
    behind an average).
    """
    if not freshness_statuses:
        return 40.0, "MISSING"

    penalty = {"FRESH": 0, "AGING": 8, "STALE": 20, "MISSING": 30, "INVALID": 35}
    total_penalty = sum(penalty.get(s, 20) for s in freshness_statuses)
    confidence = max(10.0, 100.0 - total_penalty / max(1, len(freshness_statuses)) * 1.5)

    # INVALID (corrupted/future timestamp) is treated as worse than MISSING --
    # actively wrong data is a bigger risk to trust than simply absent data.
    order = ["INVALID", "MISSING", "STALE", "AGING", "FRESH"]
    worst = min(freshness_statuses, key=lambda s: order.index(s) if s in order else 0)
    return round(confidence, 1), worst


def calculate_risk(assets: list, vulnerabilities: list, incidents: list,
                    control_telemetry: list, freshness_statuses: list[str]) -> RiskComponents:
    """Main entry point: combine all components into a documented, explainable risk score."""
    vuln_score, vuln_notes = score_vulnerabilities(vulnerabilities)
    inc_score, inc_notes = score_incidents(incidents)
    gap_score, gap_notes = score_control_gap(control_telemetry)
    crit_score, crit_notes = score_asset_criticality(assets)
    confidence, worst_status = compute_confidence(freshness_statuses)

    components = RiskComponents(
        vulnerability_component=vuln_score,
        incident_component=inc_score,
        control_gap_component=gap_score,
        asset_criticality_component=crit_score,
        confidence=confidence,
        data_status=worst_status,
        notes=vuln_notes + inc_notes + gap_notes + crit_notes,
    )
    return components
