"""محرك التحليل التنفيذي — يحوّل البيانات الخام إلى أرقام أعمال حقيقية.

الفرق عن analyzer.py: ذاك يصف *بنية* البيانات (أنواع، قيم فارغة، شواذ)،
وهذا يجيب أسئلة *الأعمال*: كم الإجمالي؟ ما الاتجاه؟ من الأفضل؟ أين تتركز؟

كل رقم هنا محسوب من البيانات فعلياً — ويُمرَّر للنموذج كقائمة حقائق
ليكتب فوقها بدل أن يخترع.
"""
import re

import numpy as np
import pandas as pd

# تلميحات أسماء الأعمدة (عربي/إنجليزي) لاكتشاف الدلالة تلقائياً
_MEASURE_HINTS = ("amount", "total", "price", "revenue", "sales", "cost", "value",
                  "salary", "profit", "balance", "قيمة", "مبلغ", "سعر", "إجمالي",
                  "ايراد", "إيراد", "مبيعات", "راتب", "تكلفة")
_COUNT_HINTS = ("qty", "quantity", "count", "units", "stock", "عدد", "كمية", "مخزون")
# أعمدة تجميعية جاهزة: «اجمالي تكلفة التشغيل» أصلح للجمع من «القيمة في الشهر»
_AGGREGATE_HINTS = ("اجمالي", "إجمالي", "مجموع", "total", "sum", "net", "صافي")
# معدّلات ونِسَب: جمعها بلا معنى — «القيمة في الشهر» ليست مبلغاً يُجمع
_RATE_HINTS = ("في الساعة", "بالساعة", "لكل", "معدل", "نسبة", "متوسط", "سعر",
               " per ", "per_", "_per", "rate", "ratio", "percent", "price",
               "avg", "average")
# أعلام منطقية (0/1) — «متوسط نشط 0.9» و«تطور نشط عبر الزمن» هراء تحليلي
_FLAG_HINTS = ("is_", "has_", "active", "enabled", "deleted", "flag",
               "نشط", "مفعل", "محذوف")
_DIM_HINTS = ("city", "country", "region", "category", "type", "status", "state",
              "name", "product", "customer", "branch", "department", "gender",
              "مدينة", "دولة", "منطقة", "فئة", "نوع", "حالة", "اسم", "قسم", "فرع")
# حقول نصية حرة أو بيانات تواصل — رسم توزيع عليها بلا فائدة وقد يكشف أفراداً
_NON_DIM_HINTS = ("email", "mail", "phone", "mobile", "address", "description",
                  "note", "comment", "url", "link", "password",
                  "بريد", "هاتف", "جوال", "عنوان", "وصف", "ملاحظ", "رابط")

# كلمات تدل على معرّف لا مقياس — «رقم المرجع» ليس رقماً يُجمع أو يُرسم
_ID_TOKENS = frozenset((
    "id", "code", "codes", "serial", "barcode", "sku", "no", "num", "number",
    "رقم", "الرقم", "ارقام", "أرقام", "كود", "الكود", "رمز", "الرمز",
    "معرف", "المعرف", "هوية", "الهوية", "تسلسل", "التسلسل", "بطاقة",
))

TOP_N = 8
MAX_TREND_POINTS = 24
MAX_DIM_CATEGORIES = 30
MIN_ROWS_FOR_RATIO = 20
NEAR_UNIQUE_RATIO = 0.95
# فترة طرفية أقل من هذه النسبة من الوسيط = فترة غير مكتملة، لا انهيار حقيقي
MIN_EDGE_SHARE = 0.35


def _tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[\s_\-.]+", str(name).strip().lower()) if t]


def is_rate(name: str) -> bool:
    """عمود يمثل معدلاً/سعر وحدة — يُتوسَّط ولا يُجمع."""
    return any(h in str(name).lower() for h in _RATE_HINTS)


def _is_flag(name: str, series: pd.Series) -> bool:
    low = str(name).lower()
    values = set(pd.Series(series.dropna().unique()).tolist())
    return bool(values and values <= {0, 1, 0.0, 1.0}
                and (len(values) <= 2 or any(h in low for h in _FLAG_HINTS)))


