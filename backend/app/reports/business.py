"""محرك التحليل التنفيذي — يحوّل البيانات الخام إلى أرقام أعمال حقيقية.

الفرق عن analyzer.py: ذاك يصف *بنية* البيانات (أنواع، قيم فارغة، شواذ)،
وهذا يجيب أسئلة *الأعمال*: كم الإجمالي؟ ما الاتجاه؟ من الأفضل؟ أين تتركز؟

كل رقم هنا محسوب من البيانات فعلياً — ويُمرَّر للنموذج كقائمة حقائق
ليكتب فوقها بدل أن يخترع.
"""
import numpy as np
import pandas as pd

# تلميحات أسماء الأعمدة (عربي/إنجليزي) لاكتشاف الدلالة تلقائياً
_MEASURE_HINTS = ("amount", "total", "price", "revenue", "sales", "cost", "value",
                  "salary", "profit", "balance", "قيمة", "مبلغ", "سعر", "إجمالي",
                  "ايراد", "إيراد", "مبيعات", "راتب", "تكلفة")
_COUNT_HINTS = ("qty", "quantity", "count", "units", "stock", "عدد", "كمية", "مخزون")
_DIM_HINTS = ("city", "country", "region", "category", "type", "status", "state",
              "name", "product", "customer", "branch", "department", "gender",
              "مدينة", "دولة", "منطقة", "فئة", "نوع", "حالة", "اسم", "قسم", "فرع")

TOP_N = 8
MAX_TREND_POINTS = 24


def _is_identifier(name: str, series: pd.Series) -> bool:
    low = name.lower()
    if low == "id" or low.endswith(("_id", "-id")) or low.startswith("id_"):
        return True
    return bool(len(series) and series.nunique(dropna=True) == len(series)
                and pd.api.types.is_integer_dtype(series))


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
            if _is_identifier(name, s):
                continue
            score = 2 if any(h in low for h in _MEASURE_HINTS) else 0
            score += 1 if any(h in low for h in _COUNT_HINTS) else 0
            measures.append((score, name))
            continue

        unique = s.nunique(dropna=True)
        if 1 < unique <= max(50, len(s) * 0.5):
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
            out += [
                {"key": "total", "value": _num(s.sum()), "column": measure},
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
    series = series.tail(MAX_TREND_POINTS)
    if len(series) < 2:
        return None

    values = [_num(v) or 0 for v in series.values]
    first, last = values[0], values[-1]
    change = round(((last - first) / first) * 100, 1) if first else None
    peak_idx = int(np.argmax(values))
    return {
        "column": date_col, "measure": measure, "granularity": label,
        "labels": [str(pd.Timestamp(i).date()) for i in series.index],
        "values": values,
        "first": first, "last": last, "change_pct": change,
        "peak_label": str(pd.Timestamp(series.index[peak_idx]).date()),
        "peak_value": values[peak_idx],
        "period": [str(d[date_col].min().date()), str(d[date_col].max().date())],
    }


def _breakdown(df: pd.DataFrame, dim: str, measure: str | None) -> dict | None:
    d = df.dropna(subset=[dim])
    if d.empty:
        return None
    if measure and measure in d.columns:
        grouped = (d.assign(_m=pd.to_numeric(d[measure], errors="coerce"))
                   .groupby(dim)["_m"].sum().dropna().sort_values(ascending=False))
        kind = "sum"
    else:
        grouped = d.groupby(dim).size().sort_values(ascending=False)
        kind = "count"
    if grouped.empty:
        return None

    top = grouped.head(TOP_N)
    total = float(grouped.sum())
    return {
        "column": dim, "measure": measure if kind == "sum" else None, "kind": kind,
        "labels": [str(i) for i in top.index],
        "values": [_num(v) or 0 for v in top.values],
        "leader": str(top.index[0]),
        "leader_value": _num(top.iloc[0]),
        "leader_share_pct": round(100 * float(top.iloc[0]) / total, 1) if total else None,
        "categories": int(grouped.size),
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
    breakdowns = [b for b in (_breakdown(df, d, measure) for d in dims) if b]

    return {
        "semantics": {**semantics, "chosen": {
            "measure": measure, "date": date_col, "dimensions": dims}},
        "kpis": _kpis(df, measure),
        "trend": trend,
        "breakdowns": breakdowns,
    }


def facts_from_business(business: dict, table: str | None = None) -> list[str]:
    """قائمة حقائق مرقّمة تُمرَّر للنموذج — لا يُسمح له بأرقام خارجها."""
    prefix = f"[{table}] " if table else ""
    facts: list[str] = []

    for k in business["kpis"]:
        col = f" of {k['column']}" if k.get("column") else ""
        facts.append(f"{prefix}{k['key']}{col} = {k['value']}")

    tr = business.get("trend")
    if tr:
        facts.append(f"{prefix}period from {tr['period'][0]} to {tr['period'][1]}")
        facts.append(f"{prefix}first {tr['granularity']} value = {tr['first']}, "
                     f"last = {tr['last']}"
                     + (f", change = {tr['change_pct']}%" if tr["change_pct"] is not None else ""))
        facts.append(f"{prefix}peak at {tr['peak_label']} = {tr['peak_value']}")

    for b in business.get("breakdowns", []):
        facts.append(
            f"{prefix}by {b['column']}: {b['categories']} categories, "
            f"top is '{b['leader']}' = {b['leader_value']}"
            + (f" ({b['leader_share_pct']}% of total)"
               if b["leader_share_pct"] is not None else ""))
        pairs = ", ".join(f"{l}={v}" for l, v in zip(b["labels"][:5], b["values"][:5]))
        facts.append(f"{prefix}top {b['column']} values: {pairs}")

    return facts
