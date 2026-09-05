# Test Evidence

This document is the normal-test and adversarial-test matrix requested in
the audit brief (section 8). All cases below were exercised directly against
`backend/app/risk_engine/engine.py` in `backend/tests/test_risk_engine.py`.

**Verification method note:** this sandbox has no outbound network access,
so `pip install` could not run and pytest itself could not be invoked. Every
test function below was instead executed directly via a small Python
harness that imports the test module and calls each `test_*` function in
turn (no pytest runner needed, since these are plain assertion functions
with no fixtures). Full command used:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
import tests.test_risk_engine as t
for name in dir(t):
    if name.startswith('test_'):
        getattr(t, name)()
        print('PASS', name)
"
```

Result at last verification: **17/17 passed, 0 failed.**

Once `pip install -r requirements.txt` succeeds in a networked environment,
the identical assertions run under `pytest tests/test_risk_engine.py -v`
without modification.

## Normal test matrix (spec section 21 / scenarios A-E)

| # | Scenario | Input | Expected result | Actual result | Test function |
|---|---|---|---|---|---|
| A | Controls improve | Same vulns/incidents, telemetry coverage 80%→96% | Risk decreases | Risk decreased | `test_scenario_a_controls_improve_risk_decreases` |
| B | Vulnerabilities increase | Add a CRITICAL, exploitable, internet-exposed vuln | Risk increases | Risk increased | `test_scenario_b_vulnerabilities_increase_risk_increases` |
| C | Critical asset exposed | Asset criticality MEDIUM→CRITICAL | Risk increases | Risk increased | `test_scenario_c_critical_asset_exposed_risk_increases_significantly` |
| D | Remediation completes | Vulnerability status OPEN→REMEDIATED | Risk decreases | Risk decreased | `test_scenario_d_remediation_completes_vuln_risk_decreases` |
| E | EDR coverage improves | Telemetry coverage/compliance 50%→95% | Control-gap component decreases | Gap component decreased | `test_scenario_e_edr_coverage_improves_gap_component_decreases` |

## Adversarial test matrix (spec section 8, 12 cases)

| # | Case | Input | Expected system response | Actual result | Test function |
|---|---|---|---|---|---|
| 1 | Coverage > 100 | `coverage_percentage=150` | Does not crash; does not produce negative/garbage risk | Gap score stayed within [0, 25] bounds | `test_adversarial_coverage_over_100_does_not_crash` |
| 2 | Coverage < 0 | `coverage_percentage=-40` | Does not crash; clamped/bounded | Gap score stayed within [0, 25] bounds | `test_adversarial_coverage_below_zero_does_not_crash` |
| 3 | Compliance > 100 | `compliance_percentage=250` | Does not crash; bounded | Gap score stayed within [0, 25] bounds | `test_adversarial_compliance_over_100_does_not_crash` |
| 4 | Compliance < 0 | `compliance_percentage=-30` | Does not crash; bounded | Gap score stayed within [0, 25] bounds | `test_adversarial_compliance_below_zero_does_not_crash` |
| 5 | Negative/malformed vulnerability input | Vulnerability dict with exploit+internet-exposed flags on a CRITICAL severity, LOW-criticality asset | Score stays within [0, 100]; vulnerability severity still meaningfully weighted | Total stayed within bounds; vuln component > 5 | `test_adversarial_negative_vulnerability_input_does_not_crash`, `test_adversarial_critical_vuln_low_asset_criticality_still_scored` |
| 6 | Stale telemetry | Timestamp 400 days old | Classified STALE, not FRESH | Returned `STALE` | `test_adversarial_extremely_old_timestamp_marked_stale` |
| 7 | Future timestamp | Timestamp 5 days in the future | Classified as its own INVALID state (never FRESH) | Returned `INVALID` | `test_adversarial_future_timestamp_marked_invalid_not_fresh` |
| 8 | Missing telemetry | Empty telemetry list | Gap defaults to moderate (50%), not zero/false-healthy; overall `data_status=MISSING`, confidence reduced | Gap > 0 with explicit "no control telemetry" note; `data_status == "MISSING"`, confidence < 100 | `test_adversarial_missing_telemetry_defaults_to_moderate_gap_not_zero`, `test_missing_data_reduces_confidence_and_flags_status` |
| 9 | Duplicate incidents | Generator (`data/generate_data.py`) deliberately injects 6 exact-duplicate incident rows | Ingestion pipeline detects and skips duplicates, logs a `data_quality_events` row with `issue_type=DUPLICATE` | Verified by code review of `backend/app/services/ingestion.py` (`seen_inc_ids` tracking) — **not executed end-to-end in this sandbox** (requires DB); logic path confirmed present and correct on inspection | Covered by `backend/tests/test_api.py::test_data_quality_endpoint_reports_injected_issues` once dependencies are installed |
| 10 | Invalid asset reference | Vulnerability CSV row with `asset_id` missing/blank | Ingestion logs `issue_type=MISSING` and skips the row rather than inserting a dangling foreign key | Verified by code review of `ingestion.py` vulnerability-loading block | Same as above — requires a live DB to execute; not run in this sandbox |
| 11 | Inconsistent/manipulated control telemetry | Coverage 99% but `health_status=FAILED` | Risk engine does not treat this as a healthy, well-covered control — FAILED health increases the gap score regardless of the raw coverage number | Gap score for FAILED-but-high-coverage was strictly greater than the equivalent HEALTHY case | `test_adversarial_inconsistent_telemetry_high_coverage_but_failed_health` |
| 12 | Missing critical vulnerability data | No vulnerability records supplied at all | Explicit note returned ("No vulnerability data available"); does not silently default to zero risk without disclosure | `score_vulnerabilities([])` returns `(0.0, ["No vulnerability data available for this scope."])`; overall result explicitly flags `data_status` | `test_missing_data_reduces_confidence_and_flags_status` |

## What was and was not executed in this environment

**Executed and verified directly:**
- All 17 functions in `backend/tests/test_risk_engine.py` (dependency-free —
  pure Python, no database or web framework required).
- The experiment notebook's core pandas computation (see
  `notebooks/control_effectiveness_experiment.ipynb` and the README) was
  run against the actual generated CSVs.
- All frontend `.jsx` files were syntax-checked with esbuild.

**Not executed in this environment (no outbound network access for
`pip install`/`npm install`):**
- `backend/tests/test_api.py` (FastAPI TestClient integration tests) —
  written and reviewed, covers login, dashboards, risk, controls, asset
  drill-down, data-quality, and the legacy migrate/rollback cycle, but
  requires `fastapi`/`sqlalchemy`/`httpx` installed to run.
- `docker compose up --build` — configuration reviewed line by line, not
  booted.
- `npm run build` for the frontend — code reviewed and syntax-checked, not
  bundled.

Anyone running this project with normal internet access should run:

```bash
cd backend && pip install -r requirements.txt && pytest tests -v
cd frontend && npm install && npm run build
```

and treat those two commands as the final confirmation step before a live
demo.
