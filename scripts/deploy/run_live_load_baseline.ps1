<#
.SYNOPSIS
Runs k6 load baseline tests at stepped concurrency for Staging/Production environments.
.DESCRIPTION
This script executes the missions_k6.js test across three stepped concurrencies (10, 50, 100).
It then records the output for performance baseline validation and HPA threshold configuration.
#>

$ErrorActionPreference = "Stop"

$ReportFolder = "k6_reports"
if (!(Test-Path $ReportFolder)) {
    New-Item -ItemType Directory -Path $ReportFolder > $null
}

$Concurrencies = @(10, 50, 100)
$Duration = "1m"
$TestScript = "tests/load/missions_k6.js"

Write-Host "Starting LEVI-AI Live Load Baseline Sequence" -ForegroundColor Cyan

# --- Hardening: Pre-flight Health Check ---
$HealthUrl = "http://localhost:8000/health"
$MaxRetries = 5
$RetryCount = 0
$Ready = $false

Write-Host "[CHECK] Verifying backend availability at $HealthUrl..." -ForegroundColor Gray
while ($RetryCount -lt $MaxRetries -and !$Ready) {
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $Ready = $true
            Write-Host "✅ Backend is ONLINE. Starting baseline sequence." -ForegroundColor Green
        }
    } catch {
        $RetryCount++
        if ($RetryCount -lt $MaxRetries) {
            Write-Host "[WAIT] Backend not responding. Retrying in 5s ($RetryCount/$MaxRetries)..." -ForegroundColor Gray
            Start-Sleep -Seconds 5
        }
    }
}

if (!$Ready) {
    Write-Host "❌ FATAL: Backend refused connection after $MaxRetries attempts. Please start the server using 'run-dev.bat' or 'python -m uvicorn backend.api.main:app' and try again." -ForegroundColor Red
    exit 1
}

foreach ($VUs in $Concurrencies) {
    Write-Host "`n[STEP] Running load test with $VUs Concurrent VUs for $Duration..." -ForegroundColor Yellow
    $OutputFile = "$ReportFolder\k6_results_vus_${VUs}.json"
    
    # Run k6 and export results exactly to capture p50, p95, p99 limits natively
    k6 run $TestScript --vus $VUs --duration $Duration --summary-export=$OutputFile
    
    if ($LastExitCode -ne 0 -and $LastExitCode -ne 104) {
        Write-Host "[WARNING] k6 exited with code $LastExitCode." -ForegroundColor Red
    } else {
        Write-Host "Successfully completed $VUs VU test." -ForegroundColor Green
        
        # Simple extraction example from json format (requires k6 json to be parseable)
        try {
            $jsonData = Get-Content -Raw -Path $OutputFile | ConvertFrom-Json
            $p95 = $jsonData.metrics.http_req_duration.values."p(95)"
            Write-Host "P95 latency at $VUs VUs: $p95 ms" -ForegroundColor Cyan
        } catch {
            Write-Host "Metric extraction skipped." -ForegroundColor Gray
        }
    }
}

Write-Host "`n[DONE] Baseline metrics generated. Please inspect $ReportFolder to wire limits into HPA." -ForegroundColor Green
Write-Host "Update your spec.metrics configurations in the Kubernetes HPA manifest based on peak load stability." -ForegroundColor Green
