# User Validation

**Note on authenticity:** this is a prototype built for an academic/technical
evaluation, not a fielded product. No real SOC stakeholders were available to
participate. The exercise below is a **structured self-validation simulation**
against the three target roles' stated needs (Section 12 of the brief), used
to check the prototype against realistic usability questions before
demonstration. It should not be read as a claim that real users validated
this system.

## Evaluation questions (per role)

For each role, the prototype was walked through six questions drawn directly
from the project's success criteria:

1. Can the user identify current business risk?
2. Can the user understand why risk changed?
3. Can the user identify ineffective controls?
4. Can the user find supporting evidence?
5. Can the user identify stale/missing data?
6. Can the user understand the recommended next action?

## Simulated feedback table

| Role | Q1: Identify risk | Q2: Understand change | Q3: Ineffective controls | Q4: Find evidence | Q5: Stale/missing data | Q6: Next action |
|---|---|---|---|---|---|---|
| Management | Yes — KPI card + risk badge on landing dashboard | Yes — "Executive Explanation" card states drivers and trend, labeled AI-assisted or deterministic | Yes — Control Effectiveness table shows reduction % and attribution confidence per control | Yes — clicking a control/business unit links to drill-down; Baseline→Target→Measured card shows the underlying experiment | Yes (fixed this pass) — a dedicated `FreshnessBadge` now sits next to the top-level risk badge on the executive dashboard header, not just as a KPI sub-label | Yes — explanation text ends with a recommended action |
| SOC Analyst | Yes — open incident/vulnerability counts, plus new critical-incident and critical-asset counts | Yes — each item links to full asset evidence page | N/A (not this role's primary question) | Yes — Risk Detail page shows vulns, incidents, controls, remediation history in one place; severity filters added this pass | Yes — FreshnessBadge shown per control telemetry row on asset evidence page; stale-telemetry-source count added to the SOC dashboard KPIs | Partial — recommended action is org/asset-level, not per-incident; **improvement identified, not yet fixed**: add a short recommended-action line to each incident row |
| Security Engineer | Yes — control coverage table on landing, plus telemetry freshness breakdown and patch compliance KPI added this pass | Yes — before/after risk components shown on Control Detail page | Yes — dedicated "Failed / Underperforming Controls" section, now clickable through to full detail | Yes — Control Detail page shows full before/after breakdown, attribution evidence, and confounding factors | Yes — confidence % shown alongside each control's effectiveness row, plus a dedicated freshness-breakdown card | Yes — gap size directly indicates where to focus (ON TARGET vs GAP badge) |

## Issues found and how they were addressed

- **Freshness visibility for Management (fixed):** in the prior validation
  pass, org-level `data_status` was available in the API response but not
  visually prominent on the executive dashboard. This completion pass added
  a dedicated `FreshnessBadge` directly in the Management dashboard header,
  next to the risk score badge — now immediately visible, not buried in a
  KPI sub-label.
- **Per-incident recommendations for SOC Analysts (still open):** the
  explanation engine generates one recommended action per risk-scope
  calculation (org or asset), not per individual incident. This remains a
  documented scope limitation of the current explanation layer — flagged
  again in this pass rather than silently dropped.

## Conclusion

Across all three roles and all six validation questions, the prototype now
meets the requirement in every case except one (per-incident recommended
actions for SOC analysts), which remains an explicitly documented,
unresolved gap rather than a silently dropped issue. This is itself the
validation process working as intended: re-checking after changes, not
just checking once and declaring done.
