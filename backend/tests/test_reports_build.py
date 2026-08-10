import pandas as pd
import pytest

from app.reports.analyzer import profile_df
from app.reports.builder import build_report_html
from app.reports.exporter import to_xlsx
from app.reports.store import ReportStore
from app.errors import AppError, NotFoundError


@pytest.fixture
def profile():
    df = pd.DataFrame({
        "city": ["الرياض", "جدة", "الرياض", "الدمام"] * 25,
        "amount": [100.5, 200, 150, 80] * 25,
    })
    return profile_df(df)


@pytest.fixture
def insights():
    return {"summary": "ملخص تجريبي للبيانات",
            "findings": ["الرياض الأعلى مبيعاً"],
            "recommendations": ["ركز على الرياض"]}


def _build(profile, insights, **kw):
    args = dict(title="تقرير المبيعات", profile=profile, insights=insights,
                language="ar", variant="detailed", source_name="sales.csv",
                model_label="ollama/gemma3:4b", created_at="2026-08-09 12:00")
    args.update(kw)
    return build_report_html(**args)


def test_html_rtl_and_content(profile, insights):
    html = _build(profile, insights)
    assert 'dir="rtl"' in html
    assert "تقرير المبيعات" in html
    assert "ملخص تجريبي" in html
    assert "الرياض الأعلى مبيعاً" in html
    assert "const CHARTS" in html            # بيانات الرسوم مضمنة
    assert "Chart" in html                    # مكتبة الرسوم مضمنة (ذاتي الاكتفاء)


def test_html_english_ltr(profile, insights):
    html = _build(profile, insights, language="en", title="Sales Report")
    assert 'dir="ltr"' in html and "Executive Summary" in html


def test_executive_variant_caps_charts(profile, insights):
    html = _build(profile, insights, variant="executive")
    assert html.count('<canvas id="ch-') <= 3


def test_dashboard_omits_recommendations_by_default(profile, insights):
    """لوحة المؤشرات سطح مراقبة لا مذكرة — التوصيات ليست جزءاً منها افتراضياً."""
    html = _build(profile, insights, variant="dashboard")
    assert "ركز على الرياض" not in html
    assert "الرياض الأعلى مبيعاً" in html          # النتائج تظهر في الشريط الجانبي


def test_invalid_variant_rejected(profile, insights):
    with pytest.raises(AppError) as e:
        _build(profile, insights, variant="fancy")
    assert e.value.code == "unknownTemplate"


def test_xlsx_has_sheets_and_magic(profile, insights):
    data = to_xlsx(profile, insights, "ar")
    assert data[:2] == b"PK"                  # zip/xlsx magic
    import io

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data))
    assert set(wb.sheetnames) == {"ملخص", "الأعمدة"}      # لا ورقة «عينة» بعد اليوم


def test_store_roundtrip(tmp_path, profile, insights):
    store = ReportStore(str(tmp_path))
    html = _build(profile, insights)
    xlsx = to_xlsx(profile, insights, "ar")
    rid = store.create({"title": "t", "created_at": "2026-08-09"}, html, xlsx, None)
    metas = store.list()
    assert metas[0]["id"] == rid and metas[0]["pdf"] is False
    assert store.get_file(rid, "html").decode("utf-8") == html
    with pytest.raises(NotFoundError):
        store.get_file(rid, "pdf")
    store.delete(rid)
    assert store.list() == []


def test_temp_token_roundtrip(tmp_path):
    store = ReportStore(str(tmp_path))
    df = pd.DataFrame({"a": [1, 2]})
    token = store.save_temp(df, "x.csv")
    saved = store.load_temp(token)
    assert saved["source_name"] == "x.csv" and saved["kind"] == "single"
    assert len(next(iter(saved["frames"].values()))) == 2
    with pytest.raises(NotFoundError) as e:
        store.load_temp("missing")
    assert e.value.code == "analysisExpired"


# ---------- التقرير التنفيذي: أرقام أعمال بلا تفاصيل تقنية ----------

@pytest.fixture
def business_profile():
    import pandas as pd
    from app.reports.business import analyze_business
    df = pd.DataFrame({
        "order_date": pd.date_range("2025-01-01", periods=60, freq="D"),
        "city": ["الرياض"] * 40 + ["جدة"] * 20,
        "total_amount": [500.0] * 40 + [250.0] * 20,
    })
    profile = profile_df(df)
    profile["business"] = {"orders": analyze_business(df)}
    return profile


def test_executive_shows_business_kpis(business_profile, insights):
    html = _build(business_profile, insights, variant="executive")
    assert "إجمالي" in html and "متوسط" in html          # مؤشرات أعمال
    assert "25,000" in html                              # 40×500 + 20×250
    assert "city" in html                                # رسم توزيع


def test_executive_hides_technical_internals(business_profile, insights):
    html = _build(business_profile, insights, variant="executive")
    for technical in ("قيم مفقودة", "صفوف مكررة", "تفاصيل الأعمدة", "عينة من البيانات",
                      "قاموس البيانات"):
        assert technical not in html, technical


def test_data_sample_and_column_cards_are_gone_everywhere(business_profile, insights):
    """قسمان كانا يفضحان التقرير: بطاقات الأعمدة وعينة صفوف خام (وفيها بيانات أفراد)."""
    for variant in ("executive", "dashboard", "detailed"):
        html = _build(business_profile, insights, variant=variant)
        assert "عينة من البيانات" not in html
        assert "تفاصيل الأعمدة" not in html
        assert "col-card" not in html


def test_detailed_replaces_them_with_dictionary_and_ranks(business_profile, insights):
    html = _build(business_profile, insights, variant="detailed")
    assert "قاموس البيانات" in html                      # ملحق مضغوط بدل البطاقات
    assert "تعمّق حسب" in html                            # جداول ترتيب بدل العينة
    assert "جودة البيانات" in html                        # سطر واحد لا قسم


def test_three_templates_are_visibly_different(business_profile, insights):
    exec_html = _build(business_profile, insights, variant="executive")
    dash = _build(business_profile, insights, variant="dashboard")
    detail = _build(business_profile, insights, variant="detailed")
    assert "موجز تنفيذي" in exec_html and "cover" in exec_html
    assert "لوحة مؤشرات" in dash and "grid12" in dash and "landscape" in dash
    assert "تقرير تحليلي مفصّل" in detail and "القسم 1" in detail
    assert len({exec_html, dash, detail}) == 3


def test_hidden_section_is_not_rendered(business_profile, insights):
    html = _build(business_profile, insights, variant="detailed",
                  sections=["charts"])
    assert "ملخص تجريبي" not in html
    assert "الرياض الأعلى مبيعاً" not in html
    assert "ركز على الرياض" not in html
    assert '<canvas id="ch-' in html                     # الرسوم وحدها بقيت


def test_every_requested_chart_is_rendered(business_profile, insights):
    """المستخدم اختار ثلاثة رسوم — القالب لا يبتلع واحداً منها بصمت."""
    from app.reports.builder import chart_plan
    plan = chart_plan(business_profile["business"], "executive", "ar")
    html = _build(business_profile, insights, variant="executive", charts=plan)
    for c in plan:
        assert f'id="{c["id"]}"' in html, c["heading"]


def test_charts_section_off_removes_every_canvas(business_profile, insights):
    html = _build(business_profile, insights, variant="dashboard",
                  sections=["summary", "findings"])
    assert "<canvas" not in html
    assert "ملخص تجريبي" in html


def test_dropped_claims_are_disclosed(business_profile, insights):
    html = _build(business_profile, {**insights, "dropped_claims": 2})
    assert "أرقاماً غير موجودة" in html
