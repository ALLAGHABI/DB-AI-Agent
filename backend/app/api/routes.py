import urllib.parse
from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response as FileResponse
from pydantic import BaseModel

from ..agent.nl2sql import build_prompt, extract_sql
from ..db import transfer
from ..db.manager import ExecutionBlocked
from ..db.sql_guard import classify
from ..errors import AppError, http_error
from ..state import state

router = APIRouter(prefix="/api")


# ---------- LLM ----------

@router.get("/llm/providers")
async def llm_providers():
    return [asdict(await p.status()) for p in state.providers()]


# ---------- Settings ----------

class SecretsIn(BaseModel):
    openrouter_api_key: str | None = None
    openai_compat_url: str | None = None


@router.post("/settings/secrets")
def set_secrets(body: SecretsIn):
    if body.openrouter_api_key is not None:
        state.secrets.set("openrouter_api_key", body.openrouter_api_key)
    if body.openai_compat_url is not None:
        state.secrets.set("openai_compat_url", body.openai_compat_url)
    return {"success": True}


@router.get("/settings")
def get_settings_view():
    return {
        "has_openrouter_api_key": state.secrets.has("openrouter_api_key"),
        "openai_compat_url": state.secrets.get("openai_compat_url"),  # عنوان، ليس سراً
    }


# ---------- Database ----------

@router.get("/status")
def get_status():
    """حالة الجلسة — تسمح للواجهة باستعادة الاتصال بعد إعادة التحميل."""
    if not state.db.is_connected:
        return {"db_connected": False, "dialect": None, "tables": []}
    return {
        "db_connected": True,
        "dialect": state.db.dialect,
        "tables": [t["name"] for t in state.db.schema_tables()],
    }


class ConnectIn(BaseModel):
    url: str


@router.post("/db/connect")
def db_connect(body: ConnectIn):
    try:
        state.db.connect(body.url)
    except AppError:
        raise
    except Exception as e:
        raise http_error("connectFailed", detail=str(e))
    return {"success": True, "dialect": state.db.dialect,
            "tables": [t["name"] for t in state.db.schema_tables()]}


@router.get("/db/schema")
def db_schema():
    if not state.db.is_connected:
        raise http_error("notConnected")
    return {"tables": state.db.schema_tables()}


def _require_connection():
    if not state.db.is_connected:
        raise http_error("notConnected")


@router.get("/db/table/{table}/rows")
def table_rows(table: str, limit: int = 50, offset: int = 0,
               order_by: str | None = None, dir: str = "asc"):
    _require_connection()
    return state.db.browse_rows(table, limit=limit, offset=offset,
                                order_by=order_by, direction=dir)


class InsertIn(BaseModel):
    values: dict


@router.post("/db/table/{table}/rows")
def table_insert(table: str, body: InsertIn):
    _require_connection()
    try:
        pk = state.db.insert_row(table, body.values)
    except AppError:
        raise
    except Exception as e:
        raise http_error("insertFailed", detail=str(e))
    return {"success": True, "pk": pk}


class UpdateIn(BaseModel):
    pk: dict
    values: dict


@router.put("/db/table/{table}/rows")
def table_update(table: str, body: UpdateIn):
    _require_connection()
    try:
        affected = state.db.update_row(table, body.pk, body.values)
    except AppError:
        raise
    except Exception as e:
        raise http_error("updateFailed", detail=str(e))
    return {"success": True, "affected": affected}


class DeleteIn(BaseModel):
    pk: dict


@router.delete("/db/table/{table}/rows")
def table_delete(table: str, body: DeleteIn):
    _require_connection()
    try:
        affected = state.db.delete_row(table, body.pk)
    except AppError:
        raise
    except Exception as e:
        raise http_error("deleteFailed", detail=str(e))
    return {"success": True, "affected": affected}


@router.post("/db/import")
async def db_import(file: UploadFile = File(...), table: str = Form(...),
                    mode: str = Form("create")):
    _require_connection()
    data = await file.read()
    try:
        sheets = transfer.read_upload(file.filename or "upload", data)
        df = next(iter(sheets.values()))        # الاستيراد يستهدف جدولاً واحداً
        inserted = transfer.import_df(state.db, df, table, mode)
    except AppError:
        raise
    except Exception as e:
        raise http_error("importFailed", detail=str(e))
    return {"success": True, "inserted": inserted, "table": table}


