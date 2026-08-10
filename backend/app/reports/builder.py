"""بناء تقرير HTML مكتفٍ ذاتياً — ثلاثة قوالب مختلفة فعلاً لا قالب بثلاثة أقنعة.

- executive: موجز صفحة واحدة للطباعة واجتماع الإدارة.
- dashboard: شبكة مؤشرات كثيفة للشاشة، شكل الرسم يتبع شكل البيانات.
- detailed: تعمّق تحليلي بجداول ترتيب وملحق قاموس بيانات.

القرارات البصرية (نوع كل رسم، خانته في الشبكة) تُحسب هنا لا في القالب،
حتى يبقى القالب عرضاً خالصاً ويسهل اختبار القواعد.
"""
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..errors import AppError
from .labels import categories_word, measure_phrase

_DIR = os.path.dirname(__file__)
_env = Environment(
    loader=FileSystemLoader(os.path.join(_DIR, "templates")),
    autoescape=select_autoescape(["html"]),
)

VARIANTS = ("executive", "dashboard", "detailed")
SECTIONS = ("summary", "findings", "charts", "recommendations", "appendix")

# ما يظهر افتراضياً في كل قالب — والمستخدم يعدّله من مخطط التقرير
DEFAULT_SECTIONS = {
    "executive": ("summary", "findings", "charts", "recommendations"),
    "dashboard": ("summary", "findings", "charts"),
    "detailed": ("summary", "findings", "charts", "recommendations", "appendix"),
}

MAX_CHARTS = {"executive": 3, "dashboard": 6, "detailed": 10}

# لوحة فئوية — المتصدر دائماً بلون العلامة
PALETTE = ["#059669", "#0d9488", "#0369a1", "#7c3aed",
           "#d97706", "#dc2626", "#64748b", "#94a3b8"]

_STRINGS = {
    "ar": {
        "lang": "ar",
        "variantExecutive": "موجز تنفيذي", "variantDashboard": "لوحة مؤشرات",
        "variantDetailed": "تقرير تحليلي مفصّل",
        "generated": "تاريخ الإنشاء", "source": "المصدر", "engine": "النموذج",
        "rows": "عدد الصفوف", "cols": "عدد الأعمدة", "period": "الفترة",
        "summary": "الملخص التنفيذي", "findings": "أبرز النتائج",
        "charts": "الرسوم البيانية", "recommendations": "التوصيات",
        "appendix": "الملحق: قاموس البيانات",
        "trendSection": "تحليل الاتجاه", "drillSection": "تعمّق حسب {dim}",
        "comparisons": "جدول المقارنات", "sectionKicker": "القسم {n}",
        "concentrationTitle": "تركّز المؤشر",
        "kpiRecords": "عدد السجلات", "kpiTotal": "إجمالي {measure}",
        "kpiAverage": "متوسط {measure}", "kpiHighest": "أعلى {measure}",
        "trendOf": "تطور {measure} عبر الزمن", "byDim": "{measure} حسب {dim}",
        "countByDim": "العدد حسب {dim}",
        "concentration": "«{leader}» يستحوذ على {pct}% من {measure}",
        "others": "أخرى", "othersOf": "أخرى ({count} {plural})",
        "rank": "#", "category": "الفئة", "value": "القيمة", "share": "الحصة",
        "runnerUp": "الوصيف", "leaderCol": "المتصدر", "delta": "الفارق",
        "dimension": "البُعد",
        "start": "البداية", "end": "النهاية", "change": "التغير", "peak": "الذروة",
        "column": "العمود", "kind": "النوع", "nulls": "فارغ", "unique": "قيم فريدة",
        "range": "المدى",
        "kindNumeric": "رقمي", "kindDatetime": "تاريخ", "kindCategorical": "فئوي",
        "dataQuality": "جودة البيانات: {rows} صفاً · {missing}% قيم مفقودة · "
                       "{dupes} صفوف مكررة",
        "trimmedNote": "استُبعدت {count} فترة طرفية غير مكتملة من حساب الاتجاه.",
        "scopeNote": "النسب محسوبة على الصفوف التي تحمل قيمة في العمود.",
        "droppedNote": "حُذفت عبارات ذكرت أرقاماً غير موجودة في البيانات.",
        "footer": "تقرير مولّد محلياً — بياناتك لم تغادر جهازك",
        "table": "جدول",
    },
    "en": {
        "lang": "en",
        "variantExecutive": "Executive Brief", "variantDashboard": "Dashboard",
        "variantDetailed": "Analytical Report",
        "generated": "Generated", "source": "Source", "engine": "Model",
        "rows": "Rows", "cols": "Columns", "period": "Period",
        "summary": "Executive Summary", "findings": "Key Findings",
        "charts": "Charts", "recommendations": "Recommendations",
        "appendix": "Appendix: Data Dictionary",
        "trendSection": "Trend Analysis", "drillSection": "Drill-down by {dim}",
        "comparisons": "Comparisons", "sectionKicker": "Section {n}",
        "concentrationTitle": "Concentration",
        "kpiRecords": "Records", "kpiTotal": "Total {measure}",
        "kpiAverage": "Average {measure}", "kpiHighest": "Highest {measure}",
        "trendOf": "{measure} over time", "byDim": "{measure} by {dim}",
        "countByDim": "Count by {dim}",
        "concentration": "'{leader}' holds {pct}% of {measure}",
        "others": "Others", "othersOf": "Others ({count} {plural})",
        "rank": "#", "category": "Category", "value": "Value", "share": "Share",
        "runnerUp": "Runner-up", "leaderCol": "Leader", "delta": "Gap",
        "dimension": "Dimension",
        "start": "Start", "end": "End", "change": "Change", "peak": "Peak",
        "column": "Column", "kind": "Type", "nulls": "nulls", "unique": "unique",
        "range": "Range",
        "kindNumeric": "numeric", "kindDatetime": "date", "kindCategorical": "text",
        "dataQuality": "Data quality: {rows} rows · {missing}% missing · "
                       "{dupes} duplicate rows",
        "trimmedNote": "{count} incomplete edge period(s) were excluded from the trend.",
        "scopeNote": "Shares are computed on rows that carry a value in the column.",
        "droppedNote": "Statements citing numbers absent from the data were removed.",
        "footer": "Generated locally — your data never left your machine",
        "table": "Table",
    },
}


