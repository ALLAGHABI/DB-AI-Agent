"""التقاط لقطات شاشة حقيقية للتوثيق — يتطلب الخوادم شغالة على 3000/8000.

الاستخدام: .venv/bin/python scripts/capture_screenshots.py
"""
import os
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)

APP = "http://localhost:3000"


def shot(page, name):
    path = os.path.join(OUT, f"{name}.png")
    page.screenshot(path=path, full_page=False)
    print("✓", path)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  device_scale_factor=2)
        page = ctx.new_page()

        # عربي داكن (الافتراضي)
        page.goto(APP, wait_until="networkidle")
        # اتصال بالقاعدة التجريبية
        page.get_by_role("button", name="اتصال").click()
        page.wait_for_timeout(1500)

        # 1) الاستعلام الذكي مع نتائج (استعلام مباشر لتفادي انتظار النموذج)
        page.request.post("http://127.0.0.1:8000/api/db/execute", data={
            "sql": "SELECT name, price FROM products ORDER BY price DESC"})
        page.get_by_role("tab", name="محرر SQL").click()
        page.locator(".cm-content").click()
        page.keyboard.type("SELECT c.name, c.city, COUNT(o.id) AS orders\n"
                           "FROM customers c JOIN orders o ON o.customer_id = c.id\n"
                           "GROUP BY c.id ORDER BY orders DESC")
        page.get_by_role("button", name="تنفيذ").click()
        page.wait_for_timeout(1200)
        shot(page, "sql-editor-ar-dark")

        # 2) الجداول
        page.get_by_role("tab", name="الجداول").click()
        page.wait_for_timeout(1200)
        shot(page, "tables-ar-dark")

        # 3) مخطط ER
        page.get_by_role("tab", name="المخطط").click()
        page.wait_for_timeout(1500)
        shot(page, "er-diagram-ar-dark")

        # 4) التقارير
        page.get_by_role("tab", name="التقارير").click()
        page.wait_for_timeout(1200)
        shot(page, "reports-studio-ar-dark")

        # 5) الرئيسية بالإنجليزية فاتح
        page.evaluate("document.cookie = 'locale=en;path=/'")
        page.evaluate("localStorage.setItem('theme', 'light')")
        page.goto(APP, wait_until="networkidle")
        page.wait_for_timeout(1200)
        shot(page, "home-en-light")

        # 6) تقرير HTML (أول تقرير في الأرشيف إن وجد)
        r = page.request.get("http://127.0.0.1:8000/api/reports")
        reports = r.json()
        if reports:
            page.goto(f"http://127.0.0.1:8000/api/reports/{reports[0]['id']}/html",
                      wait_until="networkidle")
            page.wait_for_timeout(1500)
            shot(page, "report-ar")

        browser.close()


if __name__ == "__main__":
    main()
