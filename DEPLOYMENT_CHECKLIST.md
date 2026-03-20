# LEVI AI — Production Deployment Checklist
# Follow every step in order. Do not skip.

## ════════════════════════════════════════════
## PHASE A — Stripe Setup (15 minutes)
## ════════════════════════════════════════════

### A1. Create Stripe Account
- [ ] Go to https://dashboard.stripe.com/register
- [ ] Verify your business (required for payouts)
- [ ] Stay in TEST MODE first (toggle top-left of dashboard)

### A2. Create Products
Go to: Products → Add Product

**Product 1 — LEVI Pro**
- [ ] Name: `LEVI Pro`
- [ ] Price: ₹499 / month (Recurring)
- [ ] Click Save → copy Price ID → paste in .env as `STRIPE_PRICE_PRO`

**Product 2 — LEVI Creator**
- [ ] Name: `LEVI Creator`
- [ ] Price: ₹1499 / month (Recurring)
- [ ] Click Save → copy Price ID → paste in .env as `STRIPE_PRICE_CREATOR`

**Product 3 — Credit Pack Small**
- [ ] Name: `50 Credits`
- [ ] Price: ₹99 (One time)
- [ ] Click Save → copy Price ID → paste in .env as `STRIPE_PRICE_CREDITS_SMALL`

**Product 4 — Credit Pack Medium**
- [ ] Name: `200 Credits`
- [ ] Price: ₹299 (One time)
- [ ] Click Save → copy Price ID → paste in .env as `STRIPE_PRICE_CREDITS_MEDIUM`

### A3. Get API Keys
Go to: Developers → API Keys
- [ ] Copy "Secret key" (sk_test_...) → `STRIPE_SECRET_KEY` in .env
- [ ] Copy "Publishable key" (pk_test_...) → `STRIPE_PUBLISHABLE_KEY` in .env

### A4. Create Webhook
Go to: Developers → Webhooks → Add Endpoint
- [ ] Endpoint URL: `https://YOUR-RENDER-APP.onrender.com/payments/webhook`
- [ ] Select events:
  - [x] checkout.session.completed
  - [x] invoice.payment_succeeded
  - [x] invoice.payment_failed
  - [x] customer.subscription.deleted
- [ ] Click Add Endpoint
- [ ] Click "Signing secret" → Reveal → copy whsec_... → `STRIPE_WEBHOOK_SECRET` in .env

### A5. Test Stripe Locally
```bash
# Install Stripe CLI from https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:8000/payments/webhook

# In another terminal, trigger a test event:
stripe trigger checkout.session.completed
# Should see: "User upgraded to pro" in your backend logs
```

---

## ════════════════════════════════════════════
## PHASE B — AWS S3 Setup (10 minutes)
## ════════════════════════════════════════════

### B1. Create AWS Account
- [ ] Go to https://aws.amazon.com → Create account

### B2. Create IAM User
- [ ] AWS Console → IAM → Users → Create User
- [ ] Username: `levi-app`
- [ ] Attach policy: `AmazonS3FullAccess`
- [ ] Click Create → Security Credentials tab
- [ ] Create Access Key → Application running on AWS
- [ ] Download .csv or copy both keys → paste in .env

### B3. Create S3 Bucket
- [ ] AWS Console → S3 → Create Bucket
- [ ] Bucket name: `levi-media`
- [ ] Region: `us-east-1`
- [ ] Uncheck "Block all public access" (for image URLs to work)
- [ ] Acknowledge warning → Create bucket

