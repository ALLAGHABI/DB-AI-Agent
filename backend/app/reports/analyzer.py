"""تحليل DataFrame — إحصاءات، قيم مفقودة، شواذ، ارتباطات، ومواصفات رسوم تلقائية.

المخرجات كلها أنواع بايثون أصلية قابلة للتسلسل JSON.
"""
import numpy as np
import pandas as pd


def _py(v):
    """تحويل أنواع numpy/pandas إلى أنواع بايثون أصلية."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return round(float(v), 4)
    if isinstance(v, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(v).date())
    return str(v) if not isinstance(v, (int, float, str, bool)) else v


def _column_profile(name: str, s: pd.Series) -> dict:
    nulls = int(s.isna().sum())
    base = {"name": name, "nulls": nulls, "unique": int(s.nunique(dropna=True))}

    if pd.api.types.is_datetime64_any_dtype(s):
        base["kind"] = "datetime"
        if s.notna().any():
            base["min"] = _py(s.min())
            base["max"] = _py(s.max())
        return base

    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        clean = s.dropna()
        base["kind"] = "numeric"
        if len(clean):
            q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
            iqr = q3 - q1
            outliers = int(((clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)).sum())
            base.update({
                "mean": _py(clean.mean()), "std": _py(clean.std()),
                "min": _py(clean.min()), "max": _py(clean.max()),
                "median": _py(clean.median()), "outliers": outliers,
            })
        else:
            base.update({"mean": None, "std": None, "min": None, "max": None,
                         "median": None, "outliers": 0})
        return base

    # فئوي / نصي
    base["kind"] = "categorical"
    vc = s.dropna().astype(str).value_counts().head(10)
    base["top_values"] = [{"value": str(k), "count": int(v)} for k, v in vc.items()]
    return base


def _charts(df: pd.DataFrame, columns: list[dict], max_charts: int) -> list[dict]:
    charts: list[dict] = []

    # سلسلة زمنية: أول عمود تاريخ + أول عمود رقمي
    dt_cols = [c["name"] for c in columns if c["kind"] == "datetime"]
    num_cols = [c["name"] for c in columns if c["kind"] == "numeric"]
    cat_cols = [c["name"] for c in columns
                if c["kind"] == "categorical" and 1 < c["unique"] <= 30]

    if dt_cols and num_cols and len(charts) < max_charts:
        dt, num = dt_cols[0], num_cols[0]
        grouped = (df.dropna(subset=[dt])
                   .groupby(pd.Grouper(key=dt, freq="ME"))[num].sum())
        if len(grouped) < 3:
            grouped = (df.dropna(subset=[dt])
                       .groupby(pd.Grouper(key=dt, freq="D"))[num].sum())
        charts.append({
            "type": "line", "title": f"{num} / {dt}",
            "labels": [str(pd.Timestamp(i).date()) for i in grouped.index],
            "values": [_py(v) or 0 for v in grouped.values],
        })

    for name in cat_cols:
        if len(charts) >= max_charts:
            break
        vc = df[name].dropna().astype(str).value_counts().head(10)
        charts.append({
            "type": "bar", "title": name,
            "labels": [str(k) for k in vc.index],
            "values": [int(v) for v in vc.values],
        })

    for name in num_cols:
        if len(charts) >= max_charts:
            break
        clean = df[name].dropna()
        if clean.nunique() < 5:
            continue
        counts, edges = np.histogram(clean, bins=min(12, max(5, int(np.sqrt(len(clean))))))
        charts.append({
            "type": "histogram", "title": name,
            "labels": [f"{_py(edges[i])}–{_py(edges[i+1])}" for i in range(len(counts))],
            "values": [int(c) for c in counts],
        })

    return charts[:max_charts]


def profile_df(df: pd.DataFrame, max_charts: int = 6) -> dict:
    # محاولة اكتشاف أعمدة تاريخ مخزنة كنص
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            try:
                converted = pd.to_datetime(df[col], errors="raise", format="mixed")
                df[col] = converted
            except Exception:
                pass

    columns = [_column_profile(str(c), df[c]) for c in df.columns]

    total_cells = int(df.shape[0] * df.shape[1]) or 1
    missing = int(df.isna().sum().sum())
    overview = {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "missing_pct": round(100 * missing / total_cells, 2),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 1),
    }

    correlations = []
    nums = df.select_dtypes(include=[np.number])
    if nums.shape[1] >= 2:
        corr = nums.corr(numeric_only=True)
        for i, a in enumerate(corr.columns):
            for b in corr.columns[i + 1:]:
                r = corr.loc[a, b]
                if pd.notna(r) and abs(r) >= 0.5:
                    correlations.append({"a": str(a), "b": str(b), "r": round(float(r), 3)})

    return {
        "overview": overview,
        "columns": columns,
        "correlations": correlations,
        "charts": _charts(df, columns, max_charts),
        "sample": [[_py(v) for v in row] for row in df.head(10).values],
        "sample_columns": [str(c) for c in df.columns],
    }
