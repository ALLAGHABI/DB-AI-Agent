from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agent.nl2sql import build_prompt, extract_sql
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
