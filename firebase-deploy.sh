#!/bin/bash
# DEPLOY LEVI BACKEND TO GOOGLE CLOUD RUN
# This script builds the backend container and deploys it.

PROJECT_ID=$(firebase target:shell --site levi-ai-innovate -e "process.stdout.write(config.project)" 2>/dev/null || echo "levi-ai-c23c6")
SERVICE_NAME="levi-backend"
REGION="us-central1"

echo "🚀 Starting deployment for project: $PROJECT_ID"

# 1. Enable APIs
echo "📡 Enabling required APIs..."
gcloud services enable artifactregistry.googleapis.com run.googleapis.com --project "$PROJECT_ID"

# 2. Create Artifact Registry if it doesn't exist
echo "📦 Ensuring Artifact Registry exists..."
gcloud artifacts repositories create levi-repo --repository-format=docker --location="$REGION" --project "$PROJECT_ID" 2>/dev/null || true

# 3. Build Frontend
echo "🎨 Building Frontend (Tailwind)..."
npm run --prefix frontend build || { echo "❌ Frontend build failed"; exit 1; }

# 4. Build and Push Backend
IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/levi-repo/$SERVICE_NAME:latest"
echo "🛠️ Building image: $IMAGE_URL"
docker build -t "$IMAGE_URL" -f backend/Dockerfile.prod .
echo "📤 Pushing image..."
docker push "$IMAGE_URL"

# 5. Deploy to Cloud Run
# IMPORTANT: Include ALL required environment variables here.
# You can set these in GCP Console or via Secret Manager for better security.
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URL" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --project "$PROJECT_ID" \
  --set-env-vars "ENVIRONMENT=production,RENDER=true" \
  --update-env-vars "SECRET_KEY=REPLACE_ME,DATABASE_URL=REPLACE_ME,RAZORPAY_KEY_ID=REPLACE_ME,RAZORPAY_KEY_SECRET=REPLACE_ME,RAZORPAY_WEBHOOK_SECRET=REPLACE_ME,ADMIN_KEY=REPLACE_ME"

# 5. Deploy Frontend to Firebase Hosting
echo "🌐 Deploying Frontend to Firebase Hosting..."
firebase deploy --only hosting --project "$PROJECT_ID"

echo "✅ Deployment complete!"
echo "🔗 Your Frontend is live at: https://levi-ai-innovate.web.app"
echo "🔗 Your Backend is live at: $(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)"
