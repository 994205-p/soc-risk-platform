# SOC Control Effectiveness & Business Risk Platform

An AI-assisted, **explainable** platform that answers one question for a
mid-sized enterprise SOC: *after security controls are implemented, did
actual security risk decrease, by how much, and what evidence explains it?*

## 1. Project overview

This is a working, runnable prototype — not a slide deck or a notebook in
isolation. It connects Security Telemetry → Controls → Assets →
Vulnerabilities → Incidents → Remediation → Risk Calculation → Control
Effectiveness → Business Risk → Explanation → Evidence → Management Decision,
end to end, with a synthetic (but realistic and deliberately imperfect)
dataset behind it.

## 2. Problem statement

SOCs generate large volumes of technical telemetry, but management typically
cannot tell whether the controls they've paid for are actually reducing
business risk. This project turns that telemetry into a transparent,
explainable, evidence-backed business-risk measurement — and honestly
reports its own confidence and data-quality limitations rather than
presenting a confident-looking black box.

## 3. Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full diagram and
data-flow narrative. In short:

```
Synthetic data generator -> CSV -> Ingestion/Validation -> PostgreSQL/SQLite
   -> Risk Engine (dependency-free, unit-tested) -> Explanation Layer
   -> FastAPI -> React frontend (3 role-based dashboards + drill-down evidence)
```

## 4. Features

- Transparent, documented 0–100 risk formula with stored component breakdown
  (see [`docs/risk_methodology.md`](docs/risk_methodology.md))
- Control-effectiveness engine: before/after risk, coverage, vulnerabilities,
  incidents, per control
- Deterministic, evidence-grounded explanation layer (LLM optional, never
  required — see [`docs/responsible_ai.md`](docs/responsible_ai.md))
- Three role-based dashboards: Management, SOC Analyst, Security Engineer
- Full drill-down: Business Risk → Asset → Vulnerability/Incident → Control
  → Evidence
- Freshness indicators (FRESH/AGING/STALE/MISSING) and a FALLBACK mechanism
  that never silently presents stale data as current
- Legacy workflow coexistence with a real migrate/verify/rollback demo and
  audit log
- Data-quality validation pipeline with deliberately injected test cases
  (missing, invalid, stale, duplicate data)
- 12 automated unit tests (normal + adversarial scenarios) plus API
  integration tests
- Experiment notebook that runs an actual baseline → post-control
  measurement against the ingested dataset

## 5. Technology stack

- **Frontend:** React + Vite + Tailwind CSS + Recharts
- **Backend:** Python + FastAPI + Pydantic + SQLAlchemy
- **Database:** PostgreSQL (via docker-compose), SQLite fallback for
  zero-dependency local runs
- **Data/Analytics:** Pandas, NumPy (notebook + generator)
- **Testing:** Pytest, FastAPI TestClient
- **Docs:** Markdown + Mermaid

## 6. Folder structure

```
soc-risk-platform/
├── backend/            FastAPI app, risk engine, services, tests
├── frontend/            React + Vite + Tailwind app
├── data/                 generate_data.py + generated CSVs
├── database/           schema.sql, seed.sql
├── notebooks/       control_effectiveness_experiment.ipynb
├── docs/                  architecture, methodology, failure modes, etc.
├── docker-compose.yml
└── .env.example
```

## 7. Installation

### Option A — Docker Compose (full stack, Postgres)

```bash
git clone <this project>
cd soc-risk-platform
cp .env.example .env
python3 data/generate_data.py        # generate synthetic dataset
docker compose up --build
```

- Backend: http://localhost:8000 (interactive docs at `/docs`)
- Frontend: http://localhost:5173

The backend automatically ingests `data/processed/*.csv` into the database
on first startup (it skips ingestion if data already exists).

### Option B — Local dev, no Docker (SQLite fallback)

