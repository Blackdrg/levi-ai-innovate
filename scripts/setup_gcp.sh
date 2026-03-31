#!/bin/bash
# LEVI-AI v5.0+ GCP Setup Script
# Description: Provisions all necessary GCP services for a production-grade deployment.

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION=${GCP_REGION:-us-central1}

echo "🚀 Starting GCP Setup for LEVI-AI in project: $PROJECT_ID ($REGION)"

# 1. Enable Required APIs
echo "📡 Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudtasks.googleapis.com \
    firestore.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com

# 2. Create Cloud Storage Buckets
echo "📦 Creating Storage Buckets..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://levi-media-$PROJECT_ID" || true
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://levi-models-$PROJECT_ID" || true

# 3. Initialize Firestore (Native Mode)
echo "🔥 Initializing Firestore..."
gcloud firestore databases create --location="$REGION" --type=native || true

# 4. Create Memorystore (Redis)
echo "⚡ Creating Memorystore for Redis (Standard Tier)..."
gcloud redis instances create levi-cache \
    --size=1 --region="$REGION" \
    --redis-version=redis_6_x \
    --tier=standard || true

# 5. Create Cloud Tasks Queue (for Video/Image Jobs)
echo "📨 Creating Cloud Tasks Queue..."
gcloud tasks queues create levi-jobs-queue --location="$REGION" || true

# 6. Setup Secret Manager Placeholders
echo "🔒 Creating Secret Manager Placeholders..."
for SECRET in "GROQ_API_KEY" "TOGETHER_API_KEY" "SECRET_KEY" "RAZORPAY_KEY_ID" "RAZORPAY_KEY_SECRET"; do
    gcloud secrets create "$SECRET" --replication-policy="automatic" || true
done

echo "✅ GCP Setup Complete! Please populate secrets in the GCP Console."
echo "Media Bucket: gs://levi-media-$PROJECT_ID"
echo "Queue: levi-jobs-queue ($REGION)"
