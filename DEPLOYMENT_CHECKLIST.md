# 🚀 LEVI Production Deployment Checklist

Follow these phases in order to launch LEVI with real payments, AI generation, and scalable storage.

## Phase A: Razorpay Setup (15 min)
1.  **Create Account**: Log in to [dashboard.razorpay.com](https://dashboard.razorpay.com).
2.  **Generate API Keys**: 
    *   Go to Settings -> API Keys -> Generate Key.
    *   Save `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
3.  **Setup Webhook**:
    *   Go to Settings -> Webhooks -> Add New Webhook.
    *   Webhook URL: `https://your-backend-url.com/razorpay_webhook`.
    *   Secret: Create a random string and save as `RAZORPAY_WEBHOOK_SECRET`.
    *   Active Events: `payment.captured`.

## Phase B: AWS S3 Setup (10 min)
1.  **Create Bucket**: Create a bucket named `levi-assets` (or similar).
2.  **IAM User**: Create an IAM user with `AmazonS3FullAccess`.
3.  **Get Credentials**: Save the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
4.  **Set Region**: Note your region (e.g., `us-east-1`).

## Phase C: Together.AI & Groq (5 min)
1.  **Together.AI**: Go to [api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys) and get `TOGETHER_API_KEY`.
2.  **Groq Cloud**: Go to [console.groq.com/keys](https://console.groq.com/keys) and get `GROQ_API_KEY`.

## Phase D: Environment Variables
Add these to your Render/Production environment:
*   `DATABASE_URL`: Your production Postgres URL.
*   `REDIS_URL`: Your production Redis URL.
*   `SECRET_KEY`: A long random string for JWT.
*   `RAZORPAY_KEY_ID`: From Phase A.
*   `RAZORPAY_KEY_SECRET`: From Phase A.
*   `RAZORPAY_WEBHOOK_SECRET`: From Phase A.
*   `RAZORPAY_PRO_PLAN_AMOUNT`: 29900 (₹299 in paise).
*   `RAZORPAY_CREATOR_PLAN_AMOUNT`: 59900 (₹599 in paise).
*   `AWS_ACCESS_KEY_ID`: From Phase B.
*   `AWS_SECRET_ACCESS_KEY`: From Phase B.
*   `AWS_REGION`: From Phase B.
*   `AWS_S3_BUCKET`: From Phase B.
*   `TOGETHER_API_KEY`: From Phase C.
*   `GROQ_API_KEY`: From Phase C.
*   `RESEND_API_KEY`: Your Resend API key for emails.
*   `USE_CELERY`: Set to `true` for production.
*   `FRONTEND_URL`: `https://levi-ai.create.app` (or your custom domain).

## Phase E: Deploy
1.  **Push Code**: `git push origin main`.
2.  **Verify**: Check Render logs for "Database tables ready" and "Uvicorn running".
3.  **Test**: Perform a test purchase and verify credits in the Studio.

---

## Final Production Status:
✅ Real DB auth (SQLAlchemy)
✅ Groq Llama3 (Text) + Together FLUX (Image)
✅ Razorpay payments (Orders + Webhooks)
✅ Credit system (free/pro/creator tiers)
✅ S3 video/image storage
✅ ImageMagick + ffmpeg in Docker
✅ Daily email system (Resend)
✅ Celery background tasks
✅ Frontend ↔ Backend connected (Vercel → Render)
