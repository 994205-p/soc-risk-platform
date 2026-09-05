# Error Analysis

This document is the honest accounting of where this prototype's measurements
can be wrong, imprecise, or misleading, and why. It complements
`docs/failure_mode_analysis.md` (which covers operational failure modes) by
focusing specifically on measurement and methodology error in the risk score
and the control-effectiveness experiment.

## 1. Missing telemetry

When a control has zero telemetry rows for a period, `score_control_gap()`
defaults the gap component to 50% of its maximum (12.5/25 points) rather
than 0 (falsely healthy) or 25 (falsely maximal risk). This is a deliberate,
documented middle-ground estimate, not a measurement — it should not be
read as equivalent in precision to a gap computed from real telemetry.
Confidence is reduced accordingly and `data_status` is set to `MISSING` so
this is visible, not hidden.

## 2. Stale data

Telemetry older than `AGING_THRESHOLD_HOURS` (72h by default) is classified
STALE and reduces confidence by 20 points per affected reading (see
`compute_confidence()` in `engine.py`). A risk score computed mostly from
stale inputs is still returned (never blocked entirely) but its confidence
will reflect that — a confidence below ~60 should be read as "directional,
not exact," per the explanation layer's own disclosure text.

## 3. Confounding controls

The control-effectiveness experiment measures each control independently,
but a single asset population can be covered by several controls
simultaneously. If two controls both improve coverage over the same window
for the same assets, the attribution scorer (`compute_attribution()` in
`control_effectiveness.py`) detects this and reduces the attribution
confidence score, listing the other control(s) by ID in
`confounding_factors`. It does **not** attempt to statistically decompose
how much of the risk change belongs to each control — that would require a
controlled experiment design (e.g. staggered rollout with a control group)
that a single organisation's SOC telemetry cannot provide.

## 4. Synthetic data limitations

- The generator (`data/generate_data.py`) uses a fixed random seed (42) for
  reproducibility, but the relationships it encodes (coverage improving
  15-40 points between baseline and current, ~65% of vulnerabilities
  eventually remediated, etc.) are engineering judgment calls calibrated to
  produce a *plausible* before/after story, not drawn from real incident
  data.
- Vulnerability "before" state is approximated: all discovered
  vulnerabilities are treated as present at baseline, and only remediation
  status distinguishes "current." A real system would use point-in-time
  snapshots instead. This is disclosed in `control_effectiveness.py` and
  `docs/architecture.md`.
- Incident volume in the synthetic data is deliberately generated at a lower
  rate in the CURRENT period (55% of baseline) to simulate control
  effectiveness — this is a modeling choice for demonstration purposes, not
  an empirical finding, and would look different against real telemetry.

## 5. Risk formula limitations

See `docs/risk_methodology.md` for the full formula. Known limitations
repeated here for completeness:

- The model is **additive**, not multiplicative — it does not capture
  interaction effects (a CRITICAL vulnerability on a CRITICAL asset is
  likely worse than the sum of a CRITICAL vulnerability component plus a
  CRITICAL asset-criticality component would suggest).
- Weights (35/25/25/15 point caps) are a documented engineering judgment,
  not fit against historical loss data — no such data exists for this
  synthetic prototype.
- The diminishing-returns square-root normalization for vulnerability/
  incident counts was chosen to avoid a single noisy count dominating the
  score, but the specific curve shape (`sqrt(raw) * constant`) was tuned by
  inspection, not derived from a statistical model.

## 6. Attribution uncertainty

The `attribution_confidence` score in `control_effectiveness.py` is
explicitly a **correlation-based heuristic**: it rewards internally
consistent evidence (coverage up, compliance up, related vulnerabilities
down, related incidents down, fresh telemetry, verified remediation) and
penalizes signs of confounding (stale/missing telemetry, other controls
changing coverage on the same assets at the same time). It is not a causal
inference method (no counterfactual/control-group comparison is possible
with this dataset), and every control-effectiveness API response carries an
explicit `causation_disclaimer` field stating this.

## 7. Possible measurement bias

- **Survivorship bias in the synthetic dataset**: assets and vulnerabilities
  are generated independently of "what a real attacker would have gone
  after," so the correlation between exposure and risk score in this
  dataset may be cleaner than in reality.
- **Self-referential validation**: the notebook experiment
  (`notebooks/control_effectiveness_experiment.ipynb`) reimplements the same
  formula as the backend (`app/risk_engine/engine.py`) by design, so it
  confirms internal consistency between the two, not external validity of
  the formula itself against ground truth.
- **No adversarial red-team data**: the "exploit_available" and
  "internet_exposed" flags in the synthetic vulnerability data are randomly
  assigned, not derived from a real threat-intelligence feed — a real
  deployment should replace this with actual exploit-availability data
  (e.g. CISA KEV) for meaningful severity weighting.

## Bottom line

Every number this system produces is reproducible and traceable to a
specific formula and a specific evidence set — but "reproducible" is not
the same claim as "empirically validated against real-world outcomes." This
distinction is disclosed here, in `docs/responsible_ai.md`, and in the
`causation_disclaimer` field returned by the API, rather than left implicit.
