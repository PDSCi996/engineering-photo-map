. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot
    Invoke-DockerCompose @("restart", "worker-media")
    Write-Host ""
    Write-Host "Worker 已重启。可打开系统检测页检查 Worker / Redis 深度检测。" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