def _chartjs_source() -> str:
    with open(os.path.join(_DIR, "assets", "chart.umd.min.js"), encoding="utf-8") as f:
        return f.read()


def _format_number(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)                     # تواريخ ونصوص تُعرض كما هي
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value:,.2f}".rstrip("0").rstrip(".") if isinstance(value, float) \
        else f"{value:,}"


def _compact(value) -> str:
    """أرقام البطاقات تُقرأ بلمحة: 1,486,390 ⇒ 1.49M، و204,700.28 ⇒ 204,700."""
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    for limit, suffix in ((1e9, "B"), (1e6, "M")):
        if abs(n) >= limit:
            return f"{n / limit:,.2f}".rstrip("0").rstrip(".") + suffix
    if abs(n) >= 1000:
        return f"{n:,.0f}"                    # الهللات لا مكان لها في بطاقة مؤشر
    return _format_number(value)


def _sparkline(values: list, width: int = 120, height: int = 26) -> str:
    """خط شرارة كـSVG جاهز — نبنيه هنا لا في المتصفح ليطبع في PDF بلا مفاجآت."""
    nums = [float(v) for v in values if v is not None]
    if len(nums) < 2:
        return ""
    lo, hi = min(nums), max(nums)
    span = (hi - lo) or 1.0
    step = width / (len(nums) - 1)
    return " ".join(
        f"{i * step:.1f},{height - ((v - lo) / span) * (height - 4) - 2:.1f}"
        for i, v in enumerate(nums))


def _kpi_cards(business: dict, strings: dict, labels: dict) -> list[dict]:
    """بطاقات المؤشرات — أرقام أعمال فقط، لا إحصاءات بنية (صفوف/أعمدة/فراغات)."""
    lbl = lambda c: labels.get(c, c)            # noqa: E731
    multi = len(business) > 1
    cards: list[dict] = []

    for table, b in business.items():
        prefix = f"{lbl(table)} · " if multi else ""
        trend = b.get("trend")
        for k in b["kpis"]:
            if not multi and len(cards) >= 4:
                break
            key = k["key"]
            measure = measure_phrase(lbl(k["column"])) if k.get("column") else ""
            label = strings[f"kpi{key.capitalize()}"].format(measure=measure)
            card = {"value": _compact(k["value"]), "label": prefix + label,
                    "delta": None, "spark": ""}
            attach = (trend and ((key == "total" and trend.get("measure"))
                                 or (key == "records" and not trend.get("measure"))))
            if attach:
                card["delta"] = trend.get("change_pct")
                card["spark"] = _sparkline(trend["values"])
            cards.append(card)
        if multi and len(cards) >= 8:
            break
    return cards[:8]


