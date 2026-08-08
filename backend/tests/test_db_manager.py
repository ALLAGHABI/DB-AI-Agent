import sqlite3

import pytest

from app.db.manager import DatabaseManager, ExecutionBlocked


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "t.db"
    con = sqlite3.connect(p)
    con.executescript(
        "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);"
        "INSERT INTO customers (name) VALUES ('أحمد'), ('سارة');"
    )
    con.commit(); con.close()
    return str(p)


def test_connect_and_schema(db_path):
    m = DatabaseManager()
    m.connect(f"sqlite:///{db_path}")
    schema = m.schema_summary()
    assert "customers" in schema
    assert "name" in schema


def test_select_returns_rows_with_auto_limit(db_path):
    m = DatabaseManager(); m.connect(f"sqlite:///{db_path}")
    res = m.execute("SELECT * FROM customers")
    assert res.kind == "rows"
    assert res.columns == ["id", "name"]
    assert len(res.rows) == 2
    assert res.applied_sql.upper().count("LIMIT") == 1


def test_cte_select_returns_rows(db_path):        # v1 bug regression test
    m = DatabaseManager(); m.connect(f"sqlite:///{db_path}")
    res = m.execute("WITH c AS (SELECT * FROM customers) SELECT count(*) AS n FROM c")
    assert res.kind == "rows" and res.rows[0][0] == 2


def test_write_blocked_without_confirm(db_path):
    m = DatabaseManager(); m.connect(f"sqlite:///{db_path}")
    with pytest.raises(ExecutionBlocked):
        m.execute("DELETE FROM customers")
    # لم يُحذف شيء
    assert len(m.execute("SELECT * FROM customers").rows) == 2


def test_write_executes_with_confirm(db_path):
    m = DatabaseManager(); m.connect(f"sqlite:///{db_path}")
    res = m.execute("DELETE FROM customers WHERE name='سارة'", confirm_write=True)
    assert res.kind == "affected" and res.affected == 1


def test_sqlite_missing_file_rejected(tmp_path):
    """يجب رفض ملف SQLite غير موجود بدل إنشاء قاعدة فارغة بصمت."""
    m = DatabaseManager()
    missing = tmp_path / "nope.db"
    with pytest.raises(FileNotFoundError):
        m.connect(f"sqlite:///{missing}")
    assert not missing.exists()          # لم يُنشأ ملف فارغ
    assert m.is_connected is False


def test_sqlite_relative_path_resolved_from_search_paths(db_path, tmp_path, monkeypatch):
    """المسار النسبي يُحل عبر مسارات البحث (مجلد التشغيل ثم جذر المشروع)."""
    import os
    import shutil
    root = tmp_path / "repo"; (root / "data").mkdir(parents=True)
    shutil.copy(db_path, root / "data" / "store.db")
    workdir = root / "backend"; workdir.mkdir()
    monkeypatch.chdir(workdir)
    m = DatabaseManager()
    m.connect("sqlite:///data/store.db")   # موجود في ../data نسبةً لمجلد التشغيل
    assert m.is_connected
    assert "customers" in m.schema_summary()
