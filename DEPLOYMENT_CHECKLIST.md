# 🚀 LEVI Production Deployment Checklist

Follow these phases in order to launch LEVI with real payments, AI generation, and scalable storage.

## Phase A: Razorpay Setup (15 min)

1. **Create Account**: Log in to [dashboard.razorpay.com](https://dashboard.razorpay.com).
2. **Generate API Keys**:
    * Go to Settings -> API Keys -> Generate Key.
    * Save `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
3. **Setup Webhook**:
    * Go to Settings -> Webhooks -> Add New Webhook.
    * Webhook URL: `https://your-backend-url.com/razorpay_webhook`.
    * Secret: Create a random string and save as `RAZORPAY_WEBHOOK_SECRET`.
    * Active Events: `payment.captured`.

## Phase B: AWS S3 Setup (10 min)

1. **Create Bucket**: Create a bucket named `levi-assets` (or similar).
2. **IAM User**: Create an IAM user with `AmazonS3FullAccess`.
3. **Get Credentials**: Save the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
4. **Set Region**: Note your region (e.g., `us-east-1`).
5. **Public Access**:
    * Ensure "Block all public access" is **OFF** for the bucket.
    * Add a Bucket Policy to allow public reads (or use the code's `ACL='public-read'`):

    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicRead",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::your-bucket-name/*"
            }
        ]
    }
    ```

## Phase C: Together.AI & Groq (5 min)

1. **Together.AI**: Go to [api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys) and get `TOGETHER_API_KEY`.
2. **Groq Cloud**: Go to [console.groq.com/keys](https://console.groq.com/keys) and get `GROQ_API_KEY`.

## Phase D: Environment Variables

Add these to your Google Cloud Run / Firebase environment:

* `DATABASE_URL`: Your production Postgres URL.
* `REDIS_URL`: Your production Redis URL.
* `SECRET_KEY`: A long random string for JWT.
* `RAZORPAY_KEY_ID`: From Phase A.
* `RAZORPAY_KEY_SECRET`: From Phase A.
* `RAZORPAY_WEBHOOK_SECRET`: From Phase A.
* `RAZORPAY_PRO_PLAN_AMOUNT`: 29900 (₹299 in paise).
* `RAZORPAY_CREATOR_PLAN_AMOUNT`: 59900 (₹599 in paise).
* `AWS_ACCESS_KEY_ID`: From Phase B.
* `AWS_SECRET_ACCESS_KEY`: From Phase B.
* `AWS_REGION`: From Phase B.
* `AWS_S3_BUCKET`: From Phase B.
* `TOGETHER_API_KEY`: From Phase C.
* `GROQ_API_KEY`: From Phase C.
* `RESEND_API_KEY`: Your Resend API key for emails.
* `USE_CELERY`: Set to `true` for production.
* `FRONTEND_URL`: `https://levi-ai.create.app` (or your custom domain).
* `VAPID_PUBLIC_KEY`: Your public VAPID key.
* `VAPID_PRIVATE_KEY`: Your private VAPID key.
* `VAPID_ADMIN_EMAIL`: Your admin email (e.g., `admin@yourdomain.com`).
* `ADMIN_KEY`: A secret key for accessing `/admin` endpoints.
* `CLOUDFRONT_DOMAIN`: (Optional) Your CloudFront domain (e.g., `d123.cloudfront.net`) for faster image delivery.

## Phase E: Web Push Notifications (5 min)

1. **Generate Keys**: Run `npx web-push generate-vapid-keys`.
2. **Add to Env**: Add the public, private, and email to your environment.
3. **Frontend Button**: The "Get Daily Wisdom Notifications" button in the Studio will now work.

## Phase F: Deploy

1. **Frontend Build**: Run `cd frontend && npm run build` to generate the production CSS.
2. **Push Code**: `git push origin main`.
3. **Verify**: Check Cloud Run logs for "Database tables ready" and "Uvicorn running".
4. **Test**: Perform a test purchase and verify credits in the Studio.

---

## Final Production Status

✅ Real DB auth (SQLAlchemy)
✅ Groq Llama3 (Text) + Together FLUX (Image)
✅ Razorpay payments (Orders + Webhooks)
✅ Credit system (free/pro/creator tiers)
✅ S3 video/image storage
✅ ImageMagick + ffmpeg in Docker
✅ Daily email system (Resend)
✅ Web Push notifications (pywebpush)
✅ Celery background tasks
✅? Frontend + Backend connected (Firebase Hosting + Cloud Run)
