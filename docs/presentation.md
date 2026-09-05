# Presentation: SOC Control Effectiveness & Business Risk Platform

## Slide 1 — Title
**AI-Assisted Security Control Effectiveness and Business Risk Dashboard**
*Turning SOC telemetry into explainable business risk.*

Speaker notes: Introduce the team/role framing and the one-sentence pitch:
"We can measure whether security controls are actually reducing business
risk, explain the change, prove it with evidence, and safely handle failure."

## Slide 2 — Problem
- SOCs generate large volumes of technical security data.
- Management cannot easily tell whether implemented controls are reducing
  actual business risk.
- Existing reporting is either too technical or too opaque ("trust the
  score").

Speaker notes: Frame the gap between "we have alerts and controls" and
"we can measure impact."

## Slide 3 — Existing SOC Pain Point
- Legacy case-tracking workflows exist and can't be replaced overnight.
- Risk scoring, when it exists, is often a black box.
- Missing or stale telemetry is frequently invisible to decision-makers.

Speaker notes: Emphasize this is a coexistence story, not a rip-and-replace.

## Slide 4 — Proposed Solution
A platform that connects: Telemetry → Controls → Assets → Vulnerabilities →
Incidents → Remediation → Risk → Effectiveness → Explanation → Evidence →
Decision.

## Slide 5 — Architecture
Show `docs/architecture.md` diagram: React frontend, FastAPI backend,
Postgres/SQLite, dependency-free risk engine, synthetic data generator.

Speaker notes: Highlight that the risk engine has zero external dependencies
so it can be unit tested in isolation — this was demonstrated during build
(12/12 unit tests passing without a database or web framework).

## Slide 6 — Data Pipeline
- Synthetic generator produces BASELINE and CURRENT period data.
- Deliberate data-quality issues injected (missing, invalid, stale,
  duplicate) for realistic testing.
- Ingestion pipeline validates and flags issues instead of crashing.

## Slide 7 — Risk Calculation
- Transparent weighted formula: Vulnerability (35) + Incident (25) +
  Control Gap (25) + Asset Criticality (15) = 0–100.
- Every component stored and explainable.
- Confidence score and data-freshness status always shown.

## Slide 8 — Control Effectiveness
- Before/after comparison per control using the *same* risk formula.
- Example output: risk before 72 → risk after 52 → 27.8% reduction.
- Effectiveness score blends risk reduction with coverage attainment.

## Slide 9 — Dashboard
- Three role-based views: Management, SOC Analyst, Security Engineer.
- KPI cards, risk trend chart, control effectiveness table, drill-down
  evidence pages.

## Slide 10 — Experiment
- `notebooks/control_effectiveness_experiment.ipynb` runs the actual
  baseline → post-control measurement against the ingested dataset.
- Reports absolute/percentage risk reduction, target vs. measured result,
  and an explicit attribution/confidence discussion.

## Slide 11 — Failure & Adversarial Testing
- 12 unit tests: 5 normal scenarios (A–E) + 7 adversarial cases (invalid %,
  negative values, stale/future timestamps, missing telemetry, inconsistent
  metadata).
- `docs/failure_mode_analysis.md` documents system response to 9 failure
  modes.

## Slide 12 — Legacy Coexistence and Rollback
- Legacy cases coexist with the new platform via a migration state machine:
  NOT_MIGRATED → MIGRATED → VERIFIED, with ROLLED_BACK always available.
- Every transition is audit-logged with previous/new state and timestamp.
- Live demo: migrate → verify → rollback, in the `/legacy` page.

## Slide 13 — User Validation
- Structured self-validation against 6 usability questions × 3 roles
  (`docs/user_validation.md`).
- Honestly reports 2 identified gaps rather than claiming full validation.

## Slide 14 — Responsible AI
- Deterministic, evidence-grounded explanation layer is the default and
  required mechanism; optional LLM layer only rewords, never invents.
- Full disclosure of formula weighting rationale and known limitations.

## Slide 15 — Conclusion and Future Work
- Delivered: working prototype covering the full story from telemetry to
  business-risk explanation with evidence and safe failure handling.
- Future work: multiplicative risk modeling, real telemetry integration,
  calibrating weights against real incident/loss data, expanding LLM
  explanation layer with citation-level grounding.
