from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.utils.auth import ensure_demo_users
from app.services.ingestion import ingest_all
from app.models.models import Asset  # ensures models are registered on Base

from app.api import auth, risk, controls, records, data_quality, legacy, assets, dashboards

app = FastAPI(
    title="SOC Control Effectiveness & Business Risk Platform",
    description="Transforms SOC telemetry and technical findings into explainable business risk measurements.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(risk.router)
app.include_router(controls.router)
app.include_router(records.router)
app.include_router(data_quality.router)
app.include_router(legacy.router)
app.include_router(assets.router)
app.include_router(dashboards.router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_users(db)
        # Auto-ingest on first run only (idempotent-ish: skips if assets already loaded)
        if db.query(Asset).count() == 0:
            summary = ingest_all(db)
            print(f"[startup] Ingested data: {summary}")
        ensure_demo_users(db)  # roles exist post-ingest -> (re)create demo users
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "SOC Risk Platform API. See /docs for interactive API documentation."}
