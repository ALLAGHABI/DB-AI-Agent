import pandas as pd
import pytest

from app.reports.analyzer import profile_df
from app.reports.builder import build_report_html
from app.reports.exporter import to_xlsx
from app.reports.store import ReportStore


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
    with pytest.raises(ValueError):
        _build(profile, insights, variant="fancy")


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
    with pytest.raises(LookupError):
        store.get_file(rid, "pdf")
    store.delete(rid)
    assert store.list() == []


def test_temp_token_roundtrip(tmp_path):
    store = ReportStore(str(tmp_path))
    df = pd.DataFrame({"a": [1, 2]})
    token = store.save_temp(df, "x.csv")
    df2, name = store.load_temp(token)
    assert name == "x.csv" and len(df2) == 2
    with pytest.raises(LookupError):
        store.load_temp("missing")