def _heading(bd: dict, strings: dict, lbl) -> str:
    return (strings["byDim"].format(measure=lbl(bd["measure"]), dim=lbl(bd["column"]))
            if bd.get("measure") else strings["countByDim"].format(dim=lbl(bd["column"])))


def _auto_type(bd: dict, used_doughnut: bool) -> str:
    """شكل الرسم يتبع شكل البيانات — لا لون واحد ولا عمود واحد لكل شيء."""
    if bd["categories"] <= 5 and not used_doughnut:
        return "doughnut"
    return "hbar"


def _breakdown_chart(bd: dict, ctype: str, strings: dict, lbl) -> dict:
    labels = list(bd["labels"])
    values = list(bd["values"])
    if bd.get("others"):
        rest = bd["categories"] - len(values)
        labels.append(strings["othersOf"].format(
            count=rest, plural=categories_word(rest, strings["lang"])))
        values.append(bd["others"])
    return {
        "type": ctype, "heading": _heading(bd, strings, lbl),
        "labels": labels, "values": values,
        "colors": [PALETTE[i % len(PALETTE)] for i in range(len(values))]
        if ctype == "doughnut" else None,
        "kind": "breakdown", "column": bd["column"],
    }


def _trend_chart(tr: dict, ctype: str, strings: dict, lbl) -> dict:
    return {
        "type": ctype, "kind": "trend", "column": tr["column"],
        "heading": strings["trendOf"].format(
            measure=lbl(tr["measure"]) if tr.get("measure") else strings["kpiRecords"]),
        "labels": tr["labels"], "values": tr["values"],
        "granularity": tr.get("granularity"),
        "peak_index": tr["values"].index(tr["peak_value"])
        if tr["peak_value"] in tr["values"] else None,
    }


def _auto_charts(business: dict, variant: str, strings: dict, labels: dict) -> list[dict]:
    lbl = lambda c: labels.get(c, c)            # noqa: E731
    multi = len(business) > 1
    out: list[dict] = []
    used_doughnut = False
    cap = MAX_CHARTS[variant]

    # الاتجاهات أولاً حتى لا يبتلع جدولٌ واحد كل الخانات بتوزيعاته
    for table, b in business.items():
        tr = b.get("trend")
        if tr and len(out) < cap:
            out.append({**_trend_chart(tr, "line_area", strings, lbl),
                        "slot": 8, "hero": True, "table": table,
                        "band": lbl(table) if multi else None})
    for table, b in business.items():
        for bd in b.get("breakdowns", []):
            if len(out) >= cap:
                return out
            ctype = _auto_type(bd, used_doughnut)
            used_doughnut = used_doughnut or ctype == "doughnut"
            out.append({**_breakdown_chart(bd, ctype, strings, lbl),
                        "slot": 4, "hero": False, "table": table,
                        "band": lbl(table) if multi else None})
    return out


def _requested_charts(business: dict, requested: list[dict], strings: dict,
                      labels: dict) -> list[dict]:
    """يبني الرسوم التي اختارها المستخدم بالضبط — نوعاً وترتيباً."""
    lbl = lambda c: labels.get(c, c)            # noqa: E731
    multi = len(business) > 1
    type_map = {"bar": "hbar", "column": "vbar", "line": "line_area",
                "area": "line_area", "donut": "doughnut", "doughnut": "doughnut",
                "gauge": "gauge"}
    out: list[dict] = []

    for spec in requested:
        table = spec.get("table") or next(iter(business), None)
        b = business.get(table)
        if not b:
            continue
        band = lbl(table) if multi else None
        ctype = type_map.get(str(spec.get("type", "")).lower())
        if spec.get("kind") == "trend":
            tr = b.get("trend")
            if not tr:
                continue
            out.append({**_trend_chart(tr, ctype or "line_area", strings, lbl),
                        "slot": 8, "hero": True, "table": table, "band": band})
            continue
        bd = next((x for x in b.get("breakdowns", [])
                   if x["column"] == spec.get("column")), None)
        if not bd:
            continue
        out.append({**_breakdown_chart(bd, ctype or _auto_type(bd, False), strings, lbl),
                    "slot": 4, "hero": False, "table": table, "band": band})
    return out


GRID = 12


def _size(chart: dict) -> tuple[int, str]:
    """حجم البطاقة يتبع كمية بياناتها: دائري صغير مضغوط، وأعمدة كثيرة تحتاج مساحة."""
    if chart.get("hero"):
        return 8, "hero"
    n = len(chart.get("labels") or [])
    if chart["type"] == "doughnut":
        return 4, "short" if n <= 4 else ""
    if chart["type"] == "hbar":
        if n <= 5:
            return 4, "short"
        if n <= 9:
            return 4, ""
        return 6, "tall"                 # 10 أشرطة فأكثر تحتاج عرضاً وارتفاعاً
    return (4, "") if n <= 8 else (6, "")


