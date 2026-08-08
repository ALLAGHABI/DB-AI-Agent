import numpy as np
import pandas as pd

from app.reports.analyzer import profile_df


def _df():
    rng = np.random.default_rng(7)
    n = 200
    return pd.DataFrame({
        "order_id": range(1, n + 1),
        "amount": rng.normal(100, 20, n).round(2),
        "qty": rng.integers(1, 10, n),
        "city": rng.choice(["الرياض", "جدة", "الدمام"], n),
        "status": rng.choice(["completed", "pending", "cancelled"], n, p=[0.7, 0.2, 0.1]),
        "order_date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "note": [None] * 150 + ["ok"] * 50,
    })


def test_overview():
    p = profile_df(_df())
    assert p["overview"]["rows"] == 200
    assert p["overview"]["cols"] == 7
    assert p["overview"]["duplicate_rows"] == 0
    assert 0 < p["overview"]["missing_pct"] < 100


def test_numeric_column_stats():
    p = profile_df(_df())
    cols = {c["name"]: c for c in p["columns"]}
    amount = cols["amount"]
    assert amount["kind"] == "numeric"
    assert amount["nulls"] == 0
    assert 80 < amount["mean"] < 120
    assert amount["min"] < amount["max"]
    assert "std" in amount


def test_categorical_top_values():
    p = profile_df(_df())
    cols = {c["name"]: c for c in p["columns"]}
    city = cols["city"]
    assert city["kind"] == "categorical"
    assert len(city["top_values"]) <= 10
    assert sum(v["count"] for v in city["top_values"]) == 200


def test_datetime_detected():
    p = profile_df(_df())
    cols = {c["name"]: c for c in p["columns"]}
    assert cols["order_date"]["kind"] == "datetime"


def test_missing_and_outliers():
    p = profile_df(_df())
    cols = {c["name"]: c for c in p["columns"]}
    assert cols["note"]["nulls"] == 150
    assert "outliers" in cols["amount"]          # IQR count موجود للأرقام


def test_correlations_only_strong_pairs():
    df = _df()
    df["amount2"] = df["amount"] * 2 + 1          # ارتباط تام
    p = profile_df(df)
    pairs = {(c["a"], c["b"]) for c in p["correlations"]}
    assert ("amount", "amount2") in pairs or ("amount2", "amount") in pairs
    for c in p["correlations"]:
        assert abs(c["r"]) >= 0.5


def test_chart_specs_capped_and_typed():
    p = profile_df(_df(), max_charts=6)
    assert 0 < len(p["charts"]) <= 6
    kinds = {c["type"] for c in p["charts"]}
    assert kinds <= {"histogram", "bar", "line"}
    for c in p["charts"]:
        assert c["labels"] and c["values"]
        assert len(c["labels"]) == len(c["values"])


def test_json_serializable():
    import json
    json.dumps(profile_df(_df()))


def test_identifier_columns_excluded_from_charts():
    p = profile_df(_df())
    titles = " ".join(c["title"] for c in p["charts"])
    assert "order_id" not in titles          # عمود معرف — لا يُرسم
    assert "amount" in titles                 # العمود الرقمي الحقيقي يُرسم
