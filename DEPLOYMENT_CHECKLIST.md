# 🚀 LEVI Production Deployment Checklist

Follow these phases in order to launch LEVI with real payments (Razorpay), AI generation, and scalable storage.

## Phase A: Razorpay Setup (15 min)

1. **Create Account**: Log in to [razorpay.com](https://razorpay.com).
2. **Generate Keys**:
    * Go to Dashboard -> Settings -> API Keys.
    * Generate a **Test Key** (starts with `rzp_test_...`).
    * Copy both `Key ID` and `Key Secret`.
3. **Setup Webhook**:
    * Go to Settings -> Webhooks.
    * Add endpoint: `https://your-backend-url.com/api/razorpay_webhook`.
    * Select event: `payment.captured`.
    * Copy the secret you set and add it to `RAZORPAY_WEBHOOK_SECRET` in your environment.

## Phase B: AWS S3 Setup (10 min)

1. **Create Bucket**: Create a bucket named `levi-assets` (or similar).
2. **IAM User**: Create an IAM user with `AmazonS3FullAccess`.
3. **Get Credentials**: Save the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
4. **Set Region**: Note your region (e.g., `us-east-1`).

## Phase C: Together.AI (2 min)

1. **Regenerate Key**: Go to [api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys).
2. **Update Env**: Save the new key as `TOGETHER_API_KEY`.

## Phase D: Environment Variables

Add these to your Render/Production environment:

* `DATABASE_URL`: Your production Postgres URL.
* `REDIS_URL`: Your production Redis URL.
* `RAZORPAY_KEY_ID`: From Phase A.
* `RAZORPAY_KEY_SECRET`: From Phase A.
* `RAZORPAY_PRO_PLAN_AMOUNT`: 29900 (for ₹299).
* `RAZORPAY_CREATOR_PLAN_AMOUNT`: 59900 (for ₹599).
* `AWS_ACCESS_KEY_ID`: From Phase B.
* `AWS_SECRET_ACCESS_KEY`: From Phase B.
* `AWS_REGION`: From Phase B.
* `AWS_S3_BUCKET`: From Phase B.
* `TOGETHER_API_KEY`: From Phase C.
* `USE_CELERY`: Set to `true`.
* `FRONTEND_URL`: `https://levi-ai.create.app` (or your custom domain).

## Phase E: Deploy

1. **Push Code**: `git push origin main`.
2. **Verify**: Check Render logs for "Database tables ready" and "Uvicorn running".
3. **Test**: Perform a test purchase using Razorpay Test Mode.
