# Stripe Setup Guide — LEVI AI
# Follow these steps in order

## STEP 1 — Create Stripe Account
1. Go to https://dashboard.stripe.com/register
2. Complete verification
3. Start in TEST MODE (toggle top-left) for development

## STEP 2 — Create Products
Go to: Dashboard → Products → Add Product

### Product 1: LEVI Pro
- Name: LEVI Pro
- Description: Unlimited AI chat, 300 HD generations/month
- Pricing: Recurring → Monthly → ₹499  (or $6 for USD)
- Click Save → Copy the Price ID (starts with price_)
- Paste into .env as: STRIPE_PRICE_PRO=price_xxxxx

### Product 2: LEVI Creator
- Name: LEVI Creator  
- Description: Unlimited everything, video generation, custom branding
- Pricing: Recurring → Monthly → ₹1499  (or $18 for USD)
- Click Save → Copy the Price ID
- Paste into .env as: STRIPE_PRICE_CREATOR=price_xxxxx

### Product 3: Credit Pack Small (one-time)
- Name: 50 Credits
- Pricing: One time → ₹99
- Paste into .env as: STRIPE_PRICE_CREDITS_SMALL=price_xxxxx

### Product 4: Credit Pack Medium (one-time)
- Name: 200 Credits
- Pricing: One time → ₹299
- Paste into .env as: STRIPE_PRICE_CREDITS_MEDIUM=price_xxxxx

## STEP 3 — Get API Keys
Go to: Dashboard → Developers → API Keys
- Copy "Secret key"    → STRIPE_SECRET_KEY=sk_test_...
- Copy "Publishable key" → STRIPE_PUBLISHABLE_KEY=pk_test_...

## STEP 4 — Set Up Webhook
Go to: Dashboard → Developers → Webhooks → Add Endpoint

### Endpoint URL:
https://your-render-app.onrender.com/payments/webhook

### Select events to listen to:
✅ checkout.session.completed
✅ invoice.payment_succeeded
✅ invoice.payment_failed
✅ customer.subscription.deleted

### After creating:
- Click the webhook → "Signing secret" → Reveal
- Copy whsec_... → paste into .env as STRIPE_WEBHOOK_SECRET=whsec_...

## STEP 5 — Test Locally (Stripe CLI)
Install Stripe CLI: https://stripe.com/docs/stripe-cli

# Forward webhooks to your local server:
stripe listen --forward-to localhost:8000/payments/webhook

# Test a payment:
stripe trigger checkout.session.completed

## STEP 6 — Add to main.py
Add this to backend/main.py after app is created:

    from backend.payments import router as payments_router
    app.include_router(payments_router)

## STEP 7 — Add to requirements.txt
    stripe>=7.0.0
    boto3>=1.34.0
    moviepy>=1.0.3     (optional, for video generation)

## STEP 8 — Switch to LIVE mode
When ready for real payments:
1. Toggle Stripe Dashboard to LIVE mode
2. Replace sk_test_ keys with sk_live_ keys
3. Replace price_ IDs with live mode price IDs
4. Update webhook endpoint to use live mode

## AWS S3 Setup (for video storage)
1. Go to https://aws.amazon.com → Create account
2. IAM → Users → Create User → Attach "AmazonS3FullAccess"
3. Security Credentials → Create Access Key → copy both keys
4. S3 → Create Bucket → name it "levi-media" → region us-east-1
5. Bucket Policy → set public read (or use CloudFront for CDN)
6. Paste keys into .env
