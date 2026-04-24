#!/bin/bash
# Git setup script for DB-AI-Agent
set -e
cd "$(dirname "$0")"

echo "🔧 تهيئة Git للمشروع..."

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git غير مثبّت. يرجى تثبيته أولاً:"
    echo "   xcode-select --install"
    read -p "Press any key to close..." -n 1
    exit 1
fi

# Init if not already a git repo
if [ ! -d ".git" ]; then
    git init -b main
    echo "✅ تم إنشاء git repo"
else
    echo "ℹ️  git repo موجود مسبقاً"
fi

# Configure user if missing
if [ -z "$(git config user.name)" ]; then
    echo "⚠️  يجب ضبط git user.name أولاً:"
    read -p "   أدخل اسمك: " GIT_NAME
    git config user.name "$GIT_NAME"
fi
if [ -z "$(git config user.email)" ]; then
    read -p "   أدخل بريدك الإلكتروني: " GIT_EMAIL
    git config user.email "$GIT_EMAIL"
fi

# Stage everything (respecting .gitignore)
git add -A

# Show status
echo ""
echo "📋 الملفات الجاهزة للالتزام:"
git status --short

# Commit
if git diff --cached --quiet; then
    echo "ℹ️  لا توجد تغييرات جديدة للالتزام"
else
    git commit -m "Initial commit: SmartDB AI - وكيل قاعدة البيانات الذكي"
    echo "✅ تم عمل الالتزام الأولي"
fi

echo ""
echo "🎉 تم! المشروع جاهز للرفع على GitHub."
echo ""
echo "   الخطوة التالية: سيتم فتح GitHub لإنشاء ريبو جديد."
echo ""
read -p "اضغط Enter للإنهاء..."
