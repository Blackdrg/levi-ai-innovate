# Set the project URL
$repoUrl = "https://github.com/Blackdrg/levi-ai-innovate"

Write-Host "=== LEVI-AI Repository Migration ==="
Write-Host "Target: $repoUrl"

# Check if origin exists
$remoteExists = git remote | Select-String "origin"

if ($remoteExists) {
    Write-Host "Updating existing 'origin' remote URL..."
    git remote set-url origin "$repoUrl.git"
} else {
    Write-Host "Adding new 'origin' remote URL..."
    git remote add origin "$repoUrl.git"
}

# Stage all files
Write-Host "Adding all files..."
git add .

# Create a commit
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
Write-Host "Committing changes..."
git commit -m "Migration: Push to levi-ai-innovate ($timestamp)"

# Push to master
Write-Host "Pushing to master branch..."
git push -u origin master

Write-Host "=== Migration Complete! ==="
