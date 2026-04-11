# Qdrant Docker启动脚本
# 重启电脑后执行此脚本

Write-Host "=== Qdrant Docker Migration ===" -ForegroundColor Cyan

# Step 1: Check Docker
Write-Host "Step 1: Checking Docker Desktop..." -ForegroundColor Yellow
$dockerCheck = docker info 2>&1
if ($dockerCheck -match "error") {
    Write-Host "Docker Desktop not running. Please start it manually." -ForegroundColor Red
    Write-Host "Start: C:\Program Files\Docker\Docker\Docker Desktop.exe" -ForegroundColor Yellow
    Read-Host "Press Enter after Docker Desktop starts..."
}

Write-Host "Docker is running!" -ForegroundColor Green

# Step 2: Stop existing container (if any)
Write-Host "Step 2: Stopping existing Qdrant container..." -ForegroundColor Yellow
docker stop qdrant-server 2>$null
docker rm qdrant-server 2>$null

# Step 3: Start Qdrant container
Write-Host "Step 3: Starting Qdrant container..." -ForegroundColor Yellow
$storagePath = "D:\动画\众生界\.vectorstore\qdrant_docker"
docker run -d -p 6333:6333 -p 6334:6334 `
    -v "${storagePath}:/qdrant/storage" `
    --name qdrant-server `
    qdrant/qdrant

Write-Host "Qdrant container started!" -ForegroundColor Green

# Step 4: Verify
Write-Host "Step 4: Verifying Qdrant..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$response = Invoke-WebRequest -Uri "http://localhost:6333/collections" -UseBasicParsing
Write-Host "Qdrant API response: $($response.StatusCode)" -ForegroundColor Green

Write-Host @"
=== Migration Ready ===
Next steps:
1. cd D:\动画\众生界\.case-library\scripts
2. python sync_to_qdrant.py --docker --no-resume
"@ -ForegroundColor Cyan

Read-Host "Press Enter to open sync script folder..."
Start-Process "D:\动画\众生界\.case-library\scripts"