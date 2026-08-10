"""استيراد وتصدير البيانات والنسخ الاحتياطي."""
import io
import re
import sqlite3
import tempfile

import pandas as pd

from .manager import DatabaseManager
from ..errors import AppError

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


MAX_HEADER_SCAN = 6

# «ال» وحدها ليست كلمة عربية — فهي أداة تعريف انفصلت عن كلمتها بكسر سطر
_DANGLING_AL = re.compile(r"(?<![\w؀-ۿ])ال\s+(?=[؀-ۿ])")


def _pick_header_row(preview: pd.DataFrame) -> int:
    """يختار صف العناوين — ملفات Excel الواقعية تبدأ بعناوين وشعارات وصفوف فارغة."""
    best, best_score = 0, -1.0
    for i in range(min(MAX_HEADER_SCAN, len(preview))):
        row = preview.iloc[i]
        filled = row.notna().sum()
        if not filled:
            continue
        texts = sum(1 for v in row if isinstance(v, str) and v.strip())
        unique = row.dropna().astype(str).nunique()
        score = filled + texts * 0.5 + unique * 0.5
        if score > best_score:
            best, best_score = i, score
    return best


def _clean_header(name) -> str:
    """اسم عمود صالح للعرض — خلايا Excel تحمل أسطراً ومسافات مضاعفة.

    «القيمة في ال\nشهر» تصير «القيمة في الشهر»، و«وحدة  القياس» تصير
    «وحدة القياس» — وإلا ظهر الاسم مبتوراً أو مشوّهاً في كل عنوان بالتقرير.
    """
    text = re.sub(r"\s+", " ", str(name)).strip()
    return _DANGLING_AL.sub("ال", text)      # «في ال ساعة» ⇒ «في الساعة»


def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    df.columns = [_clean_header(c) for c in df.columns]
    keep = [c for c in df.columns if not c.lower().startswith("unnamed")]
    return df[keep] if keep else df


def read_upload(filename: str, data: bytes) -> dict:
    """يقرأ الملف ويعيد {اسم الورقة: إطار} — ملفات Excel قد تحوي عدة أوراق."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError("fileTooLarge", limit="20MB")
    name = filename.lower()
    base = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0] or "data"

    if name.endswith(".csv"):
        return {base: _clean_frame(pd.read_csv(io.BytesIO(data)))}
    if name.endswith(".json"):
        return {base: _clean_frame(pd.read_json(io.BytesIO(data)))}
    if name.endswith((".xlsx", ".xls")):
        book = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None)
        sheets: dict[str, pd.DataFrame] = {}
        for sheet, raw in book.items():
            if raw.empty:
                continue
            header = _pick_header_row(raw.head(MAX_HEADER_SCAN))
            df = pd.read_excel(io.BytesIO(data), sheet_name=sheet, header=header)
            df = _clean_frame(df)
            if not df.empty and len(df.columns):
                sheets[str(sheet).strip() or f"sheet{len(sheets) + 1}"] = df
        if not sheets:
            raise AppError("emptyFile")
        return sheets
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
