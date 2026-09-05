# Responsible AI

This project treats "AI" narrowly and honestly: a deterministic, rule-based
explanation layer is the default and required mechanism. An optional LLM
layer may reword that output, but the system's core risk determination never
depends on an LLM, and the LLM is never a source of new factual claims.

## AI-assisted vs. deterministic explanations (implementation)

`backend/app/risk_engine/llm_explainer.py` implements the optional layer:

1. **Deterministic path (default, always available):**
   `app/risk_engine/explain.py::build_explanation()` builds the explanation
   entirely from values already computed and stored by the risk engine
   (component scores, notes, confidence, prior snapshot). This function has
   no network dependency and cannot fail due to external services.
2. **Optional AI-assisted path:** only activates when
   `ENABLE_LLM_EXPLANATIONS=true` **and** `ANTHROPIC_API_KEY` is set. When
   active, `get_ai_explanation()` sends the deterministic text plus a
   strict evidence-only JSON payload to the model, with an explicit system
   prompt forbidding invented facts, invented numbers, or unsupported
   claims. The model's job is rewording for a business audience, not
   fact-finding.
3. **Fallback is automatic and silent to the request path:** any network
   error, timeout, malformed response, or missing configuration causes
   `get_ai_explanation()` to return the deterministic text unchanged. This
   function is designed to **never raise** — a failure in the optional layer
   can never break the core risk calculation or the API response.

Every explanation-bearing API response includes:

- `explanation` — the text to display (AI-reworded or deterministic)
- `explanation_source` — `"ai_assisted"` or `"deterministic"`
- `explanation_label` — the exact user-facing string:
  - **"AI-assisted explanation"** when the AI layer successfully reworded the text
  - **"Evidence-based deterministic explanation"** when the fallback (or
    default, since the feature ships disabled) path was used
- `deterministic_explanation` — the original deterministic text, always
  present, so the AI-reworded version can be checked against its source

The frontend (`ExplanationLabel` component in
`frontend/src/components/ui.jsx`) renders this label directly next to every
explanation card — it is never hidden or only shown on request.

**Default state:** `ENABLE_LLM_EXPLANATIONS=false` out of the box (see
`.env.example`), so a fresh install of this project runs entirely on
deterministic explanations with no API key required, satisfying "the
application MUST continue working using deterministic explanations."

## Explainability

Every risk score is decomposed into four named, capped components
(vulnerability, incident, control gap, asset criticality), each independently
stored in `risk_snapshots`. See `docs/risk_methodology.md` for the full
formula. There is no opaque model in the scoring path.

## Transparency

- The weighting rationale is documented, not just the numbers.
- Known limitations of the additive (vs. multiplicative) model are disclosed.
- Confidence and data status are always shown alongside the score, never
  hidden even when they are low.

## Data quality

Ingestion validates and flags (never silently drops or "fixes without a
trace") missing values, out-of-range percentages, duplicates, and stale
timestamps into `data_quality_events`, visible on the `/data-quality` page.

## Human oversight

The system explicitly frames itself as a decision-support tool: dashboards
recommend a "next action" but do not take any autonomous action against
production systems. Legacy migration/rollback and control changes are
human-triggered through the UI/API.

## Security

- No hardcoded secrets; configuration via environment variables
  (`.env.example`).
- Role-based authorization on dashboards (management / soc_analyst /
  security_engineer) via JWT.
- Passwords hashed with bcrypt.
- Parameterized queries throughout via SQLAlchemy ORM (no raw string-built
  SQL), mitigating injection risk.
- Audit logging for every legacy migration/rollback state transition.

## Privacy

All data in this project is synthetic. No real personal, customer, or
employee data is used or required to run the prototype.

## Bias

The risk formula's weights (documented in `risk_methodology.md`) are an
engineering judgment call about the relative importance of vulnerabilities,
incidents, control gaps, and asset criticality. This is disclosed as a
modeling assumption, not presented as an empirically "correct" answer — a
real deployment should validate weights against an organization's actual
historical loss/incident data.

## Hallucination prevention

The deterministic explanation layer (`app/risk_engine/explain.py`) builds
sentences exclusively from values already computed and stored by the risk
engine (component scores, notes, confidence, prior snapshot). It cannot
introduce a vulnerability, incident, or control that isn't in the evidence
it was given. If an optional LLM layer is enabled, it is instructed (see
`ENABLE_LLM_EXPLANATIONS` in `config.py`) to only rephrase this grounded
text — never to add new factual claims — and any LLM-generated text must be
clearly labeled as AI-generated in the UI.

## Auditability

`audit_logs` records every legacy migration/verify/rollback transition with
actor, previous state, new state, and timestamp. `risk_snapshots` preserves
every computed score with its full component breakdown, so any historical
number can be explained after the fact.

## Uncertainty

Confidence (0–100) and data status (FRESH/AGING/STALE/MISSING/FALLBACK) are
first-class, always-visible outputs of every risk calculation — never an
afterthought or hidden field.

## Fail-safe behavior

See `docs/failure_mode_analysis.md`. The guiding principle: it is always
better to show "we don't have enough evidence to be confident" than to show
a confident-looking number built on missing or broken data.

## What this system does NOT claim

- It does not claim that its risk score is a scientifically validated
  measure of actual financial or security loss probability.
- It does not claim that correlation between control rollout and risk
  reduction proves causation (see the control-effectiveness experiment,
  which explicitly reports this caveat).
- It does not fabricate incidents, vulnerabilities, or evidence under any
  circumstance — all displayed evidence traces back to a database record.
