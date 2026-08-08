import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.state as state_mod
from app.main import app
from app.state import AppState


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    fresh = AppState()
    monkeypatch.setattr(state_mod, "state", fresh)
    import app.api.routes as routes_mod
    monkeypatch.setattr(routes_mod, "state", fresh)
    return TestClient(app)


@pytest.fixture
def sample_db(tmp_path):
    p = tmp_path / "s.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE categories (id INTEGER PRIMARY KEY, title TEXT NOT NULL);
        CREATE TABLE products (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, price REAL,
            category_id INTEGER REFERENCES categories(id));
        INSERT INTO categories (title) VALUES ('كتب'), ('أدوات');
        INSERT INTO products (name, price, category_id)
        VALUES ('كتاب أ', 25, 1), ('كتاب ب', 30, 1), ('مفك', 12, 2);
    """)
    con.commit(); con.close()
    return str(p)


@pytest.fixture
def connected(client, sample_db):
    r = client.post("/api/db/connect", json={"url": f"sqlite:///{sample_db}"})
    assert r.json()["success"]
    return client


def test_status_reports_connection(connected):
    r = connected.get("/api/status")
    body = r.json()
    assert body["db_connected"] is True
    assert body["dialect"] == "sqlite"
    assert "products" in body["tables"]


def test_status_disconnected(client):
    body = client.get("/api/status").json()
    assert body["db_connected"] is False and body["tables"] == []


def test_schema_includes_pks_fks_and_counts(connected):
    tables = {t["name"]: t for t in connected.get("/api/db/schema").json()["tables"]}
    prod = tables["products"]
    assert prod["primary_keys"] == ["id"]
    assert prod["row_count"] == 3
    fk = prod["foreign_keys"][0]
    assert fk["referred_table"] == "categories"


def test_browse_rows_paginated_sorted(connected):
    r = connected.get("/api/db/table/products/rows",
                      params={"limit": 2, "offset": 0, "order_by": "price", "dir": "desc"})
    body = r.json()
    assert body["total"] == 3
    assert body["columns"][:2] == ["id", "name"]
    assert body["rows"][0][1] == "كتاب ب"          # الأغلى أولاً
    assert len(body["rows"]) == 2


def test_browse_rejects_unknown_table_and_column(connected):
    assert connected.get("/api/db/table/evil/rows").status_code == 404
    r = connected.get("/api/db/table/products/rows", params={"order_by": "nope"})
    assert r.status_code == 400


def test_insert_update_delete_row(connected):
    r = connected.post("/api/db/table/products/rows",
                       json={"values": {"name": "جديد", "price": 5, "category_id": 2}})
    assert r.json()["success"] is True
    rid = r.json()["pk"]["id"]

    r = connected.put("/api/db/table/products/rows",
                      json={"pk": {"id": rid}, "values": {"price": 7.5}})
    assert r.json()["affected"] == 1

    r = connected.request("DELETE", "/api/db/table/products/rows", json={"pk": {"id": rid}})
    assert r.json()["affected"] == 1
    assert connected.get("/api/db/table/products/rows").json()["total"] == 3


def test_update_requires_pk(connected):
    r = connected.put("/api/db/table/products/rows", json={"pk": {}, "values": {"price": 1}})
    assert r.status_code == 400


def test_insert_rejects_unknown_column(connected):
    r = connected.post("/api/db/table/products/rows",
                       json={"values": {"name": "x", "hack": 1}})
    assert r.status_code == 400
