. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot
    Invoke-DockerCompose @("up", "-d", "--build", "frontend")
    Invoke-DockerCompose @("restart", "frontend")
    Write-Host ""
    Write-Host "前端已重新构建并重启。浏览器建议按 Ctrl + F5。" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
