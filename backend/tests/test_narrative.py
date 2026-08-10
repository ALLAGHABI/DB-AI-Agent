import pandas as pd
import pytest

from app.reports.business import analyze_business
from app.reports.insights import generate_insights
from app.reports.narrative import compose_narrative

LABELS = {"total_amount": "قيمة المبيعات", "city": "المدينة", "orders": "الطلبات"}


@pytest.fixture
def business():
    df = pd.DataFrame({
        "order_date": pd.date_range("2025-01-01", periods=90, freq="D"),
        "city": ["الرياض"] * 60 + ["جدة"] * 30,
        "total_amount": [400.0] * 60 + [100.0] * 30,
    })
    return {"orders": analyze_business(df)}


def test_narrative_is_written_in_arabic_from_numbers(business):
    out = compose_narrative(business, LABELS, "ar", subject="الطلبات")
    assert "يغطي هذا التقرير" in out["summary"] and "90" in out["summary"]
    joined = " ".join(out["findings"])
    assert "قيمة المبيعات" in joined and "27,000" in joined     # 60×400 + 30×100
    assert "الرياض" in joined
    assert out["recommendations"]
    assert not any(c.isascii() and c.isalpha() for c in out["summary"])


def test_narrative_english(business):
    out = compose_narrative(business, {"total_amount": "Sales value"}, "en")
    assert "This report covers" in out["summary"]
    assert "Sales value" in " ".join(out["findings"])


def test_narrative_flags_concentration(business):
    out = compose_narrative(business, LABELS, "ar")
    # الرياض تمثل 88.9% من المبيعات ⇒ توصية بمراجعة التركّز
    assert any("تركّز" in r for r in out["recommendations"])


class _Stubborn:
    """نموذج يصرّ على الإنجليزية مهما طُلب."""
    is_local = True

    def __init__(self):
        self.calls = 0

    async def chat(self, model, system, user, **kw):
        self.calls += 1

        class R:
            text = ("## SUMMARY\nThis report analyzes employee working hours "
                    "and reveals a substantial increase in total costs.\n")
        return R()


async def test_fallback_rescues_wrong_language(business):
    """إن عجز النموذج عن العربية مرتين، يُكتب التقرير من الأرقام."""
    fallback = compose_narrative(business, LABELS, "ar", subject="الطلبات")
    out = await generate_insights(_Stubborn(), "m", ["records = 90"], "ar",
                                  fallback=fallback)
    assert out["language_ok"] is True
    assert out["used_fallback"] is True
    assert "يغطي هذا التقرير" in out["summary"]
    assert out["findings"] and out["recommendations"]


class _SummaryOnly:
    is_local = True

    async def chat(self, model, system, user, **kw):
        class R:
            text = "## SUMMARY\nتغطي البيانات 90 سجلاً من الطلبات.\n"
        return R()


async def test_fallback_fills_missing_sections(business):
    """رد بلا نتائج ولا توصيات يُكمَّل من الأرقام بدل تقرير أعرج."""
    fallback = compose_narrative(business, LABELS, "ar")
    out = await generate_insights(_SummaryOnly(), "m", ["records = 90"], "ar",
                                  fallback=fallback)
    assert "تغطي البيانات" in out["summary"]      # ملخص النموذج محفوظ
    assert out["findings"] and out["recommendations"]
    assert out["used_fallback"] is True
