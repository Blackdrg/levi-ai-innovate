# LEVI-AI v5.0+ GCP Setup Script (PowerShell)
# Description: Provisions all necessary GCP services.

$ErrorActionPreference = "Stop"

$ProjectID = (gcloud config get-value project)
$Region = $Env:GCP_REGION -replace "", "us-central1"

Write-Host "🚀 Starting GCP Setup for LEVI-AI in project: $ProjectID ($Region)" -ForegroundColor Cyan

# 1. Enable Required APIs
Write-Host "📡 Enabling APIs..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    cloudtasks.googleapis.com `
    firestore.googleapis.com `
    redis.googleapis.com `
    secretmanager.googleapis.com `
    storage.googleapis.com `
    artifactregistry.googleapis.com `
    cloudbuild.googleapis.com

# 2. Create Cloud Storage Buckets
Write-Host "📦 Creating Storage Buckets..." -ForegroundColor Yellow
try { gsutil mb -p $ProjectID -l $Region "gs://levi-media-$ProjectID" } catch { Write-Host "Bucket exists." }
try { gsutil mb -p $ProjectID -l $Region "gs://levi-models-$ProjectID" } catch { Write-Host "Bucket exists." }

# 3. Initialize Firestore (Native Mode)
Write-Host "🔥 Initializing Firestore..." -ForegroundColor Yellow
try { gcloud firestore databases create --location=$Region --type=native } catch { Write-Host "Database exists." }

# 4. Create Memorystore (Redis)
Write-Host "⚡ Creating Memorystore for Redis..." -ForegroundColor Yellow
try { gcloud redis instances create levi-cache --size=1 --region=$Region --redis-version=redis_6_x --tier=standard } catch { Write-Host "Instance exists." }

# 5. Create Cloud Tasks Queue
Write-Host "📨 Creating Cloud Tasks Queue..." -ForegroundColor Yellow
try { gcloud tasks queues create levi-jobs-queue --location=$Region } catch { Write-Host "Queue exists." }

# 6. Setup Secret Manager Placeholders
Write-Host "🔒 Creating Secret Manager Placeholders..." -ForegroundColor Yellow
$Secrets = @("GROQ_API_KEY", "TOGETHER_API_KEY", "SECRET_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET")
foreach ($Secret in $Secrets) {
    try { gcloud secrets create $Secret --replication-policy="automatic" } catch { Write-Host "Secret $Secret exists." }
}

Write-Host "✅ GCP Setup Complete!" -ForegroundColor Green
Write-Host "Media Bucket: gs://levi-media-$ProjectID"
Write-Host "Queue: levi-jobs-queue ($Region)"
