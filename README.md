# LEVI - AI Quotes Bot w/ Clean Architecture 🌟

[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen?logo=docker)](https://www.docker.com/)

LEVI is now **fully functional** w/ modern frontend architecture, semantic quote search, AI chat, and glassmorphism dark theme (indigo/amber).

## ✨ Features (Live!)

- **Semantic Quote Search**: /api/search_quotes (embeddings-powered)

- **AI Chat**: /api/chat (session-aware conversations)

- **Quote Generation**: /api/generate  
- **Modern UI**: Dark theme (#0F172A), glass cards, hover animations, 80vh chat
- **Central API Client**: frontend/js/api.js routes all via nginx /api/
- **Responsive**: Tailwind + custom CSS, PWA-ready

## 🏗️ Fixed Architecture

```
Nginx (80) 
  → frontend/ (index.html/chat.html/quotes.html)
  ↳ /api/ → backend:8000 (FastAPI)
        ↳ Postgres/pgvector + Redis + RASA
```

## 🚀 How to Run (Local Development)

To start both the backend and frontend simultaneously with automatic port management:

```bash
python run_app.py
```

- **Frontend**: [http://localhost:8080](http://localhost:8080)
- **Backend**: [http://localhost:8000](http://localhost:8000)

## 🌐 How to Deploy (Firebase & Cloud Run)

LEVI is pre-configured for a hybrid cloud deployment: **Firebase Hosting** for the frontend and **Google Cloud Run** for the backend.

### 1. Backend Deployment (Cloud Run)

- **Containerize**: Use [Dockerfile.prod](file:///c:/Users/mehta/Desktop/LEVI/backend/Dockerfile.prod) to build your image.

  ```bash
  gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/levi-backend ./backend
  ```

- **Deploy**: Deploy to Cloud Run.

  ```bash
  gcloud run deploy levi-backend --image gcr.io/YOUR_PROJECT_ID/levi-backend --platform managed --allow-unauthenticated
  ```

- **Update URL**: Note the provided Service URL.

### 2. Frontend Deployment (Firebase)

- **Configure**: Open [firebase.json](file:///c:/Users/mehta/Desktop/LEVI/firebase.json) and replace `https://your-backend-url.a.run.app` with your Cloud Run Service URL.
- **Initialize**:

  ```bash
  firebase init hosting
  ```

- **Deploy**:

  ```bash
  firebase deploy --only hosting
  ```

### 3. Security

- Update `origins` in [main.py](file:///c:/Users/mehta/Desktop/LEVI/backend/main.py) with your actual Firebase URL to ensure CORS is correctly handled.

## 🛠️ Robustness Features

- **Unified Lifecycle**: `run_app.py` manages both services and automatically kills stale processes.
- **Fail-safe AI**: Backend automatically switches to rule-based wisdom if heavy models fail to load.
- **Network Resilience**: Service Worker uses a Network-First strategy to ensure you always get fresh AI responses while staying fast.
- **Health Monitoring**: Integrated healthchecks in Docker ensures automatic recovery of any crashed services.

## 📱 Pages

| Page | URL | Features |
|------|-----|----------|
| Landing | / | Hero + CTAs (Indigo theme) |
| Chat | /chat.html | Real-time API chat, typing indicator |
| Quotes | /quotes.html | Semantic search, glassmorphism cards |

## 🎨 UI Theme

```
BG: #0F172A    Text: #F8FAFC
User: #6366F1  Bot/Card: #1E293B  
Accent: #F59E0B  Glass: rgba(30,41,59,.8) + blur
```

## 🛠️ Tech Stack

- **Frontend**: HTML/JS/CSS (api.js central client)
- **Backend**: FastAPI 0.104, pgvector, sentence-transformers, Torch CPU
- **Services**: nginx, postgres, redis, rasa 3.6
- **Docker**: All-in-one compose (fixed pip syntax)

## 🔧 Fixed Issues

- **API Routing**: All via `/api/` (nginx proxy)
- **requirements.txt**: Torch CPU install syntax
- **CSS Lint**: Safari backdrop-filter + vanilla CSS
- **JS IDs**: chatBox= `#messages`, searchInput= `#search-input`

## 📁 Structure (Spec Match)

```
frontend/
├── index.html (hero)
├── chat.html (w/ api.js/chat.js)
├── quotes.html (w/ api.js/quotes.js)
├── js/api.js (central)
└── css/styles.css (dark glass theme)
```

## 📊 API Docs

<http://localhost/api/docs> (Swagger)

## 🤖 Recent Updates (BLACKBOXAI)

```
✅ Clean API architecture (11 steps exact)
✅ Modern theme + animations
✅ Docker build fixed (torch pip)
✅ CSS Safari/linter clean
✅ All pages live/functional
```

**Production-ready!** Contributions welcome 🚀

---
*LEVI: Leveraging Embeddings for Valuable Inspiration*

