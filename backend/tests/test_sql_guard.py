import pytest

from app.db.sql_guard import classify, ensure_limit, SqlClass


@pytest.mark.parametrize("sql,expected", [
    ("SELECT * FROM t", SqlClass.READ),
    ("WITH x AS (SELECT 1) SELECT * FROM x", SqlClass.READ),          # v1 bug: CTE
    ("  select 1", SqlClass.READ),
    ("INSERT INTO t VALUES (1)", SqlClass.WRITE),
    ("UPDATE t SET a=1", SqlClass.WRITE),
    ("WITH x AS (SELECT 1) DELETE FROM t", SqlClass.WRITE),           # v1 bug: CTE-DELETE
    ("DROP TABLE t", SqlClass.DDL),
    ("CREATE TABLE t (a int)", SqlClass.DDL),
    ("ALTER TABLE t ADD b int", SqlClass.DDL),
])
def test_classify(sql, expected):
    assert classify(sql) == expected


def test_classify_rejects_multiple_statements():
    with pytest.raises(ValueError):
        classify("SELECT 1; DROP TABLE t")


def test_classify_rejects_unparseable():
    with pytest.raises(ValueError):
        classify("NOT REALLY SQL AT ALL !!!")


def test_ensure_limit_adds_when_missing():
    out = ensure_limit("SELECT * FROM t", 500)
    assert "LIMIT 500" in out.upper()


def test_ensure_limit_keeps_existing():
    out = ensure_limit("SELECT * FROM t LIMIT 10", 500)
    assert "LIMIT 10" in out.upper() and "500" not in out


def test_ensure_limit_leaves_writes_alone():
    sql = "UPDATE t SET a=1"
    assert ensure_limit(sql, 500) == sql
