# SmartDB — AI Database Manager

**بياناتك لا تغادر جهازك · Your data never leaves your machine**

منصة ثنائية اللغة (عربي/إنجليزي) لإدارة قواعد البيانات بالذكاء الاصطناعي — **بالنماذج المحلية أولاً**.
اسأل قاعدة بياناتك بلغتك الطبيعية، وSmartDB يولّد SQL وينفذه بأمان.

A bilingual (Arabic/English) local-first AI database manager. Ask your database in natural
language — SmartDB generates the SQL and runs it safely.

> 🚧 **Phase 1 of 4** — see [`docs/superpowers/specs/`](docs/superpowers/specs/) for the roadmap
> (DB management suite, reports studio, Docker & publishing coming next).

## ✨ Features

- 🖥️ **Local models first** — auto-detects [Ollama](https://ollama.com) and lists your installed
  models; any OpenAI-compatible server (LM Studio, vLLM) works too. Cloud (OpenRouter) is opt-in.
- 🛡️ **Safe by design** — SQL is parsed with `sqlglot`; anything that modifies data shows a
  **confirmation dialog before execution**. Unbounded SELECTs get an automatic LIMIT.
- 🌍 **Bilingual UI** — full Arabic (RTL) and English (LTR) with one-click switching, dark & light themes.
- 🔐 **No secret leaks** — API keys are encrypted at rest and never returned to the browser;
  the server binds to `127.0.0.1` only.
- 🗄️ SQLite, MySQL, and PostgreSQL (drivers included).

## 🚀 Quickstart

Requirements: Python 3.10+, Node 20+ with `pnpm`, and [Ollama](https://ollama.com) running
(`ollama pull gemma3:4b` is a good start).

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Frontend
cd ../frontend
pnpm install

# Run both (from repo root)
./scripts/dev.sh
```

Open <http://localhost:3000>, connect to `data/sample_store.db`, pick a model, and ask:
*"أظهر أفضل 5 منتجات مبيعاً"*.

## 🧪 Tests

```bash
cd backend && .venv/bin/pytest
```

## 🏗️ Architecture

```
backend/   FastAPI · app/llm (Ollama, OpenAI-compat, OpenRouter) · app/db (sqlglot guard)
           · app/agent (NL→SQL) · app/api (REST)
frontend/  Next.js · TypeScript · Tailwind · shadcn/ui · next-intl (ar/en) · next-themes
```
