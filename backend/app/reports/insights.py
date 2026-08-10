"""توليد الرؤى: حقائق محسوبة → موجه صارم → نموذج لغوي → أقسام مُحللة.

مبدآن يحكمان هذا الملف:
1. النموذج لا يرى إلا حقائق محسوبة فعلاً — فلا مجال لاختلاق الأرقام.
2. اللغة تُفرض، وتُتحقق بعد الرد، ويُعاد الطلب مرة واحدة إن خالفها.
"""
import re

_LANG = {
    "ar": {"name": "Arabic", "native": "العربية",
           "instruction": "اكتب التقرير بالكامل باللغة العربية الفصحى.",
           "headers": ("الملخص", "النتائج", "التوصيات")},
    "en": {"name": "English", "native": "English",
           "instruction": "Write the entire report in English.",
           "headers": ("Summary", "Findings", "Recommendations")},
}

SYSTEM_TEMPLATE = """You are a business analyst writing an executive report for managers.

{instruction}
The reader is a manager, not an engineer: write about the business, never about
database structure, column types, nulls, keys or relationships.

You are given a numbered list of VERIFIED FACTS computed from the real data.
Rules you must obey:
- Use ONLY numbers that appear in the facts. Never invent or estimate a number.
- Never mention a metric that is not in the facts (no growth rates, percentages,
  segments or comparisons unless they are listed).
- If the facts are limited, write less — do not fill space with speculation.
- {instruction}

Respond in EXACTLY this structure, keeping the English markers:

## SUMMARY
One short paragraph (3-5 sentences) in {language_name} stating what the data covers
and its most important business signal.

## FINDINGS
- 3 to 6 bullets in {language_name}, each citing a number from the facts.

## RECOMMENDATIONS
- 2 to 4 actionable bullets in {language_name} for a manager."""


def build_insights_prompt(facts: list[str], language: str,
                          subject: str = "") -> tuple[str, str]:
    lang = _LANG.get(language, _LANG["en"])
    system = SYSTEM_TEMPLATE.format(instruction=lang["instruction"],
                                    language_name=lang["name"])
    numbered = "\n".join(f"{i}. {f}" for i, f in enumerate(facts, 1))
    user = (f"Subject: {subject}\n\n" if subject else "") + \
        f"VERIFIED FACTS (the only numbers you may use):\n{numbered}\n\n" \
        f"{lang['instruction']}"
    return system, user


def _section(text: str, name: str) -> str:
    m = re.search(rf"##\s*{name}\s*\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _bullets(block: str) -> list[str]:
    out = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith(("-", "*", "•")):
            out.append(line.lstrip("-*• ").strip().strip("*"))
    return [b for b in out if b]


def parse_insights(text: str) -> dict:
    summary = _section(text, "SUMMARY")
    findings = _bullets(_section(text, "FINDINGS"))
    recommendations = _bullets(_section(text, "RECOMMENDATIONS"))
    if not summary and not findings:
        summary = text.strip()
    return {"summary": summary, "findings": findings,
            "recommendations": recommendations}


_ARABIC = re.compile(r"[؀-ۿ]")
_LATIN_WORD = re.compile(r"[A-Za-z]{3,}")


def detect_language(text: str) -> str:
    """يكتفي بالتمييز بين العربية وغيرها — وهو ما يهمنا هنا."""
    arabic = len(_ARABIC.findall(text))
    latin = len("".join(_LATIN_WORD.findall(text)))
    return "ar" if arabic > latin else "en"


def language_matches(insights: dict, language: str) -> bool:
    body = " ".join([insights["summary"], *insights["findings"],
                     *insights["recommendations"]]).strip()
    if len(body) < 30:
        return True                     # نص قصير جداً للحكم عليه
    return detect_language(body) == ("ar" if language == "ar" else "en")


_NUMBER = re.compile(r"\d[\d,]*\.?\d*")


def _numbers(text: str) -> set[str]:
    out = set()
    for raw in _NUMBER.findall(text):
        cleaned = raw.replace(",", "").rstrip(".")
        if cleaned:
            out.add(cleaned)
    return out


def ungrounded_numbers(insights: dict, facts: list[str]) -> list[str]:
    """أرقام وردت في الرد ولا أصل لها في الحقائق — مؤشر اختلاق."""
    allowed = _numbers(" ".join(facts))
    allowed_values = [float(a) for a in allowed if _is_float(a)]

    def known(n: str) -> bool:
        """رقم مقبول إن ورد حرفياً، أو كان تقريباً لرقم وارد، أو صغيراً جداً."""
        if n in allowed:
            return True
        if not _is_float(n):
            return True
        value = float(n)
        if value <= 12:                          # ترتيب/عدّ/رقم بند صغير
            return True
        # تسامح مع التقريب: 60 مقابل 60.1، و1487 مقابل 1486.67
        return any(abs(value - a) <= max(1.0, abs(a) * 0.01) for a in allowed_values)

    said = _numbers(" ".join([insights["summary"], *insights["findings"],
                              *insights["recommendations"]]))
    return sorted(n for n in said if not known(n))


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def strip_ungrounded(insights: dict, facts: list[str]) -> tuple[dict, list[str]]:
    """يحذف كل بند يحوي رقماً غير مدعوم بالحقائق، ويُبلغ عمّا حُذف."""
    bad = set(ungrounded_numbers(insights, facts))
    if not bad:
        return insights, []

    def clean(items: list[str]) -> tuple[list[str], list[str]]:
        kept, dropped = [], []
        for item in items:
            (dropped if _numbers(item) & bad else kept).append(item)
        return kept, dropped

    findings, d1 = clean(insights["findings"])
    recommendations, d2 = clean(insights["recommendations"])
    summary = insights["summary"]
    if _numbers(summary) & bad:
        summary = ""                              # الملخص كله مشكوك فيه
        d1.append("summary")
    return ({"summary": summary, "findings": findings,
             "recommendations": recommendations}, d1 + d2)


async def generate_insights(provider, model: str, facts: list[str], language: str,
                            subject: str = "") -> dict:
    """يولّد الرؤى ويفرض اللغة ويزيل أي رقم غير مدعوم بالحقائق."""
    system, user = build_insights_prompt(facts, language, subject)
    result = await provider.chat(model, system, user, temperature=0.2, max_tokens=1200)
    insights = parse_insights(result.text)

    if not language_matches(insights, language):
        lang = _LANG.get(language, _LANG["en"])
        retry_system = system + f"\n\nCRITICAL: your previous answer was in the wrong " \
                                f"language. {lang['instruction']} Every word must be " \
                                f"in {lang['name']} ({lang['native']})."
        result = await provider.chat(model, retry_system, user,
                                     temperature=0.1, max_tokens=1200)
        retried = parse_insights(result.text)
        if language_matches(retried, language):
            insights = retried

    insights, dropped = strip_ungrounded(insights, facts)
    insights["language_ok"] = language_matches(insights, language)
    insights["dropped_claims"] = len(dropped)
    return insights
