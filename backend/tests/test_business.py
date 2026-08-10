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


def test_facts_speak_the_report_language(sales):
    """النموذج يردّد ما يُعطى — فحقائق إنجليزية تُسرّب «records» إلى تقرير عربي."""
    facts = facts_from_business(analyze_business(sales), table="orders",
                                labels={"city": "المدينة", "total_amount": "المبيعات"},
                                language="ar")
    joined = " ".join(facts)
    assert "عدد السجلات" in joined and "إجمالي المبيعات" in joined
    assert "حسب المدينة" in joined and "الذروة" in joined
    assert "records" not in joined and "categories" not in joined


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


def test_arabic_identifier_columns_are_not_measures():
    """«رقم المرجع» رقم لا يُجمع ولا يُرسم عبر الزمن — وجمعه فضيحة تحليلية."""
    df = pd.DataFrame({
        "رقم المرجع": [10000 + i for i in range(30)],
        "كود الوحدة": [100 + i % 5 for i in range(30)],
        "تكلفة التشغيل": [200.0 + i for i in range(30)],
    })
    sem = detect_semantics(df)
    assert "رقم المرجع" not in sem["measures"]
    assert "كود الوحدة" not in sem["measures"]
    assert sem["measures"] == ["تكلفة التشغيل"]


def test_incomplete_edge_period_does_not_fake_a_collapse():
    """شهر أخير فيه صفّان يُقرأ «انخفاض 98%» — نُسقط الفترة الطرفية المبتورة."""
    full = pd.DataFrame({
        "order_date": list(pd.date_range("2025-01-01", periods=90, freq="D")),
        "total_amount": [1000.0] * 90,
    })
    tail = pd.DataFrame({"order_date": [pd.Timestamp("2025-05-02")],
                         "total_amount": [50.0]})
    b = analyze_business(pd.concat([full, tail], ignore_index=True))
    tr = b["trend"]
    assert tr["trimmed_periods"] >= 1                # مايو (وأبريل الفارغ) خارج الحساب
    assert 50.0 not in tr["values"]
    assert tr["period"][1] == "2025-03-31"
    assert abs(tr["change_pct"]) < 50               # لا انهيار وهمي


def test_breakdown_declares_its_scope_and_others():
    df = pd.DataFrame({
        "city": [f"c{i}" for i in range(10)] * 4 + [None] * 60,
        "total_amount": [10.0] * 100,
    })
    bd = analyze_business(df)["breakdowns"][0]
    assert bd["coverage_pct"] == 40.0                # 40 صفاً من 100
    assert bd["others"] is not None                  # 10 فئات > TOP_N
    assert sum(bd["values_pct"]) < 100.0


def test_free_text_and_contact_columns_are_never_dimensions():
    """«التوزيع حسب البريد الإلكتروني» رسم بلا معنى — ويكشف أفراداً."""
    df = pd.DataFrame({
        "البريد الإلكتروني": ["a@x.com", "b@x.com"] * 15,
        "عنوان الشحن": ["ش. الملك", "ش. العليا"] * 15,
        "الوصف": ["طويل", "قصير"] * 15,
        "المدينة": ["الرياض", "جدة"] * 15,
    })
    assert detect_semantics(df)["dimensions"] == ["المدينة"]


def test_identical_dimensions_are_not_charted_twice():
    df = pd.DataFrame({
        "الحالة": ["مكتمل"] * 30 + ["ملغي"] * 10,
        "الوضع": ["مكتمل"] * 30 + ["ملغي"] * 10,
        "المبلغ": [5.0] * 40,
    })
    b = analyze_business(df, {"dimensions": ["الحالة", "الوضع"]})
    assert len(b["breakdowns"]) == 1


def test_boolean_flags_are_never_measures():
    """«متوسط نشط 0.9» و«تطور نشط عبر الزمن» هراء يفضح التقرير."""
    df = pd.DataFrame({
        "is_active": [1, 0, 1, 1] * 10,
        "registered_at": pd.date_range("2025-01-01", periods=40, freq="D"),
        "total_amount": [50.0] * 40,
    })
    sem = detect_semantics(df)
    assert "is_active" not in sem["measures"]
    assert sem["measures"] == ["total_amount"]


def test_rates_are_averaged_not_summed():
    """جمع أسعار الوحدات يعطي رقماً بلا معنى — والنسبة منه أسوأ."""
    df = pd.DataFrame({
        "product": ["آيفون", "شاحن"] * 20,
        "unit_price": [4000.0, 50.0] * 20,
    })
    b = analyze_business(df)
    kpis = {k["key"] for k in b["kpis"]}
    assert "total" not in kpis and "average" in kpis
    bd = b["breakdowns"][0]
    assert bd["kind"] == "avg"
    assert bd["values"][0] == 4000.0                 # متوسط لا مجموع
    assert bd["leader_share_pct"] is None            # لا نِسَب على المتوسطات
