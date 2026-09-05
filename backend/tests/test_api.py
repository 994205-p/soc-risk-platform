"""
API integration tests. Requires backend deps installed (see requirements.txt).
Run with: pytest backend/tests -v
"""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_success(client):
    r = client.post("/api/auth/login", json={"username": "manager", "password": "demo1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "management"
    assert "access_token" in body


def test_login_failure(client):
    r = client.post("/api/auth/login", json={"username": "manager", "password": "wrong"})
    assert r.status_code == 401


def test_current_risk(client):
    r = client.get("/api/risk/current")
    assert r.status_code == 200
    body = r.json()
    assert body["risk_score"] is not None
    assert 0 <= body["risk_score"] <= 100
    assert body["explanation"]


def test_management_dashboard(client):
    r = client.get("/api/dashboard/management")
    assert r.status_code == 200
    body = r.json()
    assert "kpis" in body
    assert "control_effectiveness_summary" in body


def test_controls_list_and_effectiveness(client):
    r = client.get("/api/controls")
    assert r.status_code == 200
    controls = r.json()
    assert len(controls) > 0
    cid = controls[0]["control_id"]
    r2 = client.get(f"/api/controls/{cid}/effectiveness")
    assert r2.status_code == 200
    eff = r2.json()
    assert "risk_reduction_pct" in eff


def test_asset_evidence_drilldown(client):
    r = client.get("/api/assets")
    assets = r.json()
    assert len(assets) > 0
    asset_id = assets[0]["asset_id"]
    r2 = client.get(f"/api/assets/{asset_id}/evidence")
    assert r2.status_code == 200
    body = r2.json()
    assert body["asset"]["asset_id"] == asset_id
    assert "vulnerabilities" in body and "controls" in body


def test_data_quality_endpoint_reports_injected_issues(client):
    r = client.get("/api/data-quality")
    assert r.status_code == 200
    body = r.json()
    assert body["total_events"] > 0  # generator deliberately injects issues


def test_legacy_migration_and_rollback_cycle(client):
    status_before = client.get("/api/legacy/status").json()
    assert status_before["not_migrated"] > 0

    migrate_resp = client.post("/api/legacy/migrate", json={}).json()
    assert migrate_resp["migrated_count"] > 0

    status_after_migrate = client.get("/api/legacy/status").json()
    assert status_after_migrate["migrated"] > 0

    rollback_resp = client.post("/api/legacy/rollback", json={"reason": "test rollback"}).json()
    assert rollback_resp["rolled_back_count"] > 0

    status_after_rollback = client.get("/api/legacy/status").json()
    assert status_after_rollback["rolled_back"] > 0

    audit = client.get("/api/legacy/audit-log").json()
    actions = {a["action"] for a in audit}
    assert "MIGRATE" in actions and "ROLLBACK" in actions


def test_asset_not_found_returns_404(client):
    r = client.get("/api/risk/assets/DOES-NOT-EXIST")
    assert r.status_code == 404
