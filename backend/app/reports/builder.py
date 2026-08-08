"""بناء تقرير HTML مكتفٍ ذاتياً من القالب."""
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

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
        "range": "range", "outliers": "outliers",
        "footer": "Generated locally — your data never left your machine",
    },
}


def _chartjs_source() -> str:
    with open(os.path.join(_DIR, "assets", "chart.umd.min.js"), encoding="utf-8") as f:
        return f.read()


def build_report_html(*, title: str, profile: dict, insights: dict, language: str,
                      variant: str, source_name: str, model_label: str,
                      created_at: str, brand_color: str = "#2a78d6") -> str:
    if variant not in ("executive", "detailed", "dashboard"):
        raise ValueError(f"قالب غير معروف: {variant}")
    if language not in _STRINGS:
        raise ValueError(f"لغة غير مدعومة: {language}")
    charts = profile.get("charts", [])
    if variant == "executive":
        charts = charts[:3]
    profile = {**profile, "charts": charts}
    template = _env.get_template("report.html.j2")
    return template.render(
        title=title, profile=profile, insights=insights, language=language,
        variant=variant, source_name=source_name, model_label=model_label,
        created_at=created_at, brand_color=brand_color,
        t=_STRINGS[language],
        charts_json=json.dumps(charts, ensure_ascii=False),
        chartjs_source=_chartjs_source(),
    )
