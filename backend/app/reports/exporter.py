"""تصدير التقرير: Excel منسق وPDF (إن توفر محرك)."""
import io

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

_HEADER_FILL = PatternFill("solid", fgColor="059669")
_HEADER_FONT = Font(color="FFFFFF", bold=True)


def _style_header(ws):
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    for i, col in enumerate(ws.columns, 1):
        width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 4, 12), 50)


def _sheet_name(name: str, used: set) -> str:
    """أسماء أوراق Excel محدودة بـ31 حرفاً ويجب أن تكون فريدة."""
    base = str(name)[:28] or "sheet"
    candidate, i = base, 1
    while candidate in used:
        candidate = f"{base[:26]}_{i}"
        i += 1
    used.add(candidate)
    return candidate


def to_xlsx(profile: dict, insights: dict, language: str) -> bytes:
    ar = language == "ar"
    if profile.get("kind") == "multi":
        return _to_xlsx_multi(profile, insights, ar)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # ورقة الملخص
        summary_rows = [
            ("الصفوف" if ar else "Rows", profile["overview"]["rows"]),
            ("الأعمدة" if ar else "Columns", profile["overview"]["cols"]),
            ("قيم مفقودة %" if ar else "Missing %", profile["overview"]["missing_pct"]),
            ("صفوف مكررة" if ar else "Duplicates", profile["overview"]["duplicate_rows"]),
            ("", ""),
            ("الملخص" if ar else "Summary", insights.get("summary", "")),
        ]
        for i, f in enumerate(insights.get("findings", []), 1):
            summary_rows.append((f"{'نتيجة' if ar else 'Finding'} {i}", f))
        for i, r in enumerate(insights.get("recommendations", []), 1):
            summary_rows.append((f"{'توصية' if ar else 'Recommendation'} {i}", r))
        pd.DataFrame(summary_rows, columns=["البند" if ar else "Item",
                                            "القيمة" if ar else "Value"]) \
            .to_excel(writer, sheet_name="ملخص" if ar else "Summary", index=False)

        # ورقة الأعمدة
        pd.DataFrame(profile["columns"]).drop(columns=["top_values"], errors="ignore") \
            .to_excel(writer, sheet_name="الأعمدة" if ar else "Columns", index=False)

        # ورقة العينة
        pd.DataFrame(profile["sample"], columns=profile["sample_columns"]) \
            .to_excel(writer, sheet_name="عينة" if ar else "Sample", index=False)

        for ws in writer.book.worksheets:
            _style_header(ws)
            if ar:
                ws.sheet_view.rightToLeft = True
    return buf.getvalue()


def _to_xlsx_multi(profile: dict, insights: dict, ar: bool) -> bytes:
    buf = io.BytesIO()
    used: set = set()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        rows = [
            ("عدد الجداول" if ar else "Tables", profile["overview"]["tables"]),
            ("إجمالي الصفوف" if ar else "Total rows", profile["overview"]["rows"]),
            ("إجمالي الأعمدة" if ar else "Total columns", profile["overview"]["cols"]),
            ("العلاقات" if ar else "Relationships", profile["overview"]["relationships"]),
            ("", ""),
            ("الملخص" if ar else "Summary", insights.get("summary", "")),
        ]
        for i, f in enumerate(insights.get("findings", []), 1):
            rows.append((f"{'نتيجة' if ar else 'Finding'} {i}", f))
        for i, r in enumerate(insights.get("recommendations", []), 1):
            rows.append((f"{'توصية' if ar else 'Recommendation'} {i}", r))
        pd.DataFrame(rows, columns=["البند" if ar else "Item", "القيمة" if ar else "Value"]) \
            .to_excel(writer, sheet_name=_sheet_name("ملخص" if ar else "Summary", used),
                      index=False)

        if profile["relationships"]:
            pd.DataFrame(profile["relationships"]).to_excel(
                writer, sheet_name=_sheet_name("العلاقات" if ar else "Relationships", used),
                index=False)

        for ds in profile["datasets"]:
            df = pd.DataFrame(ds["profile"]["columns"]).drop(
                columns=["top_values"], errors="ignore")
            df.to_excel(writer, sheet_name=_sheet_name(ds["name"], used), index=False)

        for ws in writer.book.worksheets:
            _style_header(ws)
            if ar:
                ws.sheet_view.rightToLeft = True
    return buf.getvalue()


def pdf_engine() -> str | None:
    """يرجع اسم محرك PDF المتاح أو None."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return "playwright"
    except ImportError:
        pass
    try:
        import weasyprint  # noqa: F401
        return "weasyprint"
    except ImportError:
        return None


def to_pdf(html: str) -> bytes | None:
    engine = pdf_engine()
    if engine == "playwright":
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf = page.pdf(format="A4", print_background=True,
                           margin={"top": "15mm", "bottom": "15mm",
                                   "left": "12mm", "right": "12mm"})
            browser.close()
            return pdf
    if engine == "weasyprint":
        import weasyprint
        return weasyprint.HTML(string=html).write_pdf()
    return None
