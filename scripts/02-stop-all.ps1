. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot
    Invoke-DockerCompose @("down")
    Write-Host ""
    Write-Host "服务已停止。" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
