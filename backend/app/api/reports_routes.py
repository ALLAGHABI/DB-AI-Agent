"""مسارات استوديو التقارير."""
import asyncio
import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from ..db import transfer
from ..reports import exporter
from ..reports.analyzer import profile_df
from ..reports.builder import build_report_html
from ..reports.insights import generate_insights
from ..reports.store import ReportStore
from ..config import settings
from ..state import state

router = APIRouter(prefix="/api/reports")


def _store() -> ReportStore:
    return ReportStore(settings.data_dir)


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    try:
        df = transfer.read_upload(file.filename or "upload", data)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(400, detail=f"تعذر قراءة الملف: {e}")
    if df.empty:
        raise HTTPException(400, detail="الملف لا يحتوي بيانات")
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
    try:
        df, source_name = store.load_temp(body.token)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))

    profile = profile_df(df)
    try:
        provider = state.provider_by_id(body.provider)
    except KeyError:
        raise HTTPException(400, detail=f"مزود غير معروف: {body.provider}")
    try:
        insights = await generate_insights(provider, body.model, profile, body.language)
    except Exception as e:
        raise HTTPException(502, detail=f"فشل توليد الرؤى: {e}")

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    model_label = f"{provider.id}/{body.model}"
    try:
        html = build_report_html(
            title=body.title, profile=profile, insights=insights,
            language=body.language, variant=body.template,
            source_name=source_name, model_label=model_label,
            created_at=created_at)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
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
        "created_at": created_at, "is_local": provider.is_local,
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
        raise HTTPException(404, detail="نوع غير معروف")
    try:
        data = _store().get_file(report_id, kind)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    media, disposition = _MEDIA[kind]
    headers = {}
    if disposition == "attachment":
        headers["Content-Disposition"] = f"attachment; filename=report-{report_id}.{kind}"
    return Response(content=data, media_type=media, headers=headers)


@router.delete("/{report_id}")
def delete_report(report_id: str):
    try:
        _store().delete(report_id)
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    return {"success": True}