def _is_identifier(name: str, series: pd.Series) -> bool:
    """معرّف = اسمه يدل عليه، أو قيمه أعداد صحيحة شبه فريدة."""
    toks = _tokens(name)
    if toks and (toks[0] in _ID_TOKENS or toks[-1] in _ID_TOKENS):
        return True
    # نسبة التفرد لا معنى لها على عينة صغيرة: جدول ميزانيات بأربعة صفوف
    # كل قيمه مختلفة، وليست معرّفات.
    if len(series) < MIN_ROWS_FOR_RATIO or not pd.api.types.is_integer_dtype(series):
        return False
    return series.nunique(dropna=True) / len(series) >= NEAR_UNIQUE_RATIO


def detect_semantics(df: pd.DataFrame) -> dict:
    """يخمّن دلالة الأعمدة: القيمة (measure)، التاريخ، والأبعاد (dimensions)."""
    measures, dates, dimensions = [], [], []
    for col in df.columns:
        name, s = str(col), df[col]
        low = name.lower()

        if pd.api.types.is_datetime64_any_dtype(s):
            dates.append(name)
            continue

        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            if _is_identifier(name, s) or _is_flag(name, s):
                continue
            score = 2 if any(h in low for h in _MEASURE_HINTS) else 0
            score += 1 if any(h in low for h in _COUNT_HINTS) else 0
            score += 2 if any(h in low for h in _AGGREGATE_HINTS) else 0
            score -= 3 if any(h in low for h in _RATE_HINTS) else 0
            measures.append((score, name))
            continue

        if any(h in low for h in _NON_DIM_HINTS):
            continue

        # تصنيف مفيد = فئات قليلة متكررة؛ عمود شبه فريد (اسم، رقم مرجعي) لا يصلح.
        # نسبة التفرد لا معنى لها على عينة صغيرة، فنطبقها من MIN_ROWS_FOR_RATIO فأكثر.
        unique = s.nunique(dropna=True)
        rows = len(s.dropna())
        repetitive = rows < MIN_ROWS_FOR_RATIO or unique / rows <= 0.6
        if 1 < unique <= MAX_DIM_CATEGORIES and repetitive:
            score = 1 if any(h in low for h in _DIM_HINTS) else 0
            dimensions.append((score, unique, name))

    measures.sort(key=lambda x: -x[0])
    dimensions.sort(key=lambda x: (-x[0], x[1]))
    return {
        "measures": [m[1] for m in measures],
        "dates": dates,
        "dimensions": [d[2] for d in dimensions],
    }


def _num(v) -> float | int | None:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    return round(float(v), 2)


def _kpis(df: pd.DataFrame, measure: str | None) -> list[dict]:
    out = [{"key": "records", "value": int(len(df))}]
    if measure and measure in df.columns:
        s = pd.to_numeric(df[measure], errors="coerce").dropna()
        if len(s):
            if not is_rate(measure):           # لا يُجمع سعر الوحدة ولا المعدل
                out.append({"key": "total", "value": _num(s.sum()), "column": measure})
            out += [
                {"key": "average", "value": _num(s.mean()), "column": measure},
                {"key": "highest", "value": _num(s.max()), "column": measure},
            ]
    return out


