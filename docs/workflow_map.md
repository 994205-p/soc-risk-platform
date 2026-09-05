# Workflow Map

## End-to-end story the system demonstrates

```
Before controls:
  Organisation has measurable security risk
      |
      v
Security controls implemented:
  Patching, EDR, MFA, email security, etc.
  (data/generate_data.py simulates this via BASELINE -> CURRENT telemetry)
      |
      v
Telemetry confirms control improvement:
  Coverage and compliance increase
  (control_telemetry rows, period=CURRENT vs BASELINE)
      |
      v
Security exposure changes:
  Vulnerabilities and incidents decrease
  (vulnerabilities.remediation_status, incidents.period)
      |
      v
Risk engine measures the change:
  Business risk decreases
  (backend/app/risk_engine/engine.py -> compute_control_effectiveness)
      |
      v
Dashboard explains why:
  Which controls contributed, what risk remains
  (Management dashboard: Executive Explanation + Control Effectiveness table)
      |
      v
Evidence is available:
  Drill-down into assets, vulnerabilities, incidents, remediation
  (GET /api/assets/{id}/evidence, Risk Detail page)
      |
      v
Data problems are visible:
  Missing/stale data explicitly identified
  (GET /api/data-quality, Data Quality page)
      |
      v
Failure is safe:
  Fallback and rollback mechanisms work
  (compute_org_risk fallback logic, Legacy rollback page)
      |
      v
The experiment measures the result:
  Baseline -> Target -> Measured Risk Reduction -> Error Analysis
  (notebooks/control_effectiveness_experiment.ipynb)
```

## Legacy coexistence workflow

```
Legacy SOC System (legacy_cases table)
      |
      v
Existing alert/case (NOT_MIGRATED)
      |
      v
New risk platform (migration_status=MIGRATED)
      |
      v
Risk enrichment (case linked to asset/vuln/control risk context)
      |
      v
Management reporting (Management dashboard, Legacy status KPIs)

  [if migration fails or needs reversal]
      |
      v
Rollback (migration_status=ROLLED_BACK, audit_logs entry written)
      |
      v
Legacy workflow restored
```
