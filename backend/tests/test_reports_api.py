import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

import app.state as state_mod
from app.main import app
from app.state import AppState

CSV = "city,amount\nالرياض,100\nجدة,200\nالرياض,150\n".encode()

FAKE_INSIGHTS = """## SUMMARY
البيانات تغطي 3 صفوف.
## FINDINGS
- الرياض الأكثر تكراراً
## RECOMMENDATIONS
- تابع جدة
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    fresh = AppState()
    monkeypatch.setattr(state_mod, "state", fresh)
    import app.api.reports_routes as rr
    import app.api.routes as routes_mod
    monkeypatch.setattr(routes_mod, "state", fresh)
    monkeypatch.setattr(rr, "state", fresh)
    return TestClient(app)


def _analyze(client):
    r = client.post("/api/reports/analyze",
                    files={"file": ("sales.csv", CSV, "text/csv")})
    assert r.status_code == 200
    return r.json()


def test_analyze_returns_profile_and_token(client):
    body = _analyze(client)
    assert body["token"]
    assert body["profile"]["overview"]["rows"] == 3


def test_analyze_rejects_garbage(client):
    r = client.post("/api/reports/analyze",
                    files={"file": ("x.exe", b"\x00\x01", "application/x")})
    assert r.status_code == 400


@respx.mock
def test_generate_and_archive_lifecycle(client):
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "gemma3:4b"}]}))
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=Response(200, json={"message": {"content": FAKE_INSIGHTS}}))

    token = _analyze(client)["token"]
    r = client.post("/api/reports/generate", json={
        "token": token, "title": "تقرير المبيعات", "template": "detailed",
        "language": "ar", "provider": "ollama", "model": "gemma3:4b"})
    assert r.status_code == 200, r.text
    meta = r.json()
    assert meta["is_local"] is True and meta["rows"] == 3

    # القائمة
    lst = client.get("/api/reports").json()
    assert lst[0]["id"] == meta["id"]

    # HTML
    html = client.get(f"/api/reports/{meta['id']}/html")
    assert html.status_code == 200
    assert "تقرير المبيعات" in html.text
    assert "الرياض الأكثر تكراراً" in html.text

    # Excel
    xlsx = client.get(f"/api/reports/{meta['id']}/xlsx")
    assert xlsx.content[:2] == b"PK"

    # حذف
    assert client.delete(f"/api/reports/{meta['id']}").json()["success"] is True
    assert client.get("/api/reports").json() == []


def test_generate_with_bad_token_404(client):
    r = client.post("/api/reports/generate", json={
        "token": "nope", "title": "x", "provider": "ollama", "model": "m"})
    assert r.status_code == 404