def _trend(df: pd.DataFrame, date_col: str, measure: str | None) -> dict | None:
    d = df.dropna(subset=[date_col]).copy()
    if d.empty:
        return None
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        return None

    span_days = (d[date_col].max() - d[date_col].min()).days
    freq, label = ("ME", "month") if span_days > 70 else ("D", "day")
    grouper = pd.Grouper(key=date_col, freq=freq)
    series = (d.groupby(grouper)[measure].sum() if measure and measure in d.columns
              else d.groupby(grouper).size())
    counts = d.groupby(grouper).size()
    bounds = d.groupby(grouper)[date_col].agg(["min", "max"])
    series = series.tail(MAX_TREND_POINTS)
    counts, bounds = counts.tail(MAX_TREND_POINTS), bounds.tail(MAX_TREND_POINTS)

    # فترة البداية أو النهاية قد تكون مبتورة (شهر لم يكتمل، أو صفوف بتواريخ شاذة)،
    # فتُقرأ كقفزة أو انهيار وهميين — نُسقطها بدل بناء استنتاج عليها.
    keep = list(range(len(series)))
    if len(keep) > 2:
        floor = float(np.median(counts.values)) * MIN_EDGE_SHARE
        while len(keep) > 2 and counts.iloc[keep[0]] < floor:
            keep.pop(0)
        while len(keep) > 2 and counts.iloc[keep[-1]] < floor:
            keep.pop()
    trimmed = len(series) - len(keep)
    series, bounds = series.iloc[keep], bounds.iloc[keep]
    if len(series) < 2:
        return None

    values = [_num(v) or 0 for v in series.values]
    first, last = values[0], values[-1]
    change = round(((last - first) / first) * 100, 1) if first else None
    peak_idx = int(np.argmax(values))
    period = [str(pd.Timestamp(bounds["min"].min()).date()),
              str(pd.Timestamp(bounds["max"].max()).date())]
    return {
        "column": date_col, "measure": measure, "granularity": label,
        "labels": [str(pd.Timestamp(i).date()) for i in series.index],
        "values": values,
        "first": first, "last": last, "change_pct": change,
        "peak_label": str(pd.Timestamp(series.index[peak_idx]).date()),
        "peak_value": values[peak_idx],
        "period": period,
        "trimmed_periods": trimmed,
    }


def _breakdown(df: pd.DataFrame, dim: str, measure: str | None) -> dict | None:
    d = df.dropna(subset=[dim])
    if d.empty:
        return None
    if measure and measure in d.columns:
        numeric = d.assign(_m=pd.to_numeric(d[measure], errors="coerce")).groupby(dim)["_m"]
        rate = is_rate(measure)
        grouped = (numeric.mean() if rate else numeric.sum()) \
            .dropna().sort_values(ascending=False)
        kind = "avg" if rate else "sum"
    else:
        grouped = d.groupby(dim).size().sort_values(ascending=False)
        kind = "count"
    if grouped.empty:
        return None

    # «أخرى (فئة واحدة)» عبث — إن بقيت واحدة فقط نعرضها باسمها
    top = grouped.head(TOP_N + 1 if grouped.size == TOP_N + 1 else TOP_N)
    total = float(grouped.sum())
    values = [_num(v) or 0 for v in top.values]
    others = _num(total - sum(values)) if grouped.size > TOP_N else None
    # نسبة الصفوف المصنّفة فعلاً — نسبةٌ محسوبة على 40% من البيانات يجب أن تُعلن
    coverage = round(100 * len(d) / len(df), 1) if len(df) else 100.0
    return {
        "column": dim, "measure": measure if kind != "count" else None, "kind": kind,
        "labels": [str(i) for i in top.index],
        "values": values,
        "values_pct": [round(100 * float(v) / total, 1) if total else None
                       for v in values],
        "total": _num(total),
        "others": others if others and others > 0 else None,
        "leader": str(top.index[0]),
        "leader_value": _num(top.iloc[0]),
        # «حصة من مجموع المتوسطات» رقم بلا معنى — النِسَب للمجاميع والأعداد فقط
        "leader_share_pct": (round(100 * float(top.iloc[0]) / total, 1)
                             if total and kind != "avg" else None),
        "categories": int(grouped.size),
        "coverage_pct": coverage,
    }


def analyze_business(df: pd.DataFrame, overrides: dict | None = None) -> dict:
    """تحليل تنفيذي لجدول/ملف واحد: مؤشرات + اتجاه + توزيعات."""
    df = df.copy()
    for col in df.columns:                       # تواريخ مخزّنة كنص
        if df[col].dtype == object:
            try:
                df[col] = pd.to_datetime(df[col], errors="raise", format="mixed")
            except Exception:
                pass

    semantics = detect_semantics(df)
    overrides = overrides or {}
    measure = overrides.get("measure") or (semantics["measures"][0]
                                           if semantics["measures"] else None)
    date_col = overrides.get("date") or (semantics["dates"][0]
                                         if semantics["dates"] else None)
    dims = overrides.get("dimensions") or semantics["dimensions"][:3]

    trend = _trend(df, date_col, measure) if date_col else None

    # بُعدان مختلفا الاسم قد يعطيان الأرقام نفسها (عمودان متطابقان في الملف)
    # — رسمان متطابقان بعنوانين مختلفين يفضحان التقرير، فنُبقي الأول فقط.
    breakdowns, seen = [], set()
    for d in dims:
        b = _breakdown(df, d, measure)
        if not b:
            continue
        signature = (tuple(b["labels"]), tuple(b["values"]))
        if signature in seen:
            continue
        seen.add(signature)
        breakdowns.append(b)

    return {
        "semantics": {**semantics, "chosen": {
            "measure": measure, "date": date_col, "dimensions": dims}},
        "kpis": _kpis(df, measure),
        "trend": trend,
        "breakdowns": breakdowns,
    }


