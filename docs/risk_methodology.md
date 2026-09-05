# Risk Methodology

## Why not a black-box model?

The project brief explicitly rules out a black-box ML risk score. A transparent,
component-based formula was chosen instead so any user — analyst, engineer, or
executive — can trace exactly why a number is what it is, and so the same
formula can be applied consistently to "before" and "after" periods for the
control-effectiveness experiment (comparability requires a fixed, documented
method).

## Formula

```
Risk (0–100) = Vulnerability Risk (0–35)
             + Incident Risk       (0–25)
             + Control Gap Risk    (0–25)
             + Asset Criticality   (0–15)
```

Each component is independently capped, so no single input can dominate the
score in a way that isn't visible in the stored breakdown
(`risk_snapshots.vulnerability_component`, etc.).

### Component weighting rationale

| Component | Max points | Rationale |
|---|---|---|
| Vulnerability Risk | 35 | Unresolved technical exposure is the most directly exploitable driver of business risk. |
| Incident Risk | 25 | Realized harm — evidence that exposure has already been acted on by an adversary. |
| Control Gap Risk | 25 | A coverage/compliance gap is a leading indicator of future incidents; weighted equal to realized incidents because prevention matters as much as response. |
| Asset Criticality | 15 | Smaller, additive weight for transparency. A fully multiplicative model (risk × criticality multiplier) would better reflect real-world impact scaling but is harder to audit — documented as a known limitation. |

### Vulnerability component

For each vulnerability: `severity_weight × (10 if open else 2)`, boosted
1.4× if an exploit is publicly available and 1.25× if the asset is
internet-exposed. Values are summed, then normalized with a square-root
curve (`min(35, sqrt(raw) * 2.1)`) so the 50th open vulnerability adds less
marginal risk than the 1st — diminishing returns, not a linear multiplier of
vulnerability count.

### Incident component

Same diminishing-returns approach: `severity_weight × (8 if open else 3)`,
normalized to a 25-point scale.

### Control gap component

For each control/asset telemetry record:
`gap = (coverage_gap * 0.6 + compliance_gap * 0.4) / 100`, increased by
0.15–0.3 if the control's health status is DEGRADED/FAILED. Averaged across
all relevant telemetry records, then scaled to 25 points. If no telemetry
exists at all, the component defaults to 50% of max (12.5 points) — a
documented, moderate "we don't know" default rather than pretending there is
no gap.

### Asset criticality component

Average of each asset's criticality weight (LOW=0.25 … CRITICAL=1.0) scaled
to 15 points.

## Risk bands

| Score | Band |
|---|---|
| 0–20 | VERY LOW |
| 21–40 | LOW |
| 41–60 | MODERATE |
| 61–80 | HIGH |
| 81–100 | CRITICAL |

## Confidence and data freshness

Every score is accompanied by a confidence value (0–100) and a data status
(FRESH / AGING / STALE / MISSING / INVALID / FALLBACK). Confidence starts at
100 and is reduced per non-fresh input (AGING −8, STALE −20, MISSING −30,
INVALID −35, averaged and scaled). `INVALID` is a distinct state from
`STALE`, used specifically for timestamps that are logically impossible
(e.g. in the future, from clock skew or data corruption) — it is penalized
more heavily than ordinary staleness because it signals a data-quality
defect rather than merely old-but-legitimate data. The overall `data_status`
reported is always the **worst** status seen among inputs — confidence is
never allowed to hide staleness behind an average.

## Control-effectiveness attribution

The formula above is also the basis for the control-effectiveness
before/after comparison (`backend/app/services/control_effectiveness.py`),
which additionally computes an `attribution_confidence` score reflecting how
consistently the evidence (coverage/compliance change, related vulnerability
and incident trends, telemetry freshness, verified remediation, and
overlapping-control confounding) supports crediting a specific control for
the observed risk change. This is explicitly a correlation-based heuristic,
not a causal-inference method — see `docs/error_analysis.md` section 6 for
the full methodology and its limits.

## Known limitations (documented, not hidden)

- The additive model does not capture true multiplicative risk amplification
  (e.g. a CRITICAL vulnerability on a CRITICAL asset is worse than the sum of
  its parts would suggest).
- Confidence penalties are heuristic, not statistically calibrated against
  real incident data (none exists for this synthetic prototype).
- The formula was tuned by engineering judgment, not by fitting against
  historical loss data — this is disclosed here and in `docs/responsible_ai.md`.
