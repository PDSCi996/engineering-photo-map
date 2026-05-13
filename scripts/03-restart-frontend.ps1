. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot
    Invoke-DockerCompose @("restart", "frontend")
    Write-Host ""
    Write-Host "前端已重启。浏览器建议按 Ctrl + F5 强制刷新。" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