# مفردات الحقائق بلغة التقرير — النموذج يردّد ما يُعطى، فيجب أن يُعطى بلغته
_FACT_WORDS = {
    "ar": {
        "records": "عدد السجلات", "total": "إجمالي {m}", "average": "متوسط {m}",
        "highest": "أعلى قيمة لـ{m}",
        "period": "الفترة من {a} إلى {b}",
        "change": "أول قيمة = {first}، آخر قيمة = {last}",
        "changePct": "، نسبة التغير = {pct}%",
        "peak": "الذروة في {label} = {value}",
        "by": "حسب {dim}: {n} فئة، المتصدر «{leader}» = {value}",
        "share": " ({pct}% من الإجمالي)",
        "scope": " (محسوبة على {pct}% من الصفوف التي تحمل قيمة)",
        "top": "أعلى قيم {dim}: {pairs}",
    },
    "en": {
        "records": "records", "total": "total of {m}", "average": "average of {m}",
        "highest": "highest of {m}",
        "period": "period from {a} to {b}",
        "change": "first value = {first}, last = {last}",
        "changePct": ", change = {pct}%",
        "peak": "peak at {label} = {value}",
        "by": "by {dim}: {n} categories, top is '{leader}' = {value}",
        "share": " ({pct}% of total)",
        "scope": " (computed on the {pct}% of rows that have a value)",
        "top": "top {dim} values: {pairs}",
    },
}


def facts_from_business(business: dict, table: str | None = None,
                        labels: dict | None = None,
                        language: str = "en") -> list[str]:
    """قائمة حقائق مرقّمة تُمرَّر للنموذج — لا يُسمح له بأرقام خارجها.

    الأعمدة تُذكر بتسميتها الوصفية، والمفردات بلغة التقرير، حتى يكتب النموذج
    لغة أعمال سليمة لا مزيجاً من أسماء الأعمدة ومصطلحات إنجليزية.
    """
    labels = labels or {}
    w = _FACT_WORDS.get(language, _FACT_WORDS["en"])
    lbl = lambda c: labels.get(c, c)          # noqa: E731
    prefix = f"[{lbl(table)}] " if table else ""
    facts: list[str] = []

    for k in business["kpis"]:
        name = w[k["key"]].format(m=lbl(k["column"])) if k.get("column") else w[k["key"]]
        facts.append(f"{prefix}{name} = {k['value']}")

    tr = business.get("trend")
    if tr:
        facts.append(prefix + w["period"].format(a=tr["period"][0], b=tr["period"][1]))
        facts.append(prefix + w["change"].format(first=tr["first"], last=tr["last"])
                     + (w["changePct"].format(pct=tr["change_pct"])
                        if tr["change_pct"] is not None else ""))
        facts.append(prefix + w["peak"].format(label=tr["peak_label"],
                                               value=tr["peak_value"]))

    for b in business.get("breakdowns", []):
        scope = ("" if b.get("coverage_pct", 100) >= 95
                 else w["scope"].format(pct=b["coverage_pct"]))
        share = (w["share"].format(pct=b["leader_share_pct"])
                 if b["leader_share_pct"] is not None else "")
        facts.append(prefix + w["by"].format(
            dim=lbl(b["column"]), n=b["categories"], leader=b["leader"],
            value=b["leader_value"]) + share + scope)
        if b["categories"] > 2:
            pairs = ", ".join(f"{l}={v}" for l, v in zip(b["labels"][:5], b["values"][:5]))
            facts.append(prefix + w["top"].format(dim=lbl(b["column"]), pairs=pairs))

    return facts
