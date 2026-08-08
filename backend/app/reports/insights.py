"""توليد الرؤى: الملف الإحصائي → موجه → نموذج لغوي → أقسام مُحللة."""
import json
import re

_LANG = {"ar": "Arabic (العربية)", "en": "English"}

SYSTEM_TEMPLATE = """You are a senior data analyst. You will receive a statistical profile
of a dataset (JSON). Write an executive report in {language}.

Respond in EXACTLY this structure (keep the English section markers):

## SUMMARY
One short paragraph (3-5 sentences) summarizing the dataset and its most important signal.

## FINDINGS
- 3 to 6 bullet points with concrete, number-backed observations.

## RECOMMENDATIONS
- 2 to 4 actionable bullet points.

Rules: use ONLY numbers present in the profile; do not invent data;
no extra sections; write the content itself in {language}."""


def build_insights_prompt(profile: dict, language: str) -> tuple[str, str]:
    system = SYSTEM_TEMPLATE.format(language=_LANG.get(language, "English"))
    slim = {
        "overview": profile["overview"],
        "columns": profile["columns"],
        "correlations": profile["correlations"],
        "chart_titles": [c["title"] for c in profile.get("charts", [])],
    }
    user = "Dataset profile:\n" + json.dumps(slim, ensure_ascii=False, default=str)
    return system, user


def _section(text: str, name: str) -> str:
    m = re.search(rf"##\s*{name}\s*\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _bullets(block: str) -> list[str]:
    out = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith(("-", "*", "•")):
            out.append(line.lstrip("-*• ").strip())
    return [b for b in out if b]


def parse_insights(text: str) -> dict:
    summary = _section(text, "SUMMARY")
    findings = _bullets(_section(text, "FINDINGS"))
    recommendations = _bullets(_section(text, "RECOMMENDATIONS"))
    if not summary and not findings:
        # نص حر بلا أقسام — خذه كملخص
        summary = text.strip()
    return {"summary": summary, "findings": findings, "recommendations": recommendations}


async def generate_insights(provider, model: str, profile: dict, language: str) -> dict:
    system, user = build_insights_prompt(profile, language)
    result = await provider.chat(model, system, user, temperature=0.2, max_tokens=1200)
    return parse_insights(result.text)
