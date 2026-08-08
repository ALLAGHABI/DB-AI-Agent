import sqlite3

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

import app.state as state_mod
from app.main import app
from app.state import AppState


@pytest.fixture
def client(tmp_path, monkeypatch):
    # عزل الحالة وبيانات الأسرار في مجلد مؤقت
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    fresh = AppState()
    monkeypatch.setattr(state_mod, "state", fresh)
    # routes.py يستورد state بالاسم — نرقعه هناك أيضاً
    import app.api.routes as routes_mod
    monkeypatch.setattr(routes_mod, "state", fresh)
    return TestClient(app)


@pytest.fixture
def sample_db(tmp_path):
    p = tmp_path / "s.db"
    con = sqlite3.connect(p)
    con.executescript(
        "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL);"
        "INSERT INTO products (name, price) VALUES ('كتاب', 25), ('قلم', 3);"
    )
    con.commit(); con.close()
    return str(p)


@respx.mock
def test_providers_endpoint(client):
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "gemma3:1b"}]}))
    r = client.get("/api/llm/providers")
    assert r.status_code == 200
    data = {p["id"]: p for p in r.json()}
    assert data["ollama"]["available"] is True
    assert data["ollama"]["is_local"] is True
    assert data["openrouter"]["available"] is False   # لا مفتاح


def test_settings_never_returns_secrets(client):
    client.post("/api/settings/secrets", json={"openrouter_api_key": "sk-or-X"})
    r = client.get("/api/settings")
    body = r.text
    assert "sk-or-X" not in body
    assert r.json()["has_openrouter_api_key"] is True


def test_connect_and_execute_flow(client, sample_db):
    r = client.post("/api/db/connect", json={"url": f"sqlite:///{sample_db}"})
    assert r.json()["success"] is True
    # SQL مباشر (قراءة)
    r = client.post("/api/db/execute", json={"sql": "SELECT name FROM products"})
    assert r.status_code == 200
    assert r.json()["kind"] == "rows" and len(r.json()["rows"]) == 2
    # كتابة بدون تأكيد → 409 مع تصنيف
    r = client.post("/api/db/execute", json={"sql": "DELETE FROM products"})
    assert r.status_code == 409
    assert r.json()["detail"]["sql_class"] == "write"
    # كتابة مع تأكيد → تنفذ
    r = client.post("/api/db/execute",
                    json={"sql": "DELETE FROM products WHERE name='قلم'", "confirm_write": True})
    assert r.json()["affected"] == 1


@respx.mock
def test_nl_generate(client, sample_db):
    client.post("/api/db/connect", json={"url": f"sqlite:///{sample_db}"})
    respx.post("http://localhost:11434/api/chat").mock(return_value=Response(200, json={
        "message": {"content": "```sql\nSELECT count(*) FROM products\n```"}}))
    r = client.post("/api/query/generate", json={
        "request": "كم عدد المنتجات؟", "provider": "ollama", "model": "gemma3:1b"})
    body = r.json()
    assert body["sql"] == "SELECT count(*) FROM products"
    assert body["sql_class"] == "read"
    assert body["is_local"] is True
