#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف التشغيل الرئيسي لتطبيق DB-AI-Agent
"""
import sys
import os
import locale

# ضبط التشفير للنظام
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# ضبط locale
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass

# إضافة مسار المشروع إلى sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from app.web_ui import WebApp
    
    def main():
        """الدالة الرئيسية"""
        print("🚀 بدء تشغيل DB-AI-Agent...")
        print("📱 واجهة الويب متاحة على: http://localhost:8080")
        
        # إنشاء وتشغيل التطبيق
        app = WebApp()
        app.run(debug=False, port=8080)
        
        print("👋 تم إغلاق التطبيق")

    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ خطأ في استيراد المكتبات: {e}")
    print("يرجى تثبيت المتطلبات باستخدام: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ خطأ غير متوقع: {e}")
    sys.exit(1)
