#!/bin/bash
# Non-interactive git setup + commit for DB-AI-Agent
cd "$(dirname "$0")"

echo "🔧 Git setup (non-interactive)..."

# Remove any stale lock
rm -f .git/index.lock 2>/dev/null

# Ensure git repo
if [ ! -d ".git" ]; then
    git init -b main
fi

# Configure user (local repo scope — won't affect your global settings)
if [ -z "$(git config --get user.name)" ]; then
    git config user.name "ALLAGHABI"
fi
if [ -z "$(git config --get user.email)" ]; then
    git config user.email "alx.h0681@gmail.com"
fi

# Ensure on main branch
git symbolic-ref HEAD refs/heads/main 2>/dev/null || git checkout -b main 2>/dev/null

# Stage everything (respecting .gitignore)
git add -A

echo ""
echo "📋 الملفات المضافة للالتزام:"
git status --short | head -40

# Commit (skip if nothing staged)
if git diff --cached --quiet; then
    echo "ℹ️  لا توجد تغييرات جديدة."
else
    git commit -m "Initial commit: SmartDB AI - وكيل قاعدة البيانات الذكي

- Flask web app with Arabic UI
- Natural language to SQL using OpenRouter API
- Supports SQLite, MySQL, PostgreSQL
- Multiple AI models (Claude, GPT-4, Gemini, Llama)
- Encrypted local settings storage"
    echo "✅ تم الالتزام بنجاح"
fi

echo ""
echo "📊 السجل:"
git log --oneline | head -5

echo ""
echo "🎉 تم تجهيز المستودع محلياً. الآن يمكنك رفعه على GitHub."
echo ""
read -p "اضغط Enter للإغلاق..."
