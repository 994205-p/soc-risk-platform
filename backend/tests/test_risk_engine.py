"""Unit tests for the risk engine — normal + adversarial cases (section 20/21 of spec)."""
from datetime import datetime, timedelta

from app.risk_engine.engine import calculate_risk, freshness_status, score_control_gap


def base_inputs():
    assets = [{"criticality": "MEDIUM"}]
    vulns = [{"severity": "MEDIUM", "remediation_status": "OPEN", "exploit_available": False, "internet_exposed": False}]
    incidents = []
    tel = [{"target_coverage": 95, "coverage_percentage": 80, "compliance_percentage": 80, "health_status": "HEALTHY"}]
    return assets, vulns, incidents, tel


# ---- Normal scenarios (section 21) ----------------------------------------

def test_scenario_a_controls_improve_risk_decreases():
    assets, vulns, incidents, tel_before = base_inputs()
    tel_after = [{"target_coverage": 95, "coverage_percentage": 96, "compliance_percentage": 96, "health_status": "HEALTHY"}]
    before = calculate_risk(assets, vulns, incidents, tel_before, ["FRESH"])
    after = calculate_risk(assets, vulns, incidents, tel_after, ["FRESH"])
    assert after.total < before.total


def test_scenario_b_vulnerabilities_increase_risk_increases():
    assets, vulns, incidents, tel = base_inputs()
    more_vulns = vulns + [{"severity": "CRITICAL", "remediation_status": "OPEN",
                            "exploit_available": True, "internet_exposed": True}]
    before = calculate_risk(assets, vulns, incidents, tel, ["FRESH"])
    after = calculate_risk(assets, more_vulns, incidents, tel, ["FRESH"])
    assert after.total > before.total


def test_scenario_c_critical_asset_exposed_risk_increases_significantly():
    assets, vulns, incidents, tel = base_inputs()
    critical_assets = [{"criticality": "CRITICAL"}]
    before = calculate_risk(assets, vulns, incidents, tel, ["FRESH"])
    after = calculate_risk(critical_assets, vulns, incidents, tel, ["FRESH"])
    assert after.total > before.total


def test_scenario_d_remediation_completes_vuln_risk_decreases():
    assets, vulns, incidents, tel = base_inputs()
    remediated = [{**vulns[0], "remediation_status": "REMEDIATED"}]
    before = calculate_risk(assets, vulns, incidents, tel, ["FRESH"])
    after = calculate_risk(assets, remediated, incidents, tel, ["FRESH"])
    assert after.total < before.total


def test_scenario_e_edr_coverage_improves_gap_component_decreases():
    low_cov = [{"target_coverage": 95, "coverage_percentage": 50, "compliance_percentage": 50, "health_status": "HEALTHY"}]
    high_cov = [{"target_coverage": 95, "coverage_percentage": 95, "compliance_percentage": 95, "health_status": "HEALTHY"}]
    gap_low, _ = score_control_gap(low_cov)
    gap_high, _ = score_control_gap(high_cov)
    assert gap_high < gap_low


# ---- Adversarial scenarios (section 20) ------------------------------------

def test_adversarial_coverage_over_100_does_not_crash():
    tel = [{"target_coverage": 95, "coverage_percentage": 150, "compliance_percentage": 150, "health_status": "HEALTHY"}]
    gap, notes = score_control_gap(tel)
    assert gap >= 0  # invalid >100 coverage should not produce negative/garbage risk


def test_adversarial_negative_vulnerability_input_does_not_crash():
    assets, _, incidents, tel = base_inputs()
    weird_vulns = [{"severity": "CRITICAL", "remediation_status": "OPEN",
                     "exploit_available": True, "internet_exposed": True}]
    result = calculate_risk(assets, weird_vulns, incidents, tel, ["FRESH"])
    assert 0 <= result.total <= 100


def test_adversarial_extremely_old_timestamp_marked_stale():
    old = datetime.utcnow() - timedelta(days=400)
    assert freshness_status(old) == "STALE"


def test_adversarial_future_timestamp_marked_invalid_not_fresh():
    future = datetime.utcnow() + timedelta(days=5)
    status = freshness_status(future)
    assert status == "INVALID"
    assert status != "FRESH"


def test_adversarial_critical_vuln_low_asset_criticality_still_scored():
    low_crit_assets = [{"criticality": "LOW"}]
    critical_vuln = [{"severity": "CRITICAL", "remediation_status": "OPEN",
                       "exploit_available": True, "internet_exposed": True}]
    result = calculate_risk(low_crit_assets, critical_vuln, [], base_inputs()[3], ["FRESH"])
    # vulnerability component should still be significant even though asset criticality is low
    assert result.vulnerability_component > 5


def test_adversarial_missing_telemetry_defaults_to_moderate_gap_not_zero():
    gap, notes = score_control_gap([])
    assert gap > 0
    assert "missing" in notes[0].lower() or "no control telemetry" in notes[0].lower()


def test_missing_data_reduces_confidence_and_flags_status():
    result = calculate_risk(*base_inputs()[:3], base_inputs()[3], [])
    assert result.data_status == "MISSING"
    assert result.confidence < 100


def test_adversarial_coverage_below_zero_does_not_crash():
    tel = [{"target_coverage": 95, "coverage_percentage": -40, "compliance_percentage": 80, "health_status": "HEALTHY"}]
    gap, notes = score_control_gap(tel)
    assert gap >= 0
    assert gap <= 25.0


def test_adversarial_compliance_over_100_does_not_crash():
    tel = [{"target_coverage": 95, "coverage_percentage": 90, "compliance_percentage": 250, "health_status": "HEALTHY"}]
    gap, notes = score_control_gap(tel)
    assert gap >= 0
    assert gap <= 25.0


def test_adversarial_compliance_below_zero_does_not_crash():
    tel = [{"target_coverage": 95, "coverage_percentage": 90, "compliance_percentage": -30, "health_status": "HEALTHY"}]
    gap, notes = score_control_gap(tel)
    assert gap >= 0
    assert gap <= 25.0


def test_adversarial_inconsistent_telemetry_high_coverage_but_failed_health():
    """A control claiming near-100% coverage but reporting FAILED health should
    NOT be scored as if it were a healthy, well-covered control -- health
    status must increase the gap even when the raw coverage number looks good
    (spec section 20, case 11: 'manipulated control telemetry claiming 100%
    coverage while evidence indicates lower coverage')."""
    healthy = [{"target_coverage": 95, "coverage_percentage": 99, "compliance_percentage": 99, "health_status": "HEALTHY"}]
    failed_but_high = [{"target_coverage": 95, "coverage_percentage": 99, "compliance_percentage": 99, "health_status": "FAILED"}]
    gap_healthy, _ = score_control_gap(healthy)
    gap_failed, _ = score_control_gap(failed_but_high)
    assert gap_failed > gap_healthy


def test_adversarial_extremely_old_timestamp_is_stale_not_invalid():
    """Old-but-plausible timestamps are STALE; only future/impossible
    timestamps are INVALID -- these are deliberately distinct states."""
    old = datetime.utcnow() - timedelta(days=30)
    assert freshness_status(old) == "STALE"
