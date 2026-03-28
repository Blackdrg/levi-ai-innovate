# LEVI-AI - Wisdom & Creative Muse 🌟 (v3.0 Bulletproof Architecture)

LEVI-AI is a high-scale AI platform for philosophical exploration and artistic synthesis. **Status: v3.0 Bulletproof Release. Architected for 50k+ concurrent users with a distributed microservices pattern, Celery async queue, and central API Gateway.**

## 🏗️ Architecture (v3.0)

```text
Frontend (Vanilla JS/Firebase) ↔ API Gateway (FastAPI) ↔ Microservices
                                           ↓
                                ┌─────────────────────┐
                                │   Celery Workers    │ ↔ Redis + AI Providers
                                └─────────────────────┘
```
- **Gateway**: Central entry point with rate limiting and auth validation.
- **Services**: Logically split into Auth, Chat, Studio, Gallery, and Analytics.
- **Queue**: Async task processing for Studio (Image/Video) using Redis.
- **Stack**: FastAPI, Celery, SQLAlchemy, Firestore, Redis, Groq/Together AI.

## ✅ Scaling & Resilience
- **Auto-scaling**: Designed for Google Cloud Run with independent service scaling.
- **Fault Tolerance**: Circuit breakers and standardized retries with exponential backoff.
- **Monitoring**: Centralized health checks and request tracking.

## 🚀 Quick Start (Dockerized)

The easiest way to run the full bulletproof stack locally:

```bash
docker-compose up --build
```
- **Frontend**: [http://localhost](http://localhost) (via Nginx)
- **API Gateway**: [http://localhost/api/v1](http://localhost/api/v1)
- **Health Check**: [http://localhost/api/v1/health](http://localhost/api/v1/health)

## 📁 Key Components

- **backend/gateway.py**: The central control layer.
- **backend/services/**: Independent microservice logic.
- **backend/celery_app.py**: Task queue configuration.
- **frontend/**: High-performance glassmorphism UI.

---
**Production Deployment**: Use `firebase-deploy.ps1` for Cloud Run (Gateway + Workers) and Firebase Hosting (Frontend).

All systems operational at scale.
