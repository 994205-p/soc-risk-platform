"""
Deterministic, rule-based explanation layer.

Per project requirements, this is the DEFAULT and REQUIRED explanation
mechanism -- the application must work fully without any LLM/API key.
An optional LLM layer (see app/services/llm_explainer.py) can be enabled
via ENABLE_LLM_EXPLANATIONS, but it only *rewords* the evidence produced
here; it never invents evidence of its own (see docs/responsible_ai.md).
"""
from app.risk_engine.engine import RiskComponents


def build_explanation(components: RiskComponents, scope_label: str,
                       previous_score: float | None = None) -> str:
    band_text = {
        "VERY_LOW": "very low",
        "LOW": "low",
        "MODERATE": "moderate",
        "HIGH": "high",
        "CRITICAL": "critical",
    }[components.band]

    parts = [f"Business risk for {scope_label} is currently {components.total}/100 ({band_text.upper()})."]

    # Trend, if we have a comparison point
    if previous_score is not None:
        delta = round(previous_score - components.total, 1)
        if delta > 0.5:
            parts.append(f"This is an improvement of {delta} points compared to the prior period.")
        elif delta < -0.5:
            parts.append(f"This is a worsening of {abs(delta)} points compared to the prior period.")
        else:
            parts.append("This is essentially unchanged from the prior period.")

    # Main drivers -- rank components by contribution
    contributions = [
        ("unresolved vulnerabilities", components.vulnerability_component, 35.0),
        ("security incidents", components.incident_component, 25.0),
        ("control coverage/compliance gaps", components.control_gap_component, 25.0),
        ("critical asset exposure", components.asset_criticality_component, 15.0),
    ]
    contributions.sort(key=lambda c: (c[1] / c[2]), reverse=True)
    top = contributions[0]
    if top[1] > 0:
        parts.append(f"The largest contributor is {top[0]} ({top[1]}/{top[2]} points).")

    # Fold in the component notes (evidence, not generated claims)
    if components.notes:
        parts.append(" ".join(components.notes))

    # Data quality / confidence disclosure -- never hide this
    if components.confidence < 70:
        parts.append(
            f"NOTE: confidence in this score is reduced ({components.confidence}/100) because "
            f"underlying data is {components.data_status}. Treat this score as directional, not exact."
        )
    else:
        parts.append(f"Data confidence: {components.confidence}/100 ({components.data_status}).")

    parts.append("Recommended next action: " + recommend_action(components))

    return " ".join(parts)


def recommend_action(components: RiskComponents) -> str:
    contributions = {
        "vulnerability": components.vulnerability_component,
        "incident": components.incident_component,
        "control_gap": components.control_gap_component,
        "criticality": components.asset_criticality_component,
    }
    top = max(contributions, key=contributions.get)
    if components.confidence < 60:
        return "prioritize restoring data collection/telemetry before making major control decisions."
    return {
        "vulnerability": "prioritize remediation of open, exploitable, internet-facing vulnerabilities.",
        "incident": "investigate root causes of recent incidents and confirm containment.",
        "control_gap": "close coverage/compliance gaps on underperforming controls.",
        "criticality": "review protections on the highest-criticality assets in scope.",
    }[top]
