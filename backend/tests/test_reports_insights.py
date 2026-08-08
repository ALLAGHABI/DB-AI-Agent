from app.reports.insights import build_insights_prompt, generate_insights, parse_insights


def test_prompt_includes_profile_and_language():
    profile = {"overview": {"rows": 99, "cols": 3, "missing_pct": 1.0, "duplicate_rows": 0},
               "columns": [], "correlations": [], "charts": []}
    system, user = build_insights_prompt(profile, "ar")
    assert "Arabic" in system or "العربية" in system
    assert "99" in user


def test_parse_full_sections():
    text = """## SUMMARY
البيانات تغطي 200 طلب بمتوسط 100 ريال.

## FINDINGS
- مدينة الرياض هي الأكثر طلبات
- 10% من الطلبات ملغاة

## RECOMMENDATIONS
- راقب الطلبات الملغاة
"""
    out = parse_insights(text)
    assert "200" in out["summary"]
    assert len(out["findings"]) == 2
    assert len(out["recommendations"]) == 1


def test_parse_lenient_when_markers_missing():
    out = parse_insights("مجرد نص حر بلا أقسام")
    assert out["summary"]
    assert out["findings"] == []


async def test_generate_uses_provider():
    class Fake:
        is_local = True
        async def chat(self, model, system, user, **kw):
            class R: text = "## SUMMARY\nملخص\n## FINDINGS\n- نتيجة"
            return R()
    profile = {"overview": {"rows": 1, "cols": 1, "missing_pct": 0, "duplicate_rows": 0},
               "columns": [], "correlations": [], "charts": []}
    out = await generate_insights(Fake(), "m", profile, "ar")
    assert out["summary"] == "ملخص"
    assert out["findings"] == ["نتيجة"]
