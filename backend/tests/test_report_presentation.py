"""ما يجعل التقرير يبدو معدّاً لا مولّداً: عناوين نظيفة وشكل رسم يناسب البيانات."""
import io

import pandas as pd

from app.api.reports_routes import _clean_title
from app.db.transfer import read_upload
from app.reports.builder import chart_plan
from app.reports.business import analyze_business


def test_report_title_drops_file_extension_and_copy_suffix():
    assert _clean_title("تقرير الأداء.XLSX-2", "x") == "تقرير الأداء"
    assert _clean_title("sales.csv", "x") == "sales"
    assert _clean_title("data (3).xlsx", "x") == "data"
    assert _clean_title("   ", "احتياطي") == "احتياطي"
    assert _clean_title("تقرير الربع الأول", "x") == "تقرير الربع الأول"


def test_excel_headers_are_normalised():
    """خلية عنوان بسطرين تنتج اسماً مبتوراً يتكرر في كل عنوان بالتقرير."""
    buf = io.BytesIO()
    pd.DataFrame({"القيمة في ال\nشهر": [10.0], "وحدة  القياس": ["أ"]}) \
        .to_excel(buf, index=False)
    df = next(iter(read_upload("f.xlsx", buf.getvalue()).values()))
    assert list(df.columns) == ["القيمة في الشهر", "وحدة القياس"]


def _plan(df, variant="dashboard", overrides=None):
    business = {"t": analyze_business(df, overrides)}
    return chart_plan(business, variant, "ar")


def test_few_categories_get_a_doughnut_many_get_bars():
    small = pd.DataFrame({"city": ["أ", "ب", "ج"] * 20, "amount": [10.0] * 60})
    types = [c["type"] for c in _plan(small)]
    assert "doughnut" in types

    wide = pd.DataFrame({"city": [f"c{i % 12}" for i in range(120)],
                         "amount": [10.0] * 120})
    assert [c["type"] for c in _plan(wide)] == ["hbar"]


def test_trend_is_the_hero_area_chart():
    df = pd.DataFrame({"order_date": pd.date_range("2025-01-01", periods=120, freq="D"),
                       "amount": [10.0] * 120})
    hero = _plan(df)[0]
    assert hero["type"] == "line_area" and hero["hero"] and hero["slot"] == 8
    assert hero["granularity"] == "month"          # المحور يُنسَّق شهوراً لا تواريخ خام


def test_top_categories_chart_shows_an_others_slice():
    df = pd.DataFrame({"city": [f"c{i % 15}" for i in range(150)],
                       "amount": [10.0] * 150})
    chart = _plan(df)[0]
    assert "أخرى" in chart["labels"][-1]
    assert len(chart["labels"]) == 9               # أفضل 8 + أخرى


def test_user_chart_choice_wins_over_the_rule():
    df = pd.DataFrame({"city": [f"c{i % 12}" for i in range(120)],
                       "amount": [10.0] * 120})
    business = {"t": analyze_business(df)}
    plan = chart_plan(business, "dashboard", "ar", requested=[
        {"table": "t", "kind": "breakdown", "column": "city", "type": "donut"}])
    assert [c["type"] for c in plan] == ["doughnut"]


def test_requesting_no_charts_yields_none():
    df = pd.DataFrame({"city": ["أ", "ب"] * 20, "amount": [10.0] * 40})
    assert chart_plan({"t": analyze_business(df)}, "dashboard", "ar",
                      requested=[]) == []


def test_only_one_hero_and_no_chart_is_dropped():
    """كل جدول قد يحمل اتجاهاً — والقالب يعرض رئيسياً واحداً، فلا يضيع الباقي."""
    from app.reports.builder import GRID, build_report_html
    frames = {}
    for name in ("أ", "ب"):
        frames[name] = analyze_business(pd.DataFrame({
            "تاريخ": pd.date_range("2025-01-01", periods=120, freq="D"),
            "فئة": [f"c{i % 6}" for i in range(120)],
            "قيمة": [10.0] * 120,
        }))
    plan = chart_plan(frames, "dashboard", "ar")
    assert sum(1 for c in plan if c["hero"]) == 1
    html = build_report_html(
        title="ت", profile={"kind": "multi", "overview": {"rows": 240, "cols": 3},
                            "datasets": [], "relationships": [], "business": frames},
        insights={"summary": "س", "findings": ["ن"], "recommendations": []},
        language="ar", variant="dashboard", source_name="x", model_label="m",
        created_at="2026-01-01 00:00", charts=plan)
    for c in plan:
        assert f'id="{c["id"]}"' in html, c["heading"]
