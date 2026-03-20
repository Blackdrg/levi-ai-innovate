# 🚀 LEVI Production Deployment Checklist

Follow these phases in order to launch LEVI with real payments, AI generation, and scalable storage.

## Phase A: Stripe Setup (15 min)
1.  **Create Account**: Log in to [dashboard.stripe.com](https://dashboard.stripe.com).
2.  **Create Products**:
    *   Create a "Pro Plan" (₹499/month).
    *   Create a "Creator Plan" (₹1499/month).
3.  **Get Price IDs**: Copy the API IDs (starts with `price_...`) for both.
4.  **Get Secret Key**: Copy your `sk_live_...` (or `sk_test_...` for dev).
5.  **Setup Webhook**:
    *   Go to Developers -> Webhooks.
    *   Add endpoint: `https://your-backend-url.com/payments/stripe_webhook`.
    *   Select event: `checkout.session.completed`.
    *   Copy the Signing Secret (`whsec_...`).

## Phase B: AWS S3 Setup (10 min)
1.  **Create Bucket**: Create a bucket named `levi-assets` (or similar).
2.  **IAM User**: Create an IAM user with `AmazonS3FullAccess`.
3.  **Get Credentials**: Save the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
4.  **Set Region**: Note your region (e.g., `us-east-1`).

## Phase C: Together.AI (2 min)
1.  **Regenerate Key**: Go to [api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys).
2.  **Update Env**: Save the new key as `TOGETHER_API_KEY`.

## Phase D: Environment Variables
Add these to your Render/Production environment:
*   `DATABASE_URL`: Your production Postgres URL.
*   `REDIS_URL`: Your production Redis URL.
*   `STRIPE_SECRET_KEY`: From Phase A.
*   `STRIPE_WEBHOOK_SECRET`: From Phase A.
*   `STRIPE_PRO_PRICE_ID`: From Phase A.
*   `STRIPE_CREATOR_PRICE_ID`: From Phase A.
*   `AWS_ACCESS_KEY_ID`: From Phase B.
*   `AWS_SECRET_ACCESS_KEY`: From Phase B.
*   `AWS_REGION`: From Phase B.
*   `AWS_S3_BUCKET`: From Phase B.
*   `TOGETHER_API_KEY`: From Phase C.
*   `USE_CELERY`: Set to `true`.
*   `FRONTEND_URL`: `https://levi-ai.create.app` (or your custom domain).

## Phase E: Deploy
1.  **Push Code**: `git push origin main`.
2.  **Verify**: Check Render logs for "Database tables ready" and "Uvicorn running".
3.  **Test**: Perform a test purchase and verify credits in the Studio.
