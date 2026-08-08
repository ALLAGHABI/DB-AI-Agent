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
            try:
                pks = insp.get_pk_constraint(table).get("constrained_columns", [])
            except Exception:
                pks = []
            try:
                fks = [
                    {
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"],
                    }
                    for fk in insp.get_foreign_keys(table)
                ]
            except Exception:
                fks = []
            with self.engine.connect() as conn:
                count = conn.execute(
                    text(f"SELECT COUNT(*) FROM {self._quote(table)}")
                ).scalar_one()
            out.append({
                "name": table,
                "columns": [
                    {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]}
                    for c in insp.get_columns(table)
                ],
                "primary_keys": pks,
                "foreign_keys": fks,
                "row_count": count,
            })
        return out

    def _quote(self, ident: str) -> str:
        return self.engine.dialect.identifier_preparer.quote(ident)

    # ---------- تصفح وتحرير الجداول (أسماء مُتحقق منها ضد المخطط دائماً) ----------

    def _table_meta(self, table: str) -> dict:
        insp = inspect(self.engine)
        if table not in insp.get_table_names():
            raise LookupError(f"جدول غير موجود: {table}")
        cols = [c["name"] for c in insp.get_columns(table)]
        try:
            pks = insp.get_pk_constraint(table).get("constrained_columns", [])
        except Exception:
            pks = []
        return {"columns": cols, "primary_keys": pks}

    def browse_rows(self, table: str, limit: int = 50, offset: int = 0,
                    order_by: str | None = None, direction: str = "asc") -> dict:
        meta = self._table_meta(table)
        if order_by is not None and order_by not in meta["columns"]:
            raise ValueError(f"عمود غير معروف للفرز: {order_by}")
        if direction not in ("asc", "desc"):
            raise ValueError("اتجاه الفرز يجب أن يكون asc أو desc")
        qt = self._quote(table)
        order_sql = f" ORDER BY {self._quote(order_by)} {direction.upper()}" if order_by else ""
        with self.engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {qt}")).scalar_one()
            result = conn.execute(
                text(f"SELECT * FROM {qt}{order_sql} LIMIT :l OFFSET :o"),
                {"l": min(limit, settings.row_limit), "o": max(offset, 0)},
            )
            return {
                "columns": list(result.keys()),
                "rows": [list(r) for r in result.fetchall()],
                "total": total,
                "primary_keys": meta["primary_keys"],
            }

    def _validate_columns(self, meta: dict, values: dict, what: str) -> None:
        unknown = set(values) - set(meta["columns"])
        if unknown:
            raise ValueError(f"أعمدة غير معروفة في {what}: {', '.join(sorted(unknown))}")
        if not values:
            raise ValueError(f"{what} فارغ")

    def insert_row(self, table: str, values: dict) -> dict:
        meta = self._table_meta(table)
        self._validate_columns(meta, values, "القيم")
        cols = ", ".join(self._quote(c) for c in values)
        binds = ", ".join(f":{c}" for c in values)
        with self.engine.connect() as conn:
            result = conn.execute(
                text(f"INSERT INTO {self._quote(table)} ({cols}) VALUES ({binds})"), values)
            conn.commit()
            pk: dict = {}
            if len(meta["primary_keys"]) == 1:
                pk_col = meta["primary_keys"][0]
                pk[pk_col] = values.get(pk_col,
                                        getattr(result, "lastrowid", None))
            return pk

    def _pk_where(self, meta: dict, pk: dict) -> str:
        if not meta["primary_keys"]:
            raise ValueError("الجدول بلا مفتاح أساسي — التحرير غير مدعوم")
        if set(pk) != set(meta["primary_keys"]):
            raise ValueError("يجب تحديد قيم المفتاح الأساسي كاملة")
        return " AND ".join(f"{self._quote(c)} = :pk_{c}" for c in pk)

    def update_row(self, table: str, pk: dict, values: dict) -> int:
        meta = self._table_meta(table)
        self._validate_columns(meta, values, "القيم")
        where = self._pk_where(meta, pk)
        sets = ", ".join(f"{self._quote(c)} = :{c}" for c in values)
        params = {**values, **{f"pk_{c}": v for c, v in pk.items()}}
        with self.engine.connect() as conn:
            result = conn.execute(
                text(f"UPDATE {self._quote(table)} SET {sets} WHERE {where}"), params)
            conn.commit()
            return result.rowcount

    def delete_row(self, table: str, pk: dict) -> int:
        meta = self._table_meta(table)
        where = self._pk_where(meta, pk)
        with self.engine.connect() as conn:
            result = conn.execute(
                text(f"DELETE FROM {self._quote(table)} WHERE {where}"),
                {f"pk_{c}": v for c, v in pk.items()})
            conn.commit()
            return result.rowcount

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