### B4. Set Bucket Policy (public read for images/videos)
Go to: bucket → Permissions → Bucket Policy → Edit
Paste this policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicRead",
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::levi-media/*"
    }
  ]
}
```
- [ ] Save policy

---

## ════════════════════════════════════════════
## PHASE C — Regenerate Exposed API Key
## ════════════════════════════════════════════

### C1. Together.AI Key (URGENT)
- [ ] Go to https://api.together.xyz/settings/api-keys
- [ ] Delete the key that was shared
- [ ] Create new key → paste in .env as `TOGETHER_API_KEY`
- [ ] Add to Render environment variables

---

## ════════════════════════════════════════════
## PHASE D — Deploy Files to Repository
## ════════════════════════════════════════════

### D1. Replace these files in your project:
- [ ] `backend/main.py`          ← new main.py (DB auth, payments router, S3)
- [ ] `backend/models.py`        ← new models.py (tier, credits, stripe fields)
- [ ] `backend/payments.py`      ← new payments.py (Stripe + webhooks)
- [ ] `backend/tasks.py`         ← new tasks.py (Celery + S3 upload)
- [ ] `backend/image_gen.py`     ← new image_gen.py (Together.AI)
- [ ] `backend/requirements.txt` ← new requirements.txt (stripe, boto3 added)
- [ ] `backend/Dockerfile.prod`  ← new Dockerfile.prod (ImageMagick + ffmpeg)
- [ ] `frontend/js/api.js`       ← fixed api.js (no duplicate export)
- [ ] `vercel.json`              ← fixed vercel.json (static output dir)
- [ ] `.vercelignore`            ← updated (blocks Python detection)

### D2. Update .env on Render
Go to: Render Dashboard → your backend service → Environment
Add ALL keys from `.env.production`:
- [ ] TOGETHER_API_KEY (new regenerated key)
- [ ] STRIPE_SECRET_KEY
- [ ] STRIPE_WEBHOOK_SECRET
- [ ] STRIPE_PRICE_PRO
- [ ] STRIPE_PRICE_CREATOR
- [ ] STRIPE_PRICE_CREDITS_SMALL
- [ ] STRIPE_PRICE_CREDITS_MEDIUM
- [ ] AWS_ACCESS_KEY_ID
- [ ] AWS_SECRET_ACCESS_KEY
- [ ] AWS_REGION
- [ ] AWS_S3_BUCKET
- [ ] FRONTEND_URL
- [ ] CORS_ORIGINS (your Vercel URL)

### D3. Git push
```bash
git add .
git commit -m "feat: production ready - Stripe + S3 + Together.AI + real DB auth"
git push origin main
```
Render and Vercel will auto-deploy.

---

## ════════════════════════════════════════════
## PHASE E — Verify Everything Works
## ════════════════════════════════════════════

### E1. Backend health check
```bash
curl https://YOUR-RENDER-APP.onrender.com/health
# Expected: {"status":"ok","version":"2.1.0"}
```

### E2. Test image generation
```bash
curl -X POST https://YOUR-RENDER-APP.onrender.com/generate_image \
  -H "Content-Type: application/json" \
  -d '{"text":"Test quote","author":"Test","mood":"inspiring"}'
# Expected: {"id":1,"image_b64":"data:image/png;base64,...","image_url":null}
```

### E3. Test registration (now saves to DB)
```bash
curl -X POST https://YOUR-RENDER-APP.onrender.com/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123","email":"test@test.com"}'
# Expected: {"access_token":"eyJ...","token_type":"bearer"}
```

### E4. Test Stripe checkout
```bash
curl -X POST https://YOUR-RENDER-APP.onrender.com/payments/create_checkout \
  -H "Content-Type: application/json" \
  -d '{"plan":"pro","user_id":1}'
# Expected: {"checkout_url":"https://checkout.stripe.com/..."}
```

### E5. Check frontend connects
- [ ] Open your Vercel URL
- [ ] Open browser DevTools → Network tab
- [ ] Look for /api/health request → should return 200
- [ ] Try registering a new account
- [ ] Try generating a quote image

---

## ════════════════════════════════════════════
## PHASE F — Go LIVE with Stripe (when ready)
## ════════════════════════════════════════════

- [ ] Stripe Dashboard → toggle to LIVE mode
- [ ] Re-create the same 4 products in LIVE mode
- [ ] Copy new LIVE price IDs → update Render env vars
- [ ] Replace sk_test_ with sk_live_ keys
- [ ] Update webhook endpoint (Stripe live mode has separate webhooks)
- [ ] Do one real ₹1 test payment to confirm full flow

---

## Current Status After All Steps Complete:
✅ Real DB auth (no in-memory dict)
✅ Together.AI FLUX image generation
✅ Stripe subscriptions + webhooks
✅ Credit system (free/pro/creator tiers)
✅ S3 video/image storage
✅ ImageMagick + ffmpeg in Docker
✅ Daily email system (Resend)
✅ Celery background tasks
✅ Frontend ↔ Backend connected (Vercel → Render)
