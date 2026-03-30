# Deployment Guide — LEVI-AI (v5.0)

Follow these steps to deploy the **"Brain" Orchestrator** stack to Google Cloud Run and Firebase Hosting.

## 🖥️ Hardware Infrastructure (v5.0 Core)

> [!IMPORTANT]
> **Cloud Run RAM Recommendation**: Because LEVI now runs local embedding models and high-concurrency orchestration, you **MUST** configure the backend service with at least **2GB RAM** (4GB recommended for heavy Studio usage). Memory-limited instances (<1GB) will encounter `OOMKilled` errors during semantic extraction.

## 💾 GitHub Secrets Checklist (v5.0 Optimized)

You MUST add these to GitHub Settings > Secrets and variables > Actions:

### 🌐 Cloud & Persistence
1. `GCP_SA_KEY`: Service Account JSON (Cloud Run Admin, Storage Admin).
2. `FIREBASE_SERVICE_ACCOUNT_JSON`: Full JSON for Firestore and Analytics.
3. `FIREBASE_PROJECT_ID`: e.g., `levi-ai-c23c6`.
4. `REDIS_URL`: **Mandatory for Orchestrator Orchestration** (Use Upstash for serverless Redis).

### 🧠 AI & Intelligence
5. `GROQ_API_KEY`: Primary inference for Intent and Planning.
6. `TOGETHER_API_KEY`: High-fidelity synthesis and Image generation.
7. `ADMIN_KEY`: X-Admin-Key for maintenance routes.

### 💳 Payments & Growth
8. `RAZORPAY_KEY_ID`: Payment gateway ID.
9. `RAZORPAY_KEY_SECRET`: Payment gateway Secret.
10. `RAZORPAY_WEBHOOK_SECRET`: Webhook verification.

### 📦 Media & Observability
11. `AWS_S3_BUCKET`: (Optional) Falling back to Base64/Firestore if not provided.
12. `SENTRY_DSN`: Recommended for monitoring the new Orchestrator's retries.

## 🚀 Execution Strategy

1. **Push to master**: Triggers the GitHub Actions pipeline (`.github/workflows/master_deploy.yml`).
2. **Backend**: Deployed to Cloud Run on port 8080.
3. **Frontend**: Deployed to Firebase Hosting with proxy rewrites.

## 🧪 Production Verification
- **Brain Check**: `https://levi-api.a.run.app/orchestrator/status`
- **Health Check**: `https://levi-api.a.run.app/health`
- **Launchpad**: `https://levi-ai-c23c6.web.app`
