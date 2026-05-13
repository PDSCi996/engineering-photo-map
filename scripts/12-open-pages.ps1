. "$PSScriptRoot\_common.ps1"
try {
    Enter-ProjectRoot

    $urls = @(
        "http://localhost:5173",
        "http://localhost:5173/#/diagnostics",
        "http://localhost:8000/api/health"
    )

    foreach ($url in $urls) {
        Write-Host "打开：$url" -ForegroundColor Cyan
        Start-Process $url
    }
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