@router.get("/db/table/{table}/export")
def db_export(table: str, format: str = "csv"):
    _require_connection()
    data, media_type, filename = transfer.export_table(state.db, table, format)
    quoted = urllib.parse.quote(filename)
    return FileResponse(content=data, media_type=media_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"})


@router.get("/db/backup")
def db_backup():
    _require_connection()
    data = transfer.sqlite_backup(state.db)
    return FileResponse(content=data, media_type="application/vnd.sqlite3", headers={
        "Content-Disposition": "attachment; filename=backup.db"})


class ExecuteIn(BaseModel):
    sql: str
    confirm_write: bool = False
    source: str = "editor"            # "editor" | "nl"
    request: str | None = None        # نص الطلب الطبيعي إن وُجد
    model: str | None = None


@router.post("/db/execute")
def db_execute(body: ExecuteIn):
    if not state.db.is_connected:
        raise http_error("notConnected")

    def record(sql_class: str, rows: int, success: bool) -> None:
        try:
            state.history.add(sql=body.sql, sql_class=sql_class, source=body.source,
                              request=body.request, model=body.model,
                              rows=rows, success=success)
        except Exception as e:                 # السجل مساعد — لا يُفشل الاستعلام
            print(f"history write failed: {e}")

    try:
        res = state.db.execute(body.sql, confirm_write=body.confirm_write)
    except ExecutionBlocked:
        raise                                  # لم يُنفَّذ بعد — لا يُسجَّل
    except AppError:
        record("unknown", 0, False)
        raise
    except Exception as e:
        record("unknown", 0, False)
        raise http_error("executeFailed", detail=str(e))

    record("read" if res.kind == "rows" else "write",
           len(res.rows) if res.kind == "rows" else res.affected, True)
    return asdict(res)


# ---------- NL → SQL ----------

class GenerateIn(BaseModel):
    request: str
    provider: str
    model: str


@router.post("/query/generate")
async def query_generate(body: GenerateIn):
    if not state.db.is_connected:
        raise http_error("notConnected")
    try:
        provider = state.provider_by_id(body.provider)
    except KeyError:
        raise http_error("unknownProvider", provider=body.provider)
    system = build_prompt(state.db.schema_summary(), state.db.dialect or "sql")
    try:
        result = await provider.chat(body.model, system, body.request)
    except Exception as e:
        raise http_error("generateFailed", 502, detail=str(e))
    sql = extract_sql(result.text)
    try:
        sql_class = classify(sql, state.db.dialect).value
    except AppError as e:
        raise HTTPException(422, detail={**e.to_detail(), "sql": sql})
    return {"sql": sql, "sql_class": sql_class,
            "provider": provider.id, "model": body.model,
            "is_local": provider.is_local}


# ---------- سجل الاستعلامات ----------

@router.get("/history")
def history_list(limit: int = 50, favorites_only: bool = False):
    return state.history.list(limit=limit, favorites_only=favorites_only)


class FavoriteIn(BaseModel):
    favorite: bool


@router.patch("/history/{entry_id}")
def history_favorite(entry_id: int, body: FavoriteIn):
    state.history.set_favorite(entry_id, body.favorite)
    return {"success": True}


@router.delete("/history/{entry_id}")
def history_delete(entry_id: int):
    state.history.delete(entry_id)
    return {"success": True}


@router.delete("/history")
def history_clear(keep_favorites: bool = True):
    removed = state.history.clear(keep_favorites=keep_favorites)
    return {"success": True, "removed": removed}


# ---------- الاتصالات المحفوظة ----------

@router.get("/connections")
def connections_list():
    return state.connections.list()


class ConnectionIn(BaseModel):
    name: str
    type: str
    sqlite_file: str = ""
    host: str = ""
    port: str = ""
    database: str = ""
    username: str = ""
    password: str = ""


@router.post("/connections")
def connections_add(body: ConnectionIn):
    return state.connections.add(**body.model_dump())


@router.delete("/connections/{conn_id}")
def connections_delete(conn_id: str):
    state.connections.delete(conn_id)
    return {"success": True}


@router.post("/connections/{conn_id}/connect")
def connections_connect(conn_id: str):
    url = state.connections.build_url(conn_id)
    try:
        state.db.connect(url)
    except AppError:
        raise
    except Exception as e:
        raise http_error("connectFailed", detail=str(e))
    return {"success": True, "dialect": state.db.dialect,
            "tables": [t["name"] for t in state.db.schema_tables()]}
