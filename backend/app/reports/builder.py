"""بناء تقرير HTML مكتفٍ ذاتياً من القالب."""
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..errors import AppError

_DIR = os.path.dirname(__file__)
_env = Environment(
    loader=FileSystemLoader(os.path.join(_DIR, "templates")),
    autoescape=select_autoescape(["html"]),
)

_STRINGS = {
    "ar": {
        "badge": "تقرير تحليلي", "generated": "تاريخ الإنشاء", "source": "المصدر",
        "engine": "النموذج", "rows": "عدد الصفوف", "cols": "عدد الأعمدة",
        "missing": "قيم مفقودة", "duplicates": "صفوف مكررة",
        "summary": "الملخص التنفيذي", "findings": "أبرز النتائج",
        "charts": "الرسوم البيانية", "recommendations": "التوصيات",
        "columns": "تفاصيل الأعمدة", "sample": "عينة من البيانات",
        "nulls": "فارغ", "unique": "فريد", "mean": "المتوسط",
        "tables": "عدد الجداول", "relationships": "العلاقات", "table": "جدول",
        "range": "المدى", "outliers": "شواذ",
        "footer": "تقرير مولّد محلياً — بياناتك لم تغادر جهازك",
    },
    "en": {
        "badge": "Analytics Report", "generated": "Generated", "source": "Source",
        "engine": "Model", "rows": "Rows", "cols": "Columns",
        "missing": "Missing values", "duplicates": "Duplicate rows",
        "summary": "Executive Summary", "findings": "Key Findings",
        "charts": "Charts", "recommendations": "Recommendations",
        "columns": "Column Details", "sample": "Data Sample",
        "nulls": "nulls", "unique": "unique", "mean": "mean",
        "tables": "Tables", "relationships": "Relationships", "table": "Table",
        "range": "range", "outliers": "outliers",
        "footer": "Generated locally — your data never left your machine",
    },
}


def _chartjs_source() -> str:
    with open(os.path.join(_DIR, "assets", "chart.umd.min.js"), encoding="utf-8") as f:
        return f.read()


def build_report_html(*, title: str, profile: dict, insights: dict, language: str,
                      variant: str, source_name: str, model_label: str,
                      created_at: str, brand_color: str = "#059669") -> str:
    if variant not in ("executive", "detailed", "dashboard"):
        raise AppError("unknownTemplate", template=variant)
    if language not in _STRINGS:
        raise AppError("unsupportedLanguage", language=language)
    if profile.get("kind") == "multi":
        # كل جدول يحمل رسومه؛ نجمعها بمعرفات فريدة للوحة الرسم
        datasets = profile["datasets"]
        if variant == "executive":
            datasets = [{**d, "profile": {**d["profile"],
                                          "charts": d["profile"]["charts"][:1]}}
                        for d in datasets]
        profile = {**profile, "datasets": datasets}
        charts = [{**c, "id": f"chart-{d['name']}-{i + 1}"}
                  for d in datasets for i, c in enumerate(d["profile"]["charts"])]
    else:
        charts = profile.get("charts", [])
        if variant == "executive":
            charts = charts[:3]
        profile = {**profile, "charts": charts}
        charts = [{**c, "id": f"chart-{i + 1}"} for i, c in enumerate(charts)]
    template = _env.get_template("report.html.j2")
    return template.render(
        title=title, profile=profile, insights=insights, language=language,
        variant=variant, source_name=source_name, model_label=model_label,
        created_at=created_at, brand_color=brand_color,
        t=_STRINGS[language],
        charts_json=json.dumps(charts, ensure_ascii=False),
        chartjs_source=_chartjs_source(),
    )
