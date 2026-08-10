"""مسارات استوديو التقارير."""
import asyncio
import datetime
import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from ..db import transfer
from ..reports import exporter
from ..reports.analyzer import MAX_DATASETS, profile_datasets, profile_df
from ..reports.business import analyze_business, facts_from_business
from ..reports import builder
from ..reports.builder import build_report_html
from ..reports.labels import label_columns
from ..reports.narrative import compose_narrative
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
    language: str = "ar"            # لغة التسميات المقترحة


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

    semantics = {name: analyze_business(df)["semantics"]
                 for name, df in frames.items() if not df.empty}
    all_columns = sorted({c for df in frames.values() for c in df.columns})
    labels = label_columns(all_columns + list(frames), body.language)

    if len(frames) == 1:
        name, df = next(iter(frames.items()))
        return {"token": _store().save_temp(df, name),
                "profile": profile_df(df), "semantics": semantics, "labels": labels}

    profile = profile_datasets(frames, relationships)
    source = state.db.dialect or "database"
    token = _store().save_temp(frames, source, relationships)
    return {"token": token, "profile": profile,
            "semantics": semantics, "labels": labels}


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), language: str = Form("ar")):
    data = await file.read()
    try:
        sheets = transfer.read_upload(file.filename or "upload", data)
    except AppError:
        raise
    except Exception as e:
        raise http_error("fileReadFailed", detail=str(e))
    sheets = {k: v for k, v in sheets.items() if not v.empty}
    if not sheets:
        raise http_error("emptyFile")

    semantics = {name: analyze_business(df)["semantics"] for name, df in sheets.items()}
    all_columns = sorted({str(c) for df in sheets.values() for c in df.columns})
    labels = label_columns(all_columns + list(sheets), language)
    source = file.filename or "upload"

    if len(sheets) == 1:
        name, df = next(iter(sheets.items()))
        return {"token": _store().save_temp(df, name), "profile": profile_df(df),
                "semantics": semantics, "labels": labels, "sheets": list(sheets)}

    # ملف متعدد الأوراق ⇒ تقرير مركّب، ورقة لكل قسم
    return {"token": _store().save_temp(sheets, source),
            "profile": profile_datasets(sheets),
            "semantics": semantics, "labels": labels, "sheets": list(sheets)}


class ChartSpec(BaseModel):
    table: str | None = None             # None = المصدر الوحيد
    kind: str = "breakdown"              # trend | breakdown
    column: str | None = None            # عمود البُعد (للتوزيعات)
    type: str | None = None              # bar | column | line | area | donut


class GenerateIn(BaseModel):
    token: str
    title: str
    template: str = "executive"          # executive | detailed | dashboard
    language: str = "ar"
    provider: str
    model: str
    overrides: dict | None = None        # {table: {measure, date, dimensions}}
    labels: dict | None = None           # {column: "تسمية وصفية"}
    sections: list[str] | None = None    # المفعّل فقط؛ None = افتراضي القالب
    charts: list[ChartSpec] | None = None  # ترتيب ونوع كل رسم؛ None = تلقائي


_EXT = re.compile(r"\.(csv|xlsx?|json)(-\d+)?$", re.IGNORECASE)
_COPY = re.compile(r"\s*\(\d+\)$")             # نسخة مكررة من التنزيل


def _clean_title(raw: str, fallback: str) -> str:
    """عنوان التقرير لا يحمل امتداد الملف — «تقرير.XLSX-2» ليس عنواناً لصفحة أولى."""
    text = _COPY.sub("", _EXT.sub("", str(raw or "").strip())).strip(" -_·")
    return text or fallback


@router.post("/generate")
def generate(body: GenerateIn):
    """يبدأ التوليد كمهمة خلفية ويعيد معرّفها فوراً.

    التوليد المحلي قد يتجاوز 30 ثانية (نموذج + PDF)، وأي وسيط HTTP بينهما
    يقطع الطلب الطويل — فنفصل بدء العمل عن انتظار نتيجته.
    """
    store = _store()
    saved = store.load_temp(body.token)          # يفشل فوراً إن انتهت الجلسة
    try:
        provider = state.provider_by_id(body.provider)
    except KeyError:
        raise http_error("unknownProvider", provider=body.provider)

    title = _clean_title(body.title, saved["source_name"])
    sections = (None if body.sections is None
                else [s for s in body.sections if s in builder.SECTIONS])

    def work() -> dict:
        frames, source_name = saved["frames"], saved["source_name"]
        if saved["kind"] == "multi":
            profile = profile_datasets(frames, saved.get("relationships"))
        else:
            profile = profile_df(next(iter(frames.values())))

        # أرقام الأعمال الحقيقية — هي وحدها ما يراه النموذج
        business, facts = {}, []
        # تسميات وصفية للأعمدة والجداول — التقرير يتحدث لغة الأعمال
        all_columns = {c for df in frames.values() for c in df.columns}
        labels = label_columns(sorted(all_columns) + list(frames),
                               body.language, body.labels)
        for name, df in frames.items():
            if df.empty:
                continue
            label = name if len(frames) > 1 else None
            b = analyze_business(df, body.overrides.get(name) if body.overrides else None)
            business[name] = b
            facts.extend(facts_from_business(b, label, labels, body.language))
        profile = {**profile, "business": business}

        fallback = compose_narrative(business, labels, body.language,
                                     subject=labels.get(source_name, source_name))
        try:
            insights = asyncio.run(generate_insights(
                provider, body.model, facts, body.language,
                subject=source_name, fallback=fallback, sections=sections))
        except AppError:
            raise
        except Exception as e:
            raise AppError("insightsFailed", 502, detail=str(e))

        charts = None
        if body.charts is not None:
            charts = builder.chart_plan(
                business, body.template, body.language, labels,
                requested=[c.model_dump() for c in body.charts])

        now = datetime.datetime.now().astimezone()
        created_at = now.strftime("%Y-%m-%d %H:%M")
        model_label = f"{provider.id}/{body.model}"
        html = build_report_html(
            title=title, profile=profile, insights=insights,
            language=body.language, variant=body.template,
            source_name=source_name, model_label=model_label,
            created_at=created_at, labels=labels,
            sections=sections, charts=charts)
        xlsx = exporter.to_xlsx(profile, insights, body.language,
                                sections=sections or builder.DEFAULT_SECTIONS[
                                    body.template])
        try:
            pdf = exporter.to_pdf(html)
        except Exception as e:
            print(f"PDF export failed: {e}")
            pdf = None

        meta = {
            "title": title, "template": body.template, "language": body.language,
            "language_ok": insights.get("language_ok", True),
            "dropped_claims": insights.get("dropped_claims", 0),
            "used_fallback": insights.get("used_fallback", False),
            "source_name": source_name, "model_label": model_label,
            "created_at": created_at, "created_iso": now.isoformat(),
            "is_local": provider.is_local,
            "rows": profile["overview"]["rows"], "cols": profile["overview"]["cols"],
        }
        report_id = store.create(meta, html, xlsx, pdf)
        return {**meta, "id": report_id, "pdf": pdf is not None}

    return {"job_id": state.jobs.run(work), "status": "running"}


@router.get("/jobs/{job_id}")
def generate_status(job_id: str):
    """حالة مهمة التوليد — running | done | failed."""
    job = state.jobs.get(job_id)
    if job["status"] == "failed":
        return {"status": "failed", "error": job["error"]}
    if job["status"] == "done":
        return {"status": "done", "report": job["result"]}
    return {"status": "running"}


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
