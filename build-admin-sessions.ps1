$source = "modules\orchestrator\lambda\admin-sessions"
$destination = "modules\orchestrator\lambda\packages"

# Create packages directory if it doesn't exist
New-Item -ItemType Directory -Force -Path $destination | Out-Null

# Create zip file
Compress-Archive -Path "$source\index.py" -DestinationPath "$destination\admin-sessions.zip" -Force

Write-Host "✓ Created admin-sessions.zip" -ForegroundColor Green
Write-Host "Size: $((Get-Item "$destination\admin-sessions.zip").Length / 1KB) KB" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. cd environments\dev" -ForegroundColor White
Write-Host "2. terraform plan" -ForegroundColor White
Write-Host "3. terraform apply" -ForegroundColor White
