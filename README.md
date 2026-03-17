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

## 🚀 Quick Start

```bash
docker compose up --build
```

**~2min** → <http://localhost> 🎉

**Test Flow:**

1. Landing hero → "Start Chat"
2. Chat: Type message → LEVI responds (via /api/chat)
3. Quotes: Search keyword → glass cards w/ hover
4. API: `curl -X POST http://localhost/api/health`

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

