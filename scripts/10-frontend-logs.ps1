. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot
    Invoke-DockerCompose @("logs", "--tail=120", "frontend")
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