def _pack(charts: list[dict], first_row_used: int) -> None:
    """يوزّع البطاقات على صفوف مكتملة — الفراغ في آخر الصف يذهب لآخر بطاقة فيه."""
    row, start = first_row_used, 0
    for i, c in enumerate(charts):
        if row + c["slot"] > GRID:
            if row < GRID and i > start:
                charts[i - 1]["slot"] += GRID - row      # وسّع الأخيرة لتملأ الصف
            row, start = 0, i
        row += c["slot"]
    if row < GRID and charts:
        charts[-1]["slot"] += GRID - row


def chart_plan(business: dict, variant: str, language: str, labels: dict | None = None,
               requested: list[dict] | None = None) -> list[dict]:
    strings = _STRINGS[language]
    labels = labels or {}
    charts = (_requested_charts(business, requested, strings, labels)
              if requested is not None
              else _auto_charts(business, variant, strings, labels))
    # رسم رئيسي واحد فقط؛ القالب يعرض الأول، فبقية الاتجاهات تصير بطاقات عادية
    seen_hero = False
    for i, c in enumerate(charts, 1):
        c["id"] = f"ch-{i}"
        if c.get("hero"):
            c["hero"] = not seen_hero
            seen_hero = True
        c["slot"], c["size"] = _size(c)
        if c["kind"] == "trend" and not c["hero"]:
            c["slot"] = 6                       # اتجاه ثانوي يحتاج عرضاً لا مربعاً
    return charts


def _concentration(business: dict, strings: dict, labels: dict) -> dict | None:
    """أقوى تركّز في البيانات — بطاقة مستقلة لأنها إشارة إدارية لا رسماً."""
    lbl = lambda c: labels.get(c, c)            # noqa: E731
    best = None
    for b in business.values():
        for bd in b.get("breakdowns", []):
            share = bd.get("leader_share_pct")
            if share and share >= 50 and (not best or share > best["pct"]):
                best = {
                    "pct": share, "leader": bd["leader"],
                    "text": strings["concentration"].format(
                        leader=bd["leader"], pct=_format_number(share),
                        measure=lbl(bd["measure"]) if bd.get("measure")
                        else lbl(bd["column"])),
                    "partial": bd.get("coverage_pct", 100) < 95,
                }
    return best


def _rank_tables(business: dict, strings: dict, labels: dict) -> list[dict]:
    """جداول ترتيب تحلّ محل «عينة البيانات» — قيم حقيقية لكنها مجمّعة ومفيدة."""
    lbl = lambda c: labels.get(c, c)            # noqa: E731
    multi = len(business) > 1
    out = []
    for table, b in business.items():
        for bd in b.get("breakdowns", []):
            rows = [{"rank": i + 1, "label": l, "value": _format_number(v),
                     "pct": p}
                    for i, (l, v, p) in enumerate(
                        zip(bd["labels"], bd["values"], bd["values_pct"]))]
            if bd.get("others"):
                rows.append({
                    "rank": None,
                    "label": strings["othersOf"].format(
                        count=bd["categories"] - len(bd["values"]),
                        plural=categories_word(bd["categories"] - len(bd["values"]),
                                               strings["lang"])),
                    "value": _format_number(bd["others"]),
                    "pct": round(100 * bd["others"] / bd["total"], 1)
                    if bd.get("total") else None})
            out.append({
                "title": strings["drillSection"].format(dim=lbl(bd["column"])),
                "band": lbl(table) if multi else None, "table": table,
                "heading": _heading(bd, strings, lbl),
                "rows": rows, "column": bd["column"],
                "partial": bd.get("coverage_pct", 100) < 95,
            })
    return out


def _comparisons(business: dict, strings: dict, labels: dict) -> list[dict]:
    lbl = lambda c: labels.get(c, c)            # noqa: E731
    rows = []
    for b in business.values():
        for bd in b.get("breakdowns", []):
            if len(bd["values"]) < 2:
                continue
            gap = (bd["values"][0] or 0) - (bd["values"][1] or 0)
            rows.append({
                "dimension": lbl(bd["column"]), "leader": bd["leader"],
                "runner_up": bd["labels"][1],
                "delta": _format_number(round(gap, 2)),
                "share": bd.get("leader_share_pct"),
            })
    return rows


_KIND_KEY = {"numeric": "kindNumeric", "datetime": "kindDatetime",
             "categorical": "kindCategorical"}


