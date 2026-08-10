"""استيراد وتصدير البيانات والنسخ الاحتياطي."""
import io
import sqlite3
import tempfile

import pandas as pd

from .manager import DatabaseManager
from ..errors import AppError

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def read_upload(filename: str, data: bytes) -> pd.DataFrame:
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError("fileTooLarge", limit="20MB")
    name = filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    if name.endswith(".json"):
        return pd.read_json(io.BytesIO(data))
    raise AppError("unsupportedFormat")


def import_df(manager: DatabaseManager, df: pd.DataFrame, table: str, mode: str) -> int:
    if mode not in ("create", "append"):
        raise AppError("badImportMode")
    existing = {t["name"] for t in manager.schema_tables()}
    if mode == "create" and table in existing:
        raise AppError("tableExists", table=table)
    if mode == "append" and table not in existing:
        raise AppError("tableMissingForAppend", table=table)
    df.to_sql(table, manager.engine, if_exists="append" if mode == "append" else "fail",
              index=False)
    return len(df)


def export_table(manager: DatabaseManager, table: str, fmt: str) -> tuple[bytes, str, str]:
    """يرجع (bytes, media_type, filename)."""
    meta = manager.browse_rows(table, limit=10**9, offset=0)
    df = pd.DataFrame(meta["rows"], columns=meta["columns"])
    if fmt == "csv":
        return (df.to_csv(index=False).encode("utf-8-sig"), "text/csv; charset=utf-8",
                f"{table}.csv")
    if fmt == "xlsx":
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        return (buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"{table}.xlsx")
    raise AppError("badExportFormat")


def sqlite_backup(manager: DatabaseManager) -> bytes:
    if manager.dialect != "sqlite":
        raise AppError("backupSqliteOnly")
    db_path = manager.engine.url.database
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(tmp.name)
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        tmp.seek(0)
        return tmp.read()
