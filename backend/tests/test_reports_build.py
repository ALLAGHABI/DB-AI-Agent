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
    assert html.count('<canvas id="chart-') <= 3


def test_dashboard_variant_hides_findings(profile, insights):
    html = _build(profile, insights, variant="dashboard")
    assert "الرياض الأعلى مبيعاً" not in html


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
    assert set(wb.sheetnames) == {"ملخص", "الأعمدة", "عينة"}


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
    assert "الإجمالي" in html and "المتوسط" in html      # مؤشرات أعمال
    assert "25,000" in html                              # 40×500 + 20×250
    assert "حسب city" in html or "city" in html          # رسم توزيع


def test_executive_hides_technical_internals(business_profile, insights):
    html = _build(business_profile, insights, variant="executive")
    for technical in ("قيم مفقودة", "صفوف مكررة", "تفاصيل الأعمدة", "عينة من البيانات"):
        assert technical not in html, technical


def test_detailed_keeps_technical_appendix(business_profile, insights):
    html = _build(business_profile, insights, variant="detailed")
    assert "قيم مفقودة" in html and "تفاصيل الأعمدة" in html


def test_dropped_claims_are_disclosed(business_profile, insights):
    html = _build(business_profile, {**insights, "dropped_claims": 2})
    assert "أرقاماً غير موجودة" in html
