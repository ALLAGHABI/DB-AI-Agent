#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --port 8000 --reload) &
BACK=$!
trap "kill $BACK" EXIT
cd "$ROOT/frontend" && pnpm dev
