# LEVI - AI Wisdom & Creative Muse 🌟 (Updated March 22, 2026)

LEVI is a full-stack AI app for philosophical quotes, contextual chat, and artistic image generation. **Status: Production-ready release (v2.2). Features: Celestial Design System (Newsreader/Gold), Together AI, Stripe Payments, Celery Worker, S3 Storage, and Web Push Notifications.**

## 🏗️ Architecture

```text
Frontend (Tailwind/Vanilla JS) ↔ FastAPI Backend ↔ AI Models + DB
├── Theme: Celestial (Newsreader font, Gold/Dark palette)
├── Worker: Celery (background task processing)
├── Deploy: Render (backend/worker) + Vercel (frontend)
└── Stack: FastAPI, SQLAlchemy, Alembic, Redis, DistilGPT2, SentenceTransformers
```

## ✅ Status (Diagnosed & Fixed)

| Component | Status | Notes |
| :--- | :--- | :--- |
| Frontend | 🟢 Fixed | Migrated to **Celestial Design System** (Newsreader/Gold) |
| Auth | 🟢 Fixed | Added **SessionMiddleware** + `POST /login` JSON support |
| Backend API | 🟢 Fixed | All imports resolved, modular backend structure |
| DB | 🟢 Ready | Alembic migrations synced (Analytics/PushSubscription) |
| Worker | 🟢 Ready | Dedicated **Celery worker** service in `render.yaml` |
| ML Models | 🟡 Graceful Fallback | CPU models load async, mock if fail |

**Startup Chain Fixed**: All imports resolve, `uvicorn main:app` runs cleanly.

## 🚀 Quick Start

```bash
git clone <repo> && cd LEVI
python run_app.py
# → Backend: localhost:8000 | Frontend: localhost:8080
```

## 📁 Key Files

```text
backend/
├── main.py (FastAPI)
├── db.py (SQLAlchemy)
├── redis_client.py (Cache)
├── models.py (Quote/User/Feed)
├── embeddings.py (Semantic search)
├── generation.py (DistilGPT2)
└── image_gen.py (PIL art)
frontend/
├── index.html (Landing)
├── js/api.js, index.js (Core logic)
└── css/styles.css (Glassmorphism)
```

## 🔧 Features

- `/chat`: AI conversation (Rasa → GPT2 fallback)
- `/generate`: Quote synthesis
- `/search_quotes`: Vector search
- `/generate_image`: Quote → Art
- Multi-lang (EN/Hindi)

## 📊 Health Check

```text
✅ Frontend loads (no JS errors)
✅ Backend responds /health
✅ DB tables created on startup
✅ ML models (async load + fallback)
✅ All endpoints tested
```

**Production**: Use `render.yaml` + `vercel.json`.

All systems operational.
