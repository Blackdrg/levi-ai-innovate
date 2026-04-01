# 🛡️ LEVI-AI Production Security & Launch Checklist

Before flipping traffic onto LEVI-AI v7, you MUST execute this rigid audit. The Sovereign OS architecture introduces asynchronous vulnerabilities if proper keys, mounts, and limits are omitted.

---

## 1. Domain & Networking Hardening
- [ ] **Cors Shield:** `CORS_ORIGINS` in your `.env.production` is strictly locked to your frontend domains (e.g., `["https://levi.ai", "https://studio.levi.ai"]`). No `*` wildcards.
- [ ] **HTTPS Enforced:** Load balancers terminate SSL before hitting Uvicorn. The Server relies strictly on `fastapi.middleware.cors`.
- [ ] **Firebase Handshake:** Frontend Firebase Client configuration precisely matches the backend Firebase Admin Service JSON.
- [ ] **GCS Buckets Signed:** Ensure your Google Cloud Storage buckets for Video/Image rendering are strictly **PRIVATE**. Your Python backend must dynamically generate `Signed URLs` to stream media to the client.

## 2. Distributed Memory Matrix (FAISS & Redis)
- [ ] **Persistence Volume Mounts:** If scaling to >1 API Server, FAISS memory matrix data *cannot* be local disk. `VECTOR_DB_PATH` must be mapped to a Network File System or GCS FUSE mount.
- [ ] **Redis Rate Limiting Verified:** Test the `/api/studio/video` endpoint rapidly 5 times to ensure the `backend.db.redis_client.distributed_lock` correctly returns a 429 "Transaction in progress" rather than double-deducting credits.

## 3. Financial Firewall
- [ ] **Razorpay Webhooks Registered:** Ensure the Razorpay Dashboard webhook is pointing correctly to `https://api.domain.com/payments/webhook`.
- [ ] **HMAC Signature Check:** Force a test payload to Razorpay and verify `RAZORPAY_KEY_SECRET` perfectly hashes matching the header `X-Razorpay-Signature`.

## 4. Multi-Modal Generative Assets
- [ ] **MoviePy Dependencies:** Does the container have `ImageMagick` binaries installed globally? MoviePy's TextClip relies heavily on external C-bindings.
- [ ] **TTS Folders:** Execute a test generation to ensure the Coqui TTS runtime model successfully downloaded to `/tmp/tts_models` instead of crashing on a read/write permission deny.

## 5. Environment Health
> [!TIP]
> **Use the Sovereign Probe**
> Fire a test via `GET /admin/orchestrator/stats`. Ensure `redis`, `firestore`, and `groq_api` status reads back as `healthy`.

- [ ] `.env` File scrubbed. No secrets are dynamically baked into frontend build times.
- [ ] `ENVIRONMENT=production` set on FastAPI node to completely disable Celery inline tasks (`task_always_eager=False`).
