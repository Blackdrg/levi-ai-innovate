# Deployment Guide — LEVI-AI

Follow these steps to deploy the full stack to Google Cloud Run and Firebase Hosting.

## GitHub Secrets Checklist (15+ Critical Keys)

You MUST add these to GitHub Settings > Secrets and variables > Actions:

### Google Cloud & Firebase
1. `GCP_SA_KEY`: Service Account JSON with Cloud Run Admin & Storage Admin roles.
2. `FIREBASE_SERVICE_ACCOUNT_JSON`: Service Account JSON for Firestore access.
3. `FIREBASE_SERVICE_ACCOUNT_LEVI_AI_C23C6`: Firebase CLI token or Service Account for Hosting deploy.
4. `FIREBASE_PROJECT_ID`: e.g., `levi-ai-c23c6`.
5. `FIREBASE_MESSAGING_SENDER_ID`: From Firebase Console.

### Core Backend & Auth
6. `SECRET_KEY`: Long random string for JWT/Security.
7. `ADMIN_KEY`: Security key for admin routes (`X-Admin-Key`).

### External AI & Services
8. `GROQ_API_KEY`: For fast inference.
9. `TOGETHER_API_KEY`: For image generation/LLMs.
10. `RESEND_API_KEY`: For transactional emails.

### Payments (Razorpay)
11. `RAZORPAY_KEY_ID`: Your Razorpay Key ID.
12. `RAZORPAY_KEY_SECRET`: Your Razorpay Key Secret.
13. `RAZORPAY_WEBHOOK_SECRET`: For payment verification.

### Infrastructure & Monitoring
14. `REDIS_URL`: Connection string for Upstash or Redis.
15. `SENTRY_DSN`: Sentry project DSN for error tracking.
16. `AWS_ACCESS_KEY_ID`: For S3 storage (Optional).
17. `AWS_SECRET_ACCESS_KEY`: For S3 storage (Optional).
18. `AWS_S3_BUCKET`: Your S3 bucket name (Optional).

## Deployment Steps

1. **Push to master**: Any push to the `master` branch will trigger both backend and frontend workflows.
2. **Backend**: Deployed to Cloud Run on port 8080.
3. **Frontend**: Deployed to Firebase Hosting with proxy rewrites for `/api`.

## Verification

Check the health endpoint: `https://your-app.a.run.app/health`
Verify Frontend: `https://levi-ai-c23c6.web.app`
