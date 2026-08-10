"""مسارات استوديو التقارير."""
import asyncio
import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from ..db import transfer
from ..reports import exporter
from ..reports.analyzer import MAX_DATASETS, profile_datasets, profile_df
from ..reports.builder import build_report_html
from ..reports.insights import generate_insights
from ..reports.store import ReportStore
from ..config import settings
from ..errors import AppError, http_error
from ..state import state

router = APIRouter(prefix="/api/reports")


def _store() -> ReportStore:
    return ReportStore(settings.data_dir)


MAX_TABLE_ROWS = 100_000


class AnalyzeTablesIn(BaseModel):
    tables: list[str] = []          # فارغة = كل جداول القاعدة


@router.post("/analyze-table")
def analyze_tables(body: AnalyzeTablesIn):
    """تحليل جدول أو عدة جداول أو القاعدة كاملة — بلا تصدير ورفع يدوي."""
    if not state.db.is_connected:
        raise http_error("notConnected")
    import pandas as pd

    schema = state.db.schema_tables()
    known = [t["name"] for t in schema]
    wanted = body.tables or known
    unknown = [t for t in wanted if t not in known]
    if unknown:
        raise http_error("tableMissing", 404, table=unknown[0])
    if not wanted:
        raise http_error("noTablesToAnalyze")

    frames: dict[str, pd.DataFrame] = {}
    for name in wanted[:MAX_DATASETS]:
        data = state.db.browse_rows(name, limit=MAX_TABLE_ROWS, offset=0)
        frames[name] = pd.DataFrame(data["rows"], columns=data["columns"])

    if all(df.empty for df in frames.values()):
        raise http_error("emptyTable", table=wanted[0])

    # العلاقات بين الجداول المختارة فقط
    relationships = [
        {"from": f"{t['name']}.{','.join(fk['constrained_columns'])}",
         "to": f"{fk['referred_table']}.{','.join(fk['referred_columns'])}"}
        for t in schema if t["name"] in frames
        for fk in t["foreign_keys"] if fk["referred_table"] in frames
    ]

    if len(frames) == 1:
        name, df = next(iter(frames.items()))
        profile = profile_df(df)
        return {"token": _store().save_temp(df, name), "profile": profile}

    profile = profile_datasets(frames, relationships)
    source = state.db.dialect or "database"
    token = _store().save_temp(frames, source, relationships)
    return {"token": token, "profile": profile}


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    try:
        df = transfer.read_upload(file.filename or "upload", data)
    except AppError:
        raise
    except Exception as e:
        raise http_error("fileReadFailed", detail=str(e))
    if df.empty:
        raise http_error("emptyFile")
    profile = profile_df(df)
    token = _store().save_temp(df, file.filename or "upload")
    return {"token": token, "profile": profile}


class GenerateIn(BaseModel):
    token: str
    title: str
    template: str = "executive"          # executive | detailed | dashboard
    language: str = "ar"
    provider: str
    model: str


@router.post("/generate")
async def generate(body: GenerateIn):
    store = _store()
    saved = store.load_temp(body.token)
    frames, source_name = saved["frames"], saved["source_name"]
    if saved["kind"] == "multi":
        profile = profile_datasets(frames, saved.get("relationships"))
    else:
        profile = profile_df(next(iter(frames.values())))
    try:
        provider = state.provider_by_id(body.provider)
    except KeyError:
        raise http_error("unknownProvider", provider=body.provider)
    try:
        insights = await generate_insights(provider, body.model, profile, body.language)
    except Exception as e:
        raise http_error("insightsFailed", 502, detail=str(e))

    now = datetime.datetime.now().astimezone()
    created_at = now.strftime("%Y-%m-%d %H:%M")
    created_iso = now.isoformat()
    model_label = f"{provider.id}/{body.model}"
    html = build_report_html(
        title=body.title, profile=profile, insights=insights,
        language=body.language, variant=body.template,
        source_name=source_name, model_label=model_label,
        created_at=created_at)
    xlsx = exporter.to_xlsx(profile, insights, body.language)
    try:
        # Playwright السنكروني لا يعمل داخل حلقة asyncio — ننقله إلى thread
        pdf = await asyncio.to_thread(exporter.to_pdf, html)
    except Exception as e:
        print(f"PDF export failed: {e}")
        pdf = None

    meta = {
        "title": body.title, "template": body.template, "language": body.language,
        "source_name": source_name, "model_label": model_label,
        "created_at": created_at, "created_iso": created_iso,
        "is_local": provider.is_local,
        "rows": profile["overview"]["rows"], "cols": profile["overview"]["cols"],
    }
    report_id = store.create(meta, html, xlsx, pdf)
    return {**meta, "id": report_id, "pdf": pdf is not None}


@router.get("")
def list_reports():
    return _store().list()


_MEDIA = {
    "html": ("text/html; charset=utf-8", "inline"),
    "pdf": ("application/pdf", "attachment"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             "attachment"),
}


@router.get("/{report_id}/{kind}")
def get_report_file(report_id: str, kind: str):
    if kind not in _MEDIA:
        raise http_error("unknownFileKind", 404, kind=kind)
    data = _store().get_file(report_id, kind)
    media, disposition = _MEDIA[kind]
    headers = {}
    if disposition == "attachment":
        headers["Content-Disposition"] = f"attachment; filename=report-{report_id}.{kind}"
    return Response(content=data, media_type=media, headers=headers)


@router.delete("/{report_id}")
def delete_report(report_id: str):
    _store().delete(report_id)
    return {"success": True}
