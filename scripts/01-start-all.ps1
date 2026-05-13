. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot
    Invoke-DockerCompose @("up", "-d", "--build")
    Write-Host ""
    Write-Host "启动完成。" -ForegroundColor Cyan
    Write-Host "首页：http://localhost:5173" -ForegroundColor Cyan
    Write-Host "系统检测：http://localhost:5173/#/diagnostics" -ForegroundColor Cyan
    Write-Host "后端健康检查：http://localhost:8000/api/health" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
