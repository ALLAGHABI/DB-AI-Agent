#!/bin/bash
# Launcher for DB-AI-Agent
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Activate venv if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Ensure deps installed
python -c "import flask, sqlalchemy, requests, cryptography, pandas" 2>/dev/null || pip install -r requirements.txt

# Run the app
python main.py
