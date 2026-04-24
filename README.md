# DB-AI-Agent 🤖
## وكيل قاعدة البيانات الذكي

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-AI-orange.svg)](https://openrouter.ai)

---

## 📋 **نظرة عامة**

DB-AI-Agent هو تطبيق ذكي متقدم يتيح لك التفاعل مع قواعد البيانات باستخدام **اللغة الطبيعية العربية والإنجليزية**. يحول طلباتك تلقائياً إلى استعلامات SQL دقيقة باستخدام أحدث نماذج الذكاء الاصطناعي.

### ✨ **المميزات الرئيسية**
- 🤖 **ذكاء اصطناعي متقدم:** دعم 7 نماذج AI مختلفة (Claude, GPT-4, Gemini, Llama)
- 🌍 **دعم اللغة العربية:** واجهة عربية كاملة مع معالجة متقدمة للنصوص العربية
- 🗄️ **قواعد بيانات متعددة:** SQLite, MySQL, PostgreSQL
- 🔒 **أمان متقدم:** تشفير محلي للإعدادات وكلمات المرور
- 💾 **حفظ تلقائي:** الإعدادات محفوظة في المتصفح
- 🎯 **سهولة الاستخدام:** واجهة ويب بديهية وسريعة الاستجابة

---

## 🚀 **التثبيت السريع**

### 1. **استنساخ المشروع:**
```bash
git clone <repository-url>
cd DB-AI-Agent
```

### 2. **تثبيت المتطلبات:**
```bash
pip install -r requirements.txt
```

### 3. **تشغيل التطبيق:**
```bash
python main.py
```

### 📁 **هيكل المشروع**

```
DB-AI-Agent/
├── main.py                 # نقطة البداية الرئيسية
├── app/
│   ├── __init__.py
│   ├── ui.py              # واجهة المستخدم
│   ├── database_handler.py # إدارة قواعد البيانات
│   ├── ai_agent.py        # وكيل الذكاء الاصطناعي
│   └── settings_manager.py # إدارة الإعدادات
├── utils/
│   ├── __init__.py
│   └── voice_recognition.py # التعرف على الصوت
├── data/
│   ├── settings.json      # ملف الإعدادات
│   └── query_history.db   # تاريخ الاستعلامات
└── requirements.txt       # المكتبات المطلوبة
```

## الاستخدام

1. قم بتكوين اتصال قاعدة البيانات من صفحة الإعدادات
2. أدخل مفتاح OpenRouter API
3. اختر نموذج الذكاء الاصطناعي المفضل
4. ابدأ في كتابة أو تسجيل أوامرك باللغة الطبيعية

## المتطلبات

- Python 3.8+
- مفتاح OpenRouter API
- اتصال بالإنترنت للذكاء الاصطناعي
