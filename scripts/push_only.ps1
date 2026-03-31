# Simple push script for LEVI-AI
Write-Host "=== LEVI-AI Quick Push ==="

# Stage all files
Write-Host "Adding all files..."
git add .

# Create a commit
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
Write-Host "Committing changes..."
git commit -m "Update: Quick push ($timestamp)"

# Push to currently set origin
Write-Host "Pushing to main branch..."
git push origin main

Write-Host "=== Push Complete! ==="
