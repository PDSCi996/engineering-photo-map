. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot
    Invoke-DockerCompose @("restart", "api")
    Write-Host ""
    Write-Host "后端 API 已重启。可打开 http://localhost:8000/api/health 检查。" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
