import numpy as np
import pandas as pd
import pytest

from app.reports.business import (
    analyze_business, detect_semantics, facts_from_business,
)


@pytest.fixture
def sales():
    rng = np.random.default_rng(3)
    n = 120
    return pd.DataFrame({
        "order_id": range(1, n + 1),
        "order_date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "city": rng.choice(["الرياض", "جدة", "الدمام"], n, p=[0.6, 0.25, 0.15]),
        "status": rng.choice(["completed", "cancelled"], n, p=[0.85, 0.15]),
        "total_amount": rng.integers(100, 900, n).astype(float),
        "quantity": rng.integers(1, 5, n),
    })


def test_detects_measure_date_and_dimensions(sales):
    sem = detect_semantics(sales)
    assert sem["measures"][0] == "total_amount"      # تلميح الاسم يرفع ترتيبه
    assert "order_id" not in sem["measures"]         # معرف — ليس مقياساً
    assert sem["dates"] == ["order_date"]
    assert "city" in sem["dimensions"] and "status" in sem["dimensions"]


def test_kpis_are_real_numbers(sales):
    b = analyze_business(sales)
    kpis = {k["key"]: k["value"] for k in b["kpis"]}
    assert kpis["records"] == 120
    assert kpis["total"] == pytest.approx(sales["total_amount"].sum(), rel=1e-6)
    assert kpis["average"] == pytest.approx(sales["total_amount"].mean(), abs=0.01)
    assert kpis["highest"] == sales["total_amount"].max()


def test_trend_has_direction_and_peak(sales):
    b = analyze_business(sales)
    tr = b["trend"]
    assert tr["column"] == "order_date" and tr["measure"] == "total_amount"
    assert tr["granularity"] == "month"              # 120 يوماً ⇒ تجميع شهري
    assert len(tr["labels"]) == len(tr["values"]) >= 2
    assert tr["peak_value"] == max(tr["values"])
    assert tr["period"][0] == "2025-01-01"


def test_breakdown_leader_matches_data(sales):
    b = analyze_business(sales)
    city = next(x for x in b["breakdowns"] if x["column"] == "city")
    expected = sales.groupby("city")["total_amount"].sum().idxmax()
    assert city["leader"] == expected
    assert 0 < city["leader_share_pct"] <= 100


def test_overrides_win_over_detection(sales):
    b = analyze_business(sales, {"measure": "quantity", "dimensions": ["status"]})
    assert b["semantics"]["chosen"]["measure"] == "quantity"
    assert [x["column"] for x in b["breakdowns"]] == ["status"]
    total = {k["key"]: k["value"] for k in b["kpis"]}["total"]
    assert total == pytest.approx(sales["quantity"].sum())


def test_facts_are_grounded_strings(sales):
    b = analyze_business(sales)
    facts = facts_from_business(b, table="orders")
    assert all(f.startswith("[orders] ") for f in facts)
    joined = " ".join(facts)
    assert "total of total_amount" in joined
    assert "by city" in joined and "peak at" in joined


def test_handles_data_without_dates_or_measures():
    df = pd.DataFrame({"name": ["أ", "ب", "أ"], "note": ["x", "y", "z"]})
    b = analyze_business(df)
    assert b["trend"] is None
    assert {k["key"] for k in b["kpis"]} == {"records"}
    assert b["breakdowns"][0]["kind"] == "count"     # بلا مقياس ⇒ عدّ


def test_empty_frame_is_safe():
    b = analyze_business(pd.DataFrame({"a": []}))
    assert b["kpis"][0]["value"] == 0 and b["trend"] is None


def test_near_unique_columns_are_not_dimensions():
    """عنوان الشحن مختلف لكل صف — رسم توزيع عليه بلا فائدة."""
    df = pd.DataFrame({
        "shipping_address": [f"عنوان {i}" for i in range(40)],
        "status": ["pending"] * 20 + ["shipped"] * 20,
        "total_amount": [100.0] * 40,
    })
    sem = detect_semantics(df)
    assert "shipping_address" not in sem["dimensions"]
    assert "status" in sem["dimensions"]


def test_high_cardinality_is_capped():
    df = pd.DataFrame({"code": [f"c{i % 45}" for i in range(200)]})
    assert detect_semantics(df)["dimensions"] == []      # 45 فئة > الحد
