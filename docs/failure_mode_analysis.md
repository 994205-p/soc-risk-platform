# Failure Mode Analysis

| Failure Mode | Cause | Detection | System Response | User Message | Impact |
|---|---|---|---|---|---|
| Missing data | Telemetry/vuln/incident source has no records for scope | `compute_org_risk` checks for empty query results before scoring | Falls back to last verified `risk_snapshot`, marked FALLBACK; if none exists, returns explicit MISSING result with no score | "Risk calculation has limited confidence / cannot be calculated because <source> is unavailable." | Score may be unavailable or based on older data; confidence reduced or zero |
| Stale data | Telemetry `freshness_timestamp` older than AGING/STALE thresholds | `freshness_status()` compares timestamp age against `FRESH_THRESHOLD_HOURS` / `AGING_THRESHOLD_HOURS` | Component confidence reduced; overall `data_status` set to worst observed status | "Data confidence reduced — treat this score as directional, not exact." | Score still shown but explicitly flagged, never silently treated as current |
| API/service failure | Backend unreachable, DB connection dropped | Frontend `fetch` wrapper (`services/api.js`) catches non-2xx / network errors | UI renders `ErrorState` component instead of stale/blank data | "Error: <message>" | User sees an explicit error, not an empty or misleading dashboard |
| Invalid data | Coverage/compliance % outside 0–100, negative CVSS, non-numeric fields | `ingestion.py` `_clamp_pct()` and CVSS range check | Value clamped to valid range AND a `data_quality_events` row logged with issue_type=INVALID | Visible in `/data-quality` page as a flagged INVALID event | Prevents garbage values from silently corrupting the risk score |
| Duplicate data | Same `asset_id`/`incident_id`/`telemetry_id` appears twice in source | Ingestion tracks `seen_*_ids` sets during load | Second occurrence skipped and logged as DUPLICATE | Visible in `/data-quality` page | Prevents double-counting in risk aggregation |
| Database failure | Postgres/SQLite unavailable at startup | SQLAlchemy engine connection raises on first query | Uncaught at this prototype stage — FastAPI returns 500; documented as a limitation (see README "Limitations") | Standard FastAPI 500 error | Full outage of the API tier until DB restored |
| Migration failure | Legacy case migration operation fails partway or produces unexpected state | Not simulated as a hard failure in this prototype — migration is a straightforward state transition | Rollback endpoint (`POST /api/legacy/rollback`) is always available to reverse MIGRATED/VERIFIED cases back to ROLLED_BACK | "Rolled back N case(s) to legacy workflow." | Legacy workflow can always be restored; audit log records the reversal |
| Incorrect/manipulated telemetry | A control reports coverage inconsistent with other evidence (e.g., claimed 100% coverage with FAILED health status) | Control gap scoring increases gap when `health_status` is DEGRADED/FAILED even if coverage % looks high; data-quality layer flags out-of-range values | Risk engine does not take a single "coverage %" field at face value — health status and compliance are cross-checked | Flagged in explanation notes and `/data-quality` events | Reduces risk of a single manipulated/broken metric producing a falsely low risk score |
| Control failure | A control's `health_status` = FAILED | `score_control_gap()` adds +0.3 to the gap score for FAILED telemetry | Control gap component (and therefore overall risk) increases | Explanation names "control coverage/compliance gaps" as a top driver when this dominates | Risk score reflects control failure promptly rather than lagging |

## Design principle behind all rows above

No failure mode is allowed to produce a **confidently wrong** number. The
system's default behavior under any of the above conditions is to either
(a) reduce confidence and say so explicitly, (b) fall back to a labeled,
timestamped prior result, or (c) show no score at all with a clear reason —
never to silently interpolate or guess without disclosure.