def _dictionary(profile: dict, strings: dict, labels: dict) -> list[dict]:
    """قاموس بيانات مضغوط — يحلّ محل بطاقات «تفاصيل الأعمدة» المبعثرة."""
    lbl = lambda c: labels.get(c, c)            # noqa: E731
    sources = ([(d["name"], d["profile"]) for d in profile["datasets"]]
               if profile.get("kind") == "multi" else [(None, profile)])
    out = []
    for table, prof in sources:
        rows = int(prof["overview"]["rows"]) or 1
        for col in prof["columns"]:
            rng = ""
            if col.get("min") is not None and col.get("max") is not None:
                rng = f"{_format_number(col['min'])} – {_format_number(col['max'])}"
            out.append({
                "table": lbl(table) if table else None,
                "name": lbl(col["name"]), "raw": col["name"],
                "kind": strings.get(_KIND_KEY.get(col["kind"], ""), col["kind"]),
                "nulls_pct": round(100 * col["nulls"] / rows, 1),
                "unique": col["unique"], "range": rng,
            })
    return out


def _quality_note(profile: dict, business: dict, strings: dict, variant: str) -> str:
    """سطر جودة البيانات — تفصيله للتقرير التحليلي، وللتنفيذي ما يمسّ المصداقية فقط."""
    parts = []
    if variant == "detailed":
        ov = profile["overview"]
        parts.append(strings["dataQuality"].format(
            rows=f"{ov['rows']:,}", missing=ov.get("missing_pct", 0),
            dupes=f"{ov.get('duplicate_rows', 0):,}"))
    trimmed = sum((b.get("trend") or {}).get("trimmed_periods", 0)
                  for b in business.values())
    if trimmed:
        parts.append(strings["trimmedNote"].format(count=trimmed))
    return " · ".join(parts)


def build_report_html(*, title: str, profile: dict, insights: dict, language: str,
                      variant: str, source_name: str, model_label: str,
                      created_at: str, brand_color: str = "#059669",
                      labels: dict | None = None, sections: list[str] | None = None,
                      charts: list[dict] | None = None) -> str:
    if variant not in VARIANTS:
        raise AppError("unknownTemplate", template=variant)
    if language not in _STRINGS:
        raise AppError("unsupportedLanguage", language=language)

    strings = _STRINGS[language]
    labels = labels or {}
    business = profile.get("business", {})
    active = [s for s in SECTIONS
              if s in (sections if sections is not None else DEFAULT_SECTIONS[variant])]

    plan = charts if charts is not None else chart_plan(
        business, variant, language, labels)
    if "charts" not in active:
        plan = []

    trend = next((b["trend"] for b in business.values() if b.get("trend")), None)
    period = trend["period"] if trend else None
    concentration = (_concentration(business, strings, labels)
                     if variant != "detailed" and "charts" in active else None)

    # الرسم الرئيسي وشريط النتائج في كتلة مستقلة؛ باقي البطاقات تُرصّ لتملأ صفوفها
    if variant == "dashboard":
        _pack([c for c in plan if not c.get("hero")], 4 if concentration else 0)

    # عدّاد التركّز لوحة رسم مستقلة عن بطاقات الرسوم — يُضاف للسكربت فقط
    canvases = list(plan)
    if concentration:
        canvases.append({"id": "conc-gauge", "type": "gauge",
                         "values": [concentration["pct"], 100 - concentration["pct"]],
                         "labels": []})

    template = _env.get_template(f"{variant}.html.j2")
    html = template.render(
        title=title, t=strings, language=language, variant=variant,
        rtl=language == "ar", brand_color=brand_color,
        source_name=source_name, model_label=model_label, created_at=created_at,
        sections=active, profile=profile, insights=insights,
        kpis=_kpi_cards(business, strings, labels) if business else [],
        charts=plan,
        hero=next((c for c in plan if c.get("hero")), None),
        tiles=[c for c in plan if not c.get("hero")],
        concentration=concentration,
        rank_tables=_rank_tables(business, strings, labels) if "charts" in active else [],
        comparisons=_comparisons(business, strings, labels),
        dictionary=_dictionary(profile, strings, labels) if "appendix" in active else [],
        quality_note=_quality_note(profile, business, strings, variant),
        trend=trend, period=period,
        variant_badge=strings[f"variant{variant.capitalize()}"],
        dropped_claims=insights.get("dropped_claims", 0),
        charts_json=json.dumps(canvases, ensure_ascii=False),
        chartjs_source=_chartjs_source(),
        palette_json=json.dumps(PALETTE),
    )
    return html
