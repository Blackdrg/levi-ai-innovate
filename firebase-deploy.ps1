# LEVI AI Deployment Script (Windows/PowerShell)
# Deploys Backend to Cloud Run and Frontend to Firebase Hosting

$PROJECT_ID = "levi-ai-c23c6"
$SERVICE_NAME = "levi-backend"
$REGION = "us-central1"

Write-Host "Starting deployment for project: $PROJECT_ID" -ForegroundColor Cyan

# 1. Enable APIs
Write-Host "Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable artifactregistry.googleapis.com run.googleapis.com --project $PROJECT_ID

# 2. Create Artifact Registry if it doesn't exist
Write-Host "Ensuring Artifact Registry exists..." -ForegroundColor Yellow
try {
    gcloud artifacts repositories create levi-repo --repository-format=docker --location=$REGION --project $PROJECT_ID 2>$null
} catch {}

# 3. Build Frontend
Write-Host "🎨 Building Frontend (Tailwind)..." -ForegroundColor Yellow
npm run --prefix frontend build
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend build failed"; exit $LASTEXITCODE }

# 4. Build and Push Backend
$IMAGE_URL = "$REGION-docker.pkg.dev/$PROJECT_ID/levi-repo/$SERVICE_NAME:latest"
Write-Host "🛠️ Building image: $IMAGE_URL" -ForegroundColor Yellow
docker build -t $IMAGE_URL -f backend/Dockerfile.prod .
if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit $LASTEXITCODE }

Write-Host "Pushing image..." -ForegroundColor Yellow
docker push $IMAGE_URL
if ($LASTEXITCODE -ne 0) { Write-Error "Docker push failed"; exit $LASTEXITCODE }

# 5. Deploy to Cloud Run
# IMPORTANT: Include ALL required environment variables here.
Write-Host "☁️ Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
  --image $IMAGE_URL `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated `
  --project $PROJECT_ID `
  --set-env-vars "ENVIRONMENT=production,RENDER=true" `
  --update-env-vars "SECRET_KEY=REPLACE_ME,DATABASE_URL=REPLACE_ME,RAZORPAY_KEY_ID=REPLACE_ME,RAZORPAY_KEY_SECRET=REPLACE_ME,RAZORPAY_WEBHOOK_SECRET=REPLACE_ME,ADMIN_KEY=REPLACE_ME"
if ($LASTEXITCODE -ne 0) { Write-Error "Cloud Run deployment failed"; exit $LASTEXITCODE }

# 5. Deploy Frontend to Firebase Hosting
Write-Host "Deploying Frontend to Firebase Hosting..." -ForegroundColor Yellow
firebase deploy --only hosting --project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Error "Firebase Hosting deployment failed"; exit $LASTEXITCODE }

$BACKEND_URL = gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format "value(status.url)" --project $PROJECT_ID

Write-Host "`n[OK] Deployment complete!" -ForegroundColor Green
Write-Host "Frontend live at: https://levi-ai-innovate.web.app" -ForegroundColor Green
Write-Host "Backend live at: $BACKEND_URL" -ForegroundColor Green
