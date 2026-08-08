import urllib.parse
from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response as FileResponse
from pydantic import BaseModel

from ..agent.nl2sql import build_prompt, extract_sql
from ..db import transfer
from ..db.manager import ExecutionBlocked
from ..db.sql_guard import classify
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
    except Exception as e:
        raise HTTPException(400, detail=str(e))
    return {"success": True, "dialect": state.db.dialect,
            "tables": [t["name"] for t in state.db.schema_tables()]}


@router.get("/db/schema")
def db_schema():
    if not state.db.is_connected:
        raise HTTPException(400, detail="لا يوجد اتصال")
    return {"tables": state.db.schema_tables()}


def _require_connection():
    if not state.db.is_connected:
        raise HTTPException(400, detail="لا يوجد اتصال")


@router.get("/db/table/{table}/rows")
def table_rows(table: str, limit: int = 50, offset: int = 0,
               order_by: str | None = None, dir: str = "asc"):
    _require_connection()
    try:
        return state.db.browse_rows(table, limit=limit, offset=offset,
                                    order_by=order_by, direction=dir)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


class InsertIn(BaseModel):
    values: dict


@router.post("/db/table/{table}/rows")
def table_insert(table: str, body: InsertIn):
    _require_connection()
    try:
        pk = state.db.insert_row(table, body.values)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(400, detail=f"فشل الإدراج: {e}")
    return {"success": True, "pk": pk}


class UpdateIn(BaseModel):
    pk: dict
    values: dict


@router.put("/db/table/{table}/rows")
def table_update(table: str, body: UpdateIn):
    _require_connection()
    try:
        affected = state.db.update_row(table, body.pk, body.values)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(400, detail=f"فشل التعديل: {e}")
    return {"success": True, "affected": affected}


class DeleteIn(BaseModel):
    pk: dict


@router.delete("/db/table/{table}/rows")
def table_delete(table: str, body: DeleteIn):
    _require_connection()
    try:
        affected = state.db.delete_row(table, body.pk)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(400, detail=f"فشل الحذف: {e}")
    return {"success": True, "affected": affected}


@router.post("/db/import")
async def db_import(file: UploadFile = File(...), table: str = Form(...),
                    mode: str = Form("create")):
    _require_connection()
    data = await file.read()
    try:
        df = transfer.read_upload(file.filename or "upload", data)
        inserted = transfer.import_df(state.db, df, table, mode)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(400, detail=f"فشل الاستيراد: {e}")
    return {"success": True, "inserted": inserted, "table": table}


@router.get("/db/table/{table}/export")
def db_export(table: str, format: str = "csv"):
    _require_connection()
    try:
        data, media_type, filename = transfer.export_table(state.db, table, format)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    quoted = urllib.parse.quote(filename)
    return FileResponse(content=data, media_type=media_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"})


@router.get("/db/backup")
def db_backup():
    _require_connection()
    try:
        data = transfer.sqlite_backup(state.db)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    return FileResponse(content=data, media_type="application/vnd.sqlite3", headers={
        "Content-Disposition": "attachment; filename=backup.db"})


class ExecuteIn(BaseModel):
    sql: str
    confirm_write: bool = False


@router.post("/db/execute")
def db_execute(body: ExecuteIn):
    if not state.db.is_connected:
        raise HTTPException(400, detail="لا يوجد اتصال")
    try:
        res = state.db.execute(body.sql, confirm_write=body.confirm_write)
    except ExecutionBlocked as e:
        raise HTTPException(409, detail={
            "sql_class": e.sql_class.value,
            "sql": e.sql,
            "message": "هذا الاستعلام يعدّل البيانات — يتطلب تأكيداً صريحاً",
        })
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(400, detail=f"خطأ في التنفيذ: {e}")
    return asdict(res)


# ---------- NL → SQL ----------

class GenerateIn(BaseModel):
    request: str
    provider: str
    model: str


@router.post("/query/generate")
async def query_generate(body: GenerateIn):
    if not state.db.is_connected:
        raise HTTPException(400, detail="اتصل بقاعدة البيانات أولاً")
    try:
        provider = state.provider_by_id(body.provider)
    except KeyError:
        raise HTTPException(400, detail=f"مزود غير معروف: {body.provider}")
    system = build_prompt(state.db.schema_summary(), state.db.dialect or "sql")
    try:
        result = await provider.chat(body.model, system, body.request)
    except Exception as e:
        raise HTTPException(502, detail=f"فشل توليد الاستعلام: {e}")
    sql = extract_sql(result.text)
    try:
        sql_class = classify(sql, state.db.dialect).value
    except ValueError as e:
        raise HTTPException(422, detail={"sql": sql, "message": str(e)})
    return {"sql": sql, "sql_class": sql_class,
            "provider": provider.id, "model": body.model,
            "is_local": provider.is_local}
