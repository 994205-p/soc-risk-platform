import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "sqlite:///./test_soc_risk.db"

from app.database import Base, engine, SessionLocal
from app.services.ingestion import ingest_all
from app.utils.auth import ensure_demo_users


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    ensure_demo_users(db)
    ingest_all(db)
    ensure_demo_users(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_soc_risk.db"):
        os.remove("./test_soc_risk.db")


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
