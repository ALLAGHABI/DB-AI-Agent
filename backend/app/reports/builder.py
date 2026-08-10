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
        "dataCharts": "توزيعات البيانات",
        "kpiRecords": "عدد السجلات", "kpiTotal": "الإجمالي", "kpiAverage": "المتوسط",
        "kpiHighest": "الأعلى",
        "trendOf": "تطور {measure} عبر الزمن", "byDim": "{measure} حسب {dim}",
        "countByDim": "العدد حسب {dim}",
        "droppedNote": "تنبيه: حُذفت عبارات ذكرت أرقاماً غير موجودة في البيانات.",
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
        "dataCharts": "Data distributions",
        "kpiRecords": "Records", "kpiTotal": "Total", "kpiAverage": "Average",
        "kpiHighest": "Highest",
        "trendOf": "{measure} over time", "byDim": "{measure} by {dim}",
        "countByDim": "Count by {dim}",
        "droppedNote": "Note: statements citing numbers absent from the data were removed.",
        "range": "range", "outliers": "outliers",
        "footer": "Generated locally — your data never left your machine",
    },
}


def _chartjs_source() -> str:
    with open(os.path.join(_DIR, "assets", "chart.umd.min.js"), encoding="utf-8") as f:
        return f.read()


def _format_number(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value:,.2f}".rstrip("0").rstrip(".") if isinstance(value, float) \
        else f"{value:,}"


def _business_view(business: dict, strings: dict, max_charts: int) -> tuple[list, list]:
    """يحوّل أرقام الأعمال إلى بطاقات مؤشرات ورسوم جاهزة للقالب."""
    kpi_labels = {"records": "kpiRecords", "total": "kpiTotal",
                  "average": "kpiAverage", "highest": "kpiHighest"}
    kpis, charts = [], []
    multi = len(business) > 1

    for table, b in business.items():
        prefix = f"{table} · " if multi else ""
        for k in b["kpis"]:
            if len(kpis) >= 4 and not multi:
                break
            label = strings.get(kpi_labels.get(k["key"], ""), k["key"])
            kpis.append({"display": _format_number(k["value"]),
                         "label": prefix + label})

        tr = b.get("trend")
        if tr and len(charts) < max_charts:
            charts.append({
                "id": f"bchart-{len(charts) + 1}", "type": "line",
                "heading": prefix + strings["trendOf"].format(
                    measure=tr["measure"] or strings["kpiRecords"]),
                "labels": tr["labels"], "values": tr["values"],
            })
        for bd in b.get("breakdowns", []):
            if len(charts) >= max_charts:
                break
            heading = (strings["byDim"].format(measure=bd["measure"], dim=bd["column"])
                       if bd["measure"] else strings["countByDim"].format(dim=bd["column"]))
            charts.append({
                "id": f"bchart-{len(charts) + 1}", "type": "bar",
                "heading": prefix + heading,
                "labels": bd["labels"], "values": bd["values"],
            })

    return kpis[:8], charts


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
    strings = _STRINGS[language]
    max_business_charts = 3 if variant == "executive" else 8
    kpis, business_charts = _business_view(
        profile.get("business", {}), strings, max_business_charts)
    charts = business_charts + charts

    template = _env.get_template("report.html.j2")
    return template.render(
        kpis=kpis, business_charts=business_charts,
        dropped_claims=insights.get("dropped_claims", 0),
        title=title, profile=profile, insights=insights, language=language,
        variant=variant, source_name=source_name, model_label=model_label,
        created_at=created_at, brand_color=brand_color,
        t=_STRINGS[language],
        charts_json=json.dumps(charts, ensure_ascii=False),
        chartjs_source=_chartjs_source(),
    )
