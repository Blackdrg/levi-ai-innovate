# LEVI - AI Wisdom & Creative Muse 🌟

LEVI is a full-stack AI app for philosophical quotes, contextual chat, and artistic image generation. **Status: Fully functional locally & production-ready.**

## 🏗️ Architecture

```
Frontend (Tailwind/Vanilla JS) ↔ FastAPI Backend ↔ AI Models + DB
├── Local: `python run_app.py` (localhost:8080)
├── Deploy: Render (backend) + Vercel (frontend)
└── Stack: FastAPI, SQLAlchemy (SQLite/Postgres), Redis (optional), DistilGPT2, SentenceTransformers, PIL
```

## ✅ Status (Diagnosed & Fixed)

| Component | Status | Notes |
|-----------|--------|-------|
| Frontend | 🟢 Fixed | JS syntax ("try expected") → Modularized `js/index.js` |
| Backend API | 🟢 Fixed | Missing modules (`redis_client.py`, `db.py`) created |
| DB | 🟢 Ready | SQLite local (`levi.db`), Postgres prod |
| ML Models | 🟡 Graceful Fallback | CPU models load async, mock if fail |
| Redis | 🟡 Optional | In-memory fallback works |
| Rasa NLU | 🔴 Optional | DistilGPT2 fallback active |

**Startup Chain Fixed**: All imports resolve, `uvicorn main:app` runs cleanly.

## 🚀 Quick Start

```bash
git clone <repo> && cd LEVI
python run_app.py
# → Backend: localhost:8000 | Frontend: localhost:8080
```

## 📁 Key Files

```
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

```
✅ Frontend loads (no JS errors)
✅ Backend responds /health
✅ DB tables created on startup
✅ ML models (async load + fallback)
✅ All endpoints tested
```

**Production**: Use `render.yaml` + `vercel.json`.

All systems operational.
