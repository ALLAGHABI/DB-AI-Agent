import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import create_engine, inspect, text

from ..config import settings
from .sql_guard import SqlClass, classify, ensure_limit

_DIALECTS = {"sqlite": "sqlite", "mysql": "mysql", "postgresql": "postgres"}


def _resolve_sqlite_url(url: str) -> str:
    """يتحقق من وجود ملف SQLite ويحل المسارات النسبية.

    SQLAlchemy ينشئ ملفاً فارغاً بصمت إن لم يكن موجوداً — نرفض ذلك،
    ونبحث عن المسار النسبي في مجلد التشغيل ثم في المجلد الأب (جذر المشروع).
    """
    path = url[len("sqlite:///"):]
    if os.path.isabs(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"ملف قاعدة البيانات غير موجود: {path}")
        return url
    for base in (os.getcwd(), os.path.dirname(os.getcwd())):
        candidate = os.path.join(base, path)
        if os.path.exists(candidate):
            return f"sqlite:///{os.path.abspath(candidate)}"
    raise FileNotFoundError(f"ملف قاعدة البيانات غير موجود: {path}")


class ExecutionBlocked(Exception):
    """استعلام معدِّل بدون تأكيد صريح."""

    def __init__(self, sql_class: SqlClass, sql: str):
        self.sql_class = sql_class
        self.sql = sql
        super().__init__(f"{sql_class.value} query requires confirmation")


@dataclass
class ExecResult:
    kind: str                       # "rows" | "affected"
    applied_sql: str
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    affected: int = 0


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.dialect: str | None = None

    @property
    def is_connected(self) -> bool:
        return self.engine is not None

    def connect(self, url: str) -> None:
        if url.startswith("sqlite:///"):
            url = _resolve_sqlite_url(url)
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        self.engine = engine
        self.dialect = _DIALECTS.get(engine.dialect.name, engine.dialect.name)

    def disconnect(self) -> None:
        if self.engine:
            self.engine.dispose()
        self.engine = None
        self.dialect = None

    def schema_summary(self) -> str:
        """وصف نصي للمخطط يُمرر للنموذج."""
        insp = inspect(self.engine)
        parts: list[str] = []
        for table in insp.get_table_names():
            cols = ", ".join(
                f"{c['name']} {c['type']}" for c in insp.get_columns(table)
            )
            line = f"TABLE {table} ({cols})"
            for fk in insp.get_foreign_keys(table):
                line += (f"\n  FK: {','.join(fk['constrained_columns'])} -> "
                         f"{fk['referred_table']}({','.join(fk['referred_columns'])})")
            parts.append(line)
        return "\n".join(parts)

    def schema_tables(self) -> list[dict]:
        insp = inspect(self.engine)
        out = []
        for table in insp.get_table_names():
            out.append({
                "name": table,
                "columns": [
                    {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]}
                    for c in insp.get_columns(table)
                ],
            })
        return out

    def execute(self, sql: str, confirm_write: bool = False) -> ExecResult:
        if not self.is_connected:
            raise RuntimeError("لا يوجد اتصال بقاعدة البيانات")
        sql_class = classify(sql, self.dialect)
        if sql_class in (SqlClass.WRITE, SqlClass.DDL) and not confirm_write:
            raise ExecutionBlocked(sql_class, sql)
        applied = ensure_limit(sql, settings.row_limit, self.dialect)
        with self.engine.connect() as conn:
            result = conn.execute(text(applied))
            if sql_class == SqlClass.READ:
                cols = list(result.keys())
                rows = [list(r) for r in result.fetchall()]
                return ExecResult(kind="rows", applied_sql=applied,
                                  columns=cols, rows=rows)
            conn.commit()
            return ExecResult(kind="affected", applied_sql=applied,
                              affected=result.rowcount)
