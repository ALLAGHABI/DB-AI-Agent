import pytest

from app.connections_store import ConnectionsStore
from app.errors import AppError, NotFoundError
from app.history import QueryHistory


# ---------- سجل الاستعلامات ----------

def test_history_add_and_list_newest_first(tmp_path):
    h = QueryHistory(str(tmp_path))
    h.add(sql="SELECT 1", sql_class="read", source="editor")
    h.add(sql="SELECT 2", sql_class="read", source="nl",
          request="كم العدد؟", model="ollama/gemma3:4b", rows=5)
    items = h.list()
    assert len(items) == 2
    assert items[0]["sql"] == "SELECT 2"
    assert items[0]["request"] == "كم العدد؟"
    assert items[0]["rows"] == 5
    assert items[0]["favorite"] is False
    assert items[0]["created_at"]


def test_history_favorite_and_filter(tmp_path):
    h = QueryHistory(str(tmp_path))
    first = h.add(sql="SELECT 1", sql_class="read", source="editor")
    h.add(sql="SELECT 2", sql_class="read", source="editor")
    h.set_favorite(first, True)
    favs = h.list(favorites_only=True)
    assert len(favs) == 1 and favs[0]["id"] == first and favs[0]["favorite"] is True


def test_history_clear_keeps_favorites(tmp_path):
    h = QueryHistory(str(tmp_path))
    fav = h.add(sql="SELECT 1", sql_class="read", source="editor")
    h.add(sql="SELECT 2", sql_class="read", source="editor")
    h.set_favorite(fav, True)
    h.clear(keep_favorites=True)
    remaining = h.list()
    assert len(remaining) == 1 and remaining[0]["id"] == fav


def test_history_delete_and_missing(tmp_path):
    h = QueryHistory(str(tmp_path))
    entry = h.add(sql="SELECT 1", sql_class="read", source="editor")
    h.delete(entry)
    assert h.list() == []
    with pytest.raises(NotFoundError) as e:
        h.delete(entry)
    assert e.value.code == "historyEntryMissing"


def test_history_trims_but_never_favorites(tmp_path, monkeypatch):
    import app.history as hist_mod
    monkeypatch.setattr(hist_mod, "MAX_ENTRIES", 3)
    h = QueryHistory(str(tmp_path))
    fav = h.add(sql="KEEP ME", sql_class="read", source="editor")
    h.set_favorite(fav, True)
    for i in range(10):
        h.add(sql=f"SELECT {i}", sql_class="read", source="editor")
    items = h.list(limit=100)
    assert len(items) == 4                      # 3 عادية + المفضلة
    assert any(i["sql"] == "KEEP ME" for i in items)


# ---------- الاتصالات المحفوظة ----------

def test_connection_sqlite_roundtrip(tmp_path):
    c = ConnectionsStore(str(tmp_path))
    saved = c.add(name="متجري", type="sqlite", sqlite_file="data/sample_store.db")
    assert saved["name"] == "متجري" and saved["has_password"] is False
    assert c.build_url(saved["id"]) == "sqlite:///data/sample_store.db"


def test_connection_password_encrypted_and_never_listed(tmp_path):
    c = ConnectionsStore(str(tmp_path))
    saved = c.add(name="prod", type="postgresql", host="db.local",
                  database="shop", username="admin", password="s3cret")
    listed = c.list()[0]
    assert "password" not in listed and listed["has_password"] is True
    assert "s3cret" not in (tmp_path / "connections.json").read_text()
    url = c.build_url(saved["id"])
    assert url == "postgresql+psycopg://admin:s3cret@db.local:5432/shop"


def test_connection_validation(tmp_path):
    c = ConnectionsStore(str(tmp_path))
    with pytest.raises(AppError) as e:
        c.add(name="", type="sqlite", sqlite_file="x.db")
    assert e.value.code == "connectionNameRequired"
    with pytest.raises(AppError) as e:
        c.add(name="x", type="sqlite", sqlite_file="")
    assert e.value.code == "sqlitePathRequired"
    with pytest.raises(AppError) as e:
        c.add(name="x", type="mysql", host="", database="", username="")
    assert e.value.code == "serverFieldsRequired"


def test_connection_delete(tmp_path):
    c = ConnectionsStore(str(tmp_path))
    saved = c.add(name="tmp", type="sqlite", sqlite_file="a.db")
    c.delete(saved["id"])
    assert c.list() == []
    with pytest.raises(NotFoundError):
        c.build_url(saved["id"])