```bash
# 1. Generate synthetic data
python3 data/generate_data.py

# 2. Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# (uses sqlite:///./soc_risk.db by default — see app/config.py)

# 3. Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

## 8. Environment setup

Copy `.env.example` to `.env` and adjust. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string, or leave unset for SQLite |
| `SECRET_KEY` | JWT signing secret — set a real random value for any non-local use |
| `ENABLE_LLM_EXPLANATIONS` | `false` by default; the app works fully without it |
| `FRESH_THRESHOLD_HOURS` / `AGING_THRESHOLD_HOURS` | Data freshness thresholds |

## 9. Database setup

`docker compose up` provisions Postgres automatically and the backend calls
`Base.metadata.create_all()` on startup (equivalent to running
`database/schema.sql`). To apply the schema manually against a Postgres
instance:

```bash
psql "$DATABASE_URL" -f database/schema.sql
psql "$DATABASE_URL" -f database/seed.sql
```

## 10. Data generation

```bash
python3 data/generate_data.py
```

Produces `data/processed/*.csv`: ~220 assets, 9 controls, ~3,200 telemetry
records (BASELINE + CURRENT periods), ~400 vulnerabilities, ~65 incidents,
~300 remediation records, 140 legacy cases, and a log of ~300 deliberately
injected data-quality issues (`_injected_data_quality_issues.csv`) used to
validate the ingestion pipeline.

## 11. Backend startup

See Option A/B above. Health check: `GET /api/health`.

## 12. Frontend startup

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` if the backend isn't at `http://localhost:8000`.

## 13. Running tests

```bash
cd backend
pip install -r requirements.txt
pytest tests -v
```

`tests/test_risk_engine.py` — 12 dependency-free unit tests (normal
scenarios A–E, adversarial cases from section 20 of the spec). These were
verified to pass during development.

`tests/test_api.py` — full API integration tests (login, dashboards, risk,
controls, asset drill-down, data quality, legacy migrate/rollback cycle).
These require `pip install -r requirements.txt` to have succeeded.

## 14. Running the experiment

```bash
cd notebooks
jupyter notebook control_effectiveness_experiment.ipynb
```

Requires `pandas`, `numpy`, `matplotlib` (`pip install pandas numpy
matplotlib jupyter`). The notebook reads directly from `data/processed/*.csv`
— no backend/database needed to run it. The core computation was validated
against the actual generated dataset during development: baseline risk
≈70.4, post-control risk ≈58.8, an ≈16.5% measured reduction (exact numbers
vary slightly by generator run since `random.seed(42)` is fixed but content
may shift if you regenerate with different parameters).

## 15. Demo users

| Username | Password | Role | Dashboard access (backend-enforced) |
|---|---|---|---|
| `manager` | `demo1234` | management | `/management` + all SOC/Engineering evidence + legacy migrate/rollback |
| `analyst` | `demo1234` | soc_analyst | `/soc` + all evidence (read-only on legacy) |
| `engineer` | `demo1234` | security_engineer | `/engineering` + all evidence + legacy migrate/rollback |

Created automatically on backend startup. **This is a demo credential
scheme for a prototype — not a production auth pattern.**

Role enforcement is real, not just frontend hiding: every API endpoint
requires a valid JWT, and the three role-specific dashboard endpoints
(`/api/dashboard/management`, `/soc`, `/engineering`) and the legacy
migrate/verify/rollback endpoints independently check the caller's role
server-side. See [`docs/architecture.md`](docs/architecture.md)
"Authorization model" for the full access table and the reasoning behind
which endpoints are role-restricted vs. shared across all authenticated
staff.

## 16. Dashboard explanation

- **Management** (`/management`): risk KPIs, baseline/target/measured
  experiment summary, risk trend, executive explanation (labeled AI-assisted
  or deterministic), control effectiveness table with attribution
  confidence, top business risks — deliberately free of raw technical
  detail.
- **SOC Analyst** (`/soc`): active incidents and open vulnerabilities with
  severity filtering, critical asset list, remediation backlog, stale
  telemetry count, links into full asset evidence.
- **Security Engineer** (`/engineering`): control coverage/compliance,
  telemetry freshness breakdown, patch compliance, failed/underperforming
  controls, full effectiveness + attribution detail.
- **Risk Detail** (`/risk/:assetId`): full drill-down evidence for one asset,
  including per-control freshness and the explanation-source label.
- **Control Detail** (`/controls/:controlId`): baseline→current
  coverage/compliance, attribution confidence, supporting evidence,
  confounding factors, and an explicit correlation-vs-causation disclaimer.
- **Legacy** (`/legacy`): migration status + live migrate/verify/rollback
  demo with audit log (buttons are disabled with an explanatory note for
  roles without write access).

## 17. Risk methodology

See [`docs/risk_methodology.md`](docs/risk_methodology.md) for the full
documented formula, weight rationale, freshness states (including the
distinct `INVALID` state for impossible/future timestamps), and known
limitations.

## 18. Control-effectiveness methodology

See [`backend/app/services/control_effectiveness.py`](backend/app/services/control_effectiveness.py)
and [`docs/error_analysis.md`](docs/error_analysis.md) section 6.
Effectiveness blends measured risk reduction (70%) with how close actual
coverage got to target (30%). Attribution confidence is a separate,
evidence-based correlation heuristic (coverage/compliance change, related
vulnerability/incident trends, telemetry freshness, verified remediation,
confounding-control detection) — every response explicitly states this is
correlation, not proof of causation.

## 19. Failure handling

See [`docs/failure_mode_analysis.md`](docs/failure_mode_analysis.md) for the
full table (missing data, stale data, API failure, invalid data, duplicates,
DB failure, migration failure, incorrect telemetry, control failure) and
[`docs/error_analysis.md`](docs/error_analysis.md) for measurement-level
error and bias analysis.

## 20. Legacy migration

See [`docs/rollback.md`](docs/rollback.md) and the `/legacy` page.
Migration and rollback actions are restricted to `management` and
`security_engineer` roles (enforced server-side); `soc_analyst` has
read-only visibility into migration status and the audit log.

## 21. Rollback

Same as above — migration and rollback are demonstrable, non-destructive,
and fully audit-logged with actor, previous state, new state, and timestamp.

## 22. Responsible AI

See [`docs/responsible_ai.md`](docs/responsible_ai.md) for the full
AI-assisted vs. deterministic explanation design, including exactly how the
optional layer is grounded, labeled, and falls back safely.

## 23. Full demo workflow

1. Login as **Management** (`manager` / `demo1234`).
2. On `/management`: read the current risk KPI, the Baseline → Target →
   Measured experiment card, and the Executive Explanation (note its
   "Evidence-based deterministic explanation" label — visible unless
   `ENABLE_LLM_EXPLANATIONS` is on).
3. Click a control in the Control Effectiveness table → `/controls/:id` →
   review attribution confidence, supporting evidence, confounding factors,
   and the causation disclaimer.
4. Click a business unit's underlying asset (via `/assets` or a linked
   vulnerability/incident) → `/risk/:assetId` → walk the full drill-down:
   vulnerabilities → incidents → control telemetry (with freshness badges)
   → remediation history.
5. Logout, login as **SOC Analyst** (`analyst` / `demo1234`).
6. On `/soc`: filter incidents/vulnerabilities by severity, review the
   critical asset list and remediation backlog.
7. Try `/legacy` as this role — migrate/verify/rollback buttons are
   disabled with an explanatory note (backend returns 403 if called
   directly).
8. Logout, login as **Security Engineer** (`engineer` / `demo1234`).
9. On `/engineering`: review telemetry freshness breakdown, patch
   compliance, and underperforming controls.
10. Open `/data-quality` — point out the injected MISSING/INVALID/STALE/
    DUPLICATE events from the synthetic generator.
11. On `/legacy` (this role CAN modify): run Migrate → Verify → Rollback in
    sequence and show the audit log updating with actor/previous/new state.
12. Run the experiment notebook (`notebooks/control_effectiveness_experiment.ipynb`)
    to show baseline/target/measured/attribution/error-analysis computed
    independently from the raw CSVs, using the same formula as the backend.

## 24. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend fails to start with a `DATABASE_URL` connection error | Postgres not reachable | Confirm `docker compose up` includes the `db` service and it passed its healthcheck, or unset `DATABASE_URL` to fall back to SQLite for local dev |
| `pip install` fails for `psycopg2-binary` | Missing system build tools for some platforms | On Debian/Ubuntu: `apt-get install libpq-dev python3-dev`; alternatively use the Docker path, which handles this in the image |
| Frontend shows "Error: Failed to fetch" on every page | `VITE_API_URL` doesn't match where the backend is running, or backend isn't started | Confirm backend is up at the expected port and `VITE_API_URL` (or the default `http://localhost:8000`) matches it |
| Login succeeds but every dashboard shows 403 | Logged in with a role that doesn't match the dashboard route (e.g. `analyst` visiting `/engineering`) | This is the authorization working as intended — see section 15's access table; use the role-appropriate dashboard |
| `/legacy` migrate/rollback buttons are disabled | Logged in as `soc_analyst`, which has read-only legacy access by design | Login as `manager` or `engineer` to perform migration actions |
| Notebook risk numbers don't exactly match the backend's `/api/risk/current` | Notebook uses org-wide averages across BASELINE/CURRENT periods from the CSVs directly; the live API reflects whatever the database currently holds (which may include legacy migration state changes made during a demo) | Expected — both use the identical formula (see `docs/risk_methodology.md`), but operate on potentially different snapshots of the data |
| Tests fail with `ModuleNotFoundError` | Dependencies not installed | Run `pip install -r backend/requirements.txt` before `pytest` |

## 25. Limitations

- **Still not booted end-to-end in this environment.** Across two
  completion passes, this sandbox has never had outbound network access, so
  `pip install`, `npm install`, and `docker compose up` could not be
  executed. What *has* been verified directly, both passes:
  - The risk engine's core logic (17/17 dependency-free unit tests passing
    as of this pass — up from 12, with the additional adversarial cases
    from `docs/test_evidence.md` section 8).
  - The notebook's pandas computation, executed against the real generated
    CSVs (a real bug — non-numeric columns from injected missing values —
    was found and fixed this way).
  - Every `.jsx` file, syntax-checked with esbuild after every edit,
    including this pass's sidebar/dashboard rewrites.
  - Every backend `.py` file, checked with `ast.parse()` under
    `-Werror` (zero syntax errors or warnings) after every edit.

  The FastAPI/SQLAlchemy integration layer (`backend/tests/test_api.py`)
  and the full frontend build (`npm run build`) remain reviewed-but-unbooted.
  **Before a real demo, run `pip install -r backend/requirements.txt &&
  pytest tests -v` and `npm install && npm run build`, and treat both as
  required pre-demo gates, not optional extras.**
- Vulnerability "before" state is approximated (see `docs/architecture.md`
  assumptions) rather than sourced from a dedicated point-in-time snapshot
  table.
- The additive risk formula does not model multiplicative interaction
  effects between components — documented in `docs/risk_methodology.md`
  and `docs/error_analysis.md`.
- Auth is a demo-grade JWT scheme, not a production identity system.
- Database-connection failure at startup is not gracefully handled in this
  prototype (see `docs/failure_mode_analysis.md`).
- The role/authorization model intentionally shares evidence-level
  endpoints (assets, vulnerabilities, incidents, controls, remediation,
  data-quality) across all three authenticated roles rather than scoping
  each to exactly one role — this is a documented design trade-off (see
  `docs/architecture.md` "Authorization model"), not an oversight, made to
  support the required cross-role drill-down demo flow.
- The attribution/confounding-detection logic in
  `compute_attribution()` was reviewed carefully but could not be exercised
  against a live database in this sandbox (it requires SQLAlchemy +a
  populated DB) — treat it as reviewed, not executed, until run once
  dependencies are installed.

## 26. Future improvements

- Multiplicative/interaction-aware risk modeling
- Real telemetry source integrations (EDR/SIEM APIs) behind the same
  ingestion/validation contract
- Calibrate formula weights against real historical incident/loss data
- Expand the optional LLM explanation layer with per-sentence evidence
  citations
- Add point-in-time vulnerability snapshots for more precise before/after
  control-effectiveness comparisons
- Graceful DB-connection-failure handling with a health/readiness endpoint
