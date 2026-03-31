# 🚀 LEVI v2.0 Production Deployment Checklist

Work through each phase in order. Check off as you go.

---

## Phase A: API Keys (15 min)

### Groq (LLM Inference)
- [ ] Go to [console.groq.com/keys](https://console.groq.com/keys)
- [ ] Create key → save as `GROQ_API_KEY`

### Together AI (Image Generation)
- [ ] Go to [api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys)
- [ ] Create key → save as `TOGETHER_API_KEY`

---

## Phase B: Firebase Setup (10 min)

- [ ] Go to [console.firebase.google.com](https://console.firebase.google.com)
- [ ] Create project or open `levi-ai-c23c6`
- [ ] **Firestore**: Enable in Native mode
- [ ] **Authentication**: Enable Email/Password + Google providers
- [ ] **Service Account**: Project Settings → Service Accounts → Generate new private key
  - Save JSON as `FIREBASE_SERVICE_ACCOUNT_JSON`
- [ ] Save `FIREBASE_PROJECT_ID`

---

## Phase C: Redis Setup (5 min)

- [ ] Create account at [upstash.com](https://upstash.com)
- [ ] Create Redis database → copy `REDIS_URL` (format: `redis://default:...@...upstash.io:...`)
- [ ] **Required for**: Celery workers, rate limiting, session cache, memory debouncer

---

## Phase D: Razorpay Payments (15 min)

- [ ] Log in to [dashboard.razorpay.com](https://dashboard.razorpay.com)
- [ ] Settings → API Keys → Generate Key
  - Save `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`
- [ ] Settings → Webhooks → Add New Webhook
  - URL: `https://your-backend-url.run.app/user/payments/razorpay_webhook`
  - Secret → save as `RAZORPAY_WEBHOOK_SECRET`
  - Active events: `payment.captured`

---

## Phase E: Google Cloud Run (20 min)

- [ ] Enable APIs: Cloud Run, Artifact Registry, Cloud Build
- [ ] Create service account with roles:
  - Cloud Run Admin
  - Storage Admin  
  - Artifact Registry Writer
- [ ] Download key JSON → save as `GCP_SA_KEY` GitHub secret
- [ ] Set Cloud Run service config:
  ```
  Memory: 4Gi (minimum 2Gi)
  CPU: 2
  Min instances: 1
  Max instances: 10
  Port: 8080
  ```

---

## Phase F: GitHub Secrets (5 min)

Go to **GitHub → repo → Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `GCP_SA_KEY` | GCP service account JSON |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firebase service account JSON |
| `FIREBASE_PROJECT_ID` | `levi-ai-c23c6` |
| `REDIS_URL` | Upstash Redis URL |
| `GROQ_API_KEY` | Groq API key |
| `TOGETHER_API_KEY` | Together AI key |
| `SECRET_KEY` | Random 64-char string |
| `ADMIN_KEY` | Random admin key |
| `RAZORPAY_KEY_ID` | Razorpay key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay secret |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay webhook secret |
| `SENTRY_DSN` | *(optional)* Sentry DSN |

---

## Phase G: Deploy

```bash
# Trigger full CI/CD pipeline
git push origin master:main
```

- [ ] Backend CI/CD passes (`.github/workflows/deploy-backend.yml`)
- [ ] Frontend CI/CD passes (`.github/workflows/deploy-frontend.yml`)

---

## Phase H: Smoke Tests

Run after deployment completes:

```bash
BASE=https://levi-api.a.run.app

# 1. Health check
curl $BASE/health
# Expected: {"status":"ok","database":"ok","redis":"ok"}

# 2. Local route (zero API cost)
curl -X POST $BASE/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello","session_id":"smoke_01"}'
# Expected: route="local", < 100ms

# 3. Frontend loads
curl -I https://levi-ai-c23c6.web.app
# Expected: 200 OK
```

- [ ] `/health` returns `{"status":"ok"}`
- [ ] Chat endpoint responds with `route: "local"` for greeting
- [ ] Frontend loads at Firebase Hosting URL
- [ ] Celery workers running (`celery -A backend.celery_app status`)

---

## ✅ Production Status Checklist

| Component | Status |
|-----------|--------|
| LeviOrchestrator v2.0 | ✅ 42/42 tests passing |
| Local engine (zero-API) | ✅ Greetings, FAQ, simple queries |
| 3-layer memory | ✅ Redis + Firestore + Embeddings |
| Response validation | ✅ 3-tier fallback, never empty |
| Async memory writes | ✅ Non-blocking background tasks |
| Structured logging | ✅ JSON logs with request_id correlation |
| Redis memory debouncing | ✅ Celery Beat flush every 5 min |
| Rate limiting | ✅ slowapi, 15 req/min/user |
| JWT auth | ✅ Firebase tokens |
| Payments | ✅ Razorpay orders + webhooks |
| Image generation | ✅ Together AI FLUX.1 |
| Celery workers | ✅ Background processing |
| Sentry monitoring | ✅ Error tracking (if DSN configured) |
| CI/CD pipelines | ✅ Auto-deploy on push |
