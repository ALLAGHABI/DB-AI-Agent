from app.reports.insights import (
    build_insights_prompt, detect_language, generate_insights, language_matches,
    parse_insights, strip_ungrounded, ungrounded_numbers,
)

FACTS = [
    "records = 120",
    "total of total_amount = 58400",
    "average of total_amount = 486.67",
    "by city: 3 categories, top is 'الرياض' = 35100 (60.1% of total)",
]


def test_prompt_carries_facts_and_language():
    system, user = build_insights_prompt(FACTS, "ar", subject="orders")
    assert "العربية" in system or "Arabic" in system
    assert "58400" in user and "1. records = 120" in user
    assert "orders" in user
    # التقرير التنفيذي لا يتحدث عن البنية
    assert "never about" in system and "relationships" in system


def test_parse_full_sections():
    text = """## SUMMARY
البيانات تغطي 120 طلباً بإجمالي 58400.

## FINDINGS
- الرياض تتصدر بـ 35100
- متوسط الطلب 486.67

## RECOMMENDATIONS
- ركّز على الرياض
"""
    out = parse_insights(text)
    assert "120" in out["summary"]
    assert len(out["findings"]) == 2 and len(out["recommendations"]) == 1


def test_detect_language():
    assert detect_language("هذا تقرير عن المبيعات في الرياض") == "ar"
    assert detect_language("This dataset represents online orders") == "en"


def test_language_matches_flags_wrong_language():
    english = {"summary": "This dataset represents a database of online orders and customers.",
               "findings": ["Order volume increased"], "recommendations": []}
    assert language_matches(english, "en") is True
    assert language_matches(english, "ar") is False


def test_rounding_is_tolerated_but_invention_is_not():
    rounded = {
        "summary": "الإجمالي 58400 وهو جيد.",
        "findings": ["الرياض تستحوذ على 60% تقريباً", "متوسط الطلب 487"],
        "recommendations": [],
    }
    # 60 تقريب لـ60.1 و487 تقريب لـ486.67 — كلاهما مدعوم
    assert ungrounded_numbers(rounded, FACTS) == []

    invented = {"summary": "", "findings": ["الإيراد بلغ 999999 ريال"],
                "recommendations": []}
    assert "999999" in ungrounded_numbers(invented, FACTS)


def test_strip_ungrounded_removes_invented_claims():
    insights = {
        "summary": "إجمالي المبيعات 58400.",
        "findings": ["الرياض تتصدر بـ 35100", "نمو 4500000 في الربع الأخير"],
        "recommendations": ["راقب الأداء"],
    }
    cleaned, dropped = strip_ungrounded(insights, FACTS)
    assert len(cleaned["findings"]) == 1
    assert "35100" in cleaned["findings"][0]
    assert len(dropped) == 1
    assert cleaned["summary"]           # الملخص مدعوم فيبقى


def test_strip_clears_summary_when_it_invents():
    insights = {"summary": "بلغت الإيرادات 7777777 ريال.", "findings": [],
                "recommendations": []}
    cleaned, dropped = strip_ungrounded(insights, FACTS)
    assert cleaned["summary"] == "" and dropped


class _Fake:
    """نموذج وهمي: يرد بالإنجليزية أولاً ثم بالعربية عند إعادة الطلب."""
    is_local = True

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    async def chat(self, model, system, user, **kw):
        self.calls += 1
        text = self.replies.pop(0)

        class R:
            pass
        r = R(); r.text = text
        return r


AR_REPLY = """## SUMMARY
تغطي البيانات 120 طلباً بإجمالي 58400.
## FINDINGS
- الرياض تتصدر بـ 35100
"""
EN_REPLY = """## SUMMARY
This dataset covers 120 orders totalling 58400.
## FINDINGS
- Riyadh leads with 35100
"""


async def test_retries_once_when_language_is_wrong():
    fake = _Fake([EN_REPLY, AR_REPLY])
    out = await generate_insights(fake, "m", FACTS, "ar")
    assert fake.calls == 2                      # أعاد المحاولة
    assert out["language_ok"] is True
    assert "الرياض" in out["findings"][0]


async def test_no_retry_when_language_is_right():
    fake = _Fake([AR_REPLY])
    out = await generate_insights(fake, "m", FACTS, "ar")
    assert fake.calls == 1 and out["language_ok"] is True


async def test_invented_numbers_are_stripped_end_to_end():
    reply = """## SUMMARY
تغطي البيانات 120 طلباً.
## FINDINGS
- الرياض تتصدر بـ 35100
- ارتفعت المبيعات إلى 9876543 هذا الربع
"""
    fake = _Fake([reply])
    out = await generate_insights(fake, "m", FACTS, "ar")
    assert out["dropped_claims"] == 1
    assert all("9876543" not in f for f in out["findings"])


def test_bracketed_table_names_and_markdown_are_cleaned():
    """النموذج يردّد صياغة الحقائق — القوس المربّع وعلامات Markdown أثر آلة."""
    out = parse_insights("## SUMMARY\nتم تسجيل 3200 سجلاً لـ [المصروفات].\n"
                         "## FINDINGS\n- **بلغ** الإجمالي 5 في [الميزانيات]")
    assert "[" not in out["summary"] and "المصروفات" in out["summary"]
    assert out["findings"][0] == "بلغ الإجمالي 5 في الميزانيات"
