# DB-AI-Agent User Guide
## Intelligent Database Assistant

---

## 📋 **Overview**

DB-AI-Agent is an intelligent application that allows you to interact with databases using natural language in Arabic and English. It automatically converts your requests into SQL queries using artificial intelligence.

### ✨ **Key Features:**
- 🤖 Natural language to SQL conversion using OpenRouter AI
- 🗄️ Support for SQLite, MySQL, PostgreSQL
- 🔒 Secure encryption for settings and passwords
- 🌐 Easy-to-use Arabic web interface
- 💾 Automatic settings persistence in browser
- 🎯 Choice of 7 different AI models

---

## 🚀 **Installation & Setup**

### 1. **System Requirements:**
```bash
Python 3.8+
pip (Python package manager)
```

### 2. **Install Dependencies:**
```bash
cd /Users/apple/Desktop/DB-AI-Agent
pip install -r requirements.txt
```

### 3. **Run Application:**
```bash
python main.py
```

### 4. **Open Application:**
Open your browser and navigate to: `http://localhost:8080`

---

## 🔑 **Getting OpenRouter API Key**

### Steps:
1. Go to [OpenRouter.ai](https://openrouter.ai)
2. Create new account or sign in
3. Navigate to "API Keys" in dashboard
4. Create new API key
5. Copy the key (starts with `sk-or-`)

### 💰 **Pricing:**
- Most models cost $0.001-$0.01 per 1000 tokens
- Start with free credit $1-5

---

## 📖 **Usage Guide**

### 1. **Initial Setup:**

#### A) OpenRouter API Setup:
1. Enter API key in "OpenRouter API Key" field
2. Choose preferred AI model:
   - **Claude 3.5 Sonnet** (Best for Arabic)
   - **GPT-4o** (Fast and accurate)
   - **GPT-4o Mini** (Economical)
   - **Gemini Pro 1.5** (Good for long texts)
   - **Llama 3.1 405B** (Open source)
   - **Llama 3.1 70B** (Balanced)
   - **Mistral Large** (Fast)

3. Click "Test Connection" to verify

#### B) Database Setup:

**For SQLite:**
1. Select "SQLite" from dropdown
2. Click "Browse" to select .db file
3. Or use "Sample Database"
4. Click "Connect"

**For MySQL/PostgreSQL:**
1. Select database type
2. Enter connection details:
   - Host (e.g., localhost)
   - Port (3306 for MySQL, 5432 for PostgreSQL)
   - Database name
   - Username
   - Password
3. Click "Connect"

### 2. **Using the Application:**

#### Arabic Query Examples:
```
اعرض جميع العملاء
كم عدد العملاء في الرياض؟
أضف عميل جديد اسمه أحمد من جدة
احذف العميل رقم 5
عدّل اسم العميل رقم 3 إلى محمد
اعرض أكثر 5 منتجات مبيعاً
ما هو متوسط أسعار المنتجات؟
```

#### English Query Examples:
```
Show all customers
How many orders were placed today?
Add a new product with name "Laptop" and price 1500
Delete customer with ID 10
Update product price to 200 where name is "Mouse"
Show top 5 selling products
What is the average order value?
```

### 3. **Understanding Results:**

#### On Successful Query:
- ✅ **SQL Query:** Shows generated code
- 📊 **Results:** Displayed in organized table
- ℹ️ **Additional Info:** Number of affected rows

#### On Error:
- ❌ **Error Message:** Explains the problem
- 🔧 **Solution Suggestions:** Tips to fix the issue

---

## 🛠️ **Troubleshooting**

### Common Issues:

#### 1. **"Invalid API Key"**
**Solution:**
- Ensure complete key is copied
- Verify key validity in OpenRouter
- Check account balance

#### 2. **"Database Connection Failed"**
**Solution:**
- Check SQLite file path
- Verify MySQL/PostgreSQL connection details
- Ensure database server is running

#### 3. **"No Response from AI"**
**Solution:**
- Try different AI model
- Ensure clear request
- Check internet connection

#### 4. **"Query Execution Error"**
**Solution:**
- Verify required tables and columns exist
- Ensure correct table names in request
- Click "Refresh Schema" to re-scan database

---

## 🔒 **Security & Privacy**

### Data Protection:
- 🔐 **Local Encryption:** Passwords encrypted locally
- 🚫 **No Password Storage:** Not saved in localStorage for security
- 🔑 **Secure API Keys:** Saved with local encryption
- 🌐 **Secure Connection:** All requests via HTTPS

### Security Tips:
- Don't share API key with others
- Use strong passwords for databases
- Review queries before executing on important data
- Keep database backups

---

## 📁 **Project Structure**

```
DB-AI-Agent/
├── main.py                 # Main execution file
├── requirements.txt        # Python requirements
├── app/                   # Main application folder
│   ├── __init__.py
│   ├── web_ui.py          # Web interface
│   ├── ai_agent.py        # AI agent
│   ├── database_handler.py # Database manager
│   └── settings_manager.py # Settings manager
├── templates/             # HTML templates
│   └── index.html
├── data/                  # Data files
│   ├── sample_store.db    # Sample database
│   └── schema_cache.json  # Schema cache
└── utils/                 # Helper utilities
    └── voice_recognition.py
```

---

## 🎯 **Best Practices**

### For Optimal Results:

#### 1. **Query Formulation:**
- Be clear and specific
- Use correct table and column names
- State conditions clearly

#### 2. **Model Selection:**
- **Claude 3.5 Sonnet:** Best for complex Arabic texts
- **GPT-4o Mini:** For simple, fast queries
- **GPT-4o:** For complex, accurate queries

#### 3. **Cost Management:**
- Start with economical models
- Monitor credit usage in OpenRouter
- Use clear requests to minimize attempts

---

## 🆘 **Support & Help**

### If you encounter issues:

1. **Check Log File:** Review error messages in terminal
2. **Restart Application:** `Ctrl+C` then `python main.py`
3. **Clear Settings:** Click "Clear Saved Settings"
4. **Update Requirements:** `pip install -r requirements.txt --upgrade`

### Technical Information:
- **Port:** 8080
- **Protocol:** HTTP
- **Supported Browsers:** Chrome, Firefox, Safari, Edge
- **Operating Systems:** Windows, macOS, Linux

---

## 📝 **Changelog**

### Current Version:
- ✅ Fixed UTF-8 encoding issues with Arabic text
- ✅ Support for 7 different AI models
- ✅ Automatic settings persistence in browser
- ✅ Enhanced user interface
- ✅ Comprehensive error handling
- ✅ Multi-database support

---

## 🎉 **Get Started Now!**

1. Run application: `python main.py`
2. Open browser: `http://localhost:8080`
3. Enter OpenRouter API key
4. Connect to database
5. Start asking questions!

**Quick Example:**
```
"Show all customers from Riyadh"
```

---

*This guide was created to help you get the most out of DB-AI-Agent. Enjoy interacting with databases using AI! 🚀*
