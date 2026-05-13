try {
    chcp 65001 | Out-Null
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8

    Write-Host ""
    Write-Host "中文输出测试" -ForegroundColor Cyan
    Write-Host "如果你能正常看到这几行中文，说明 CMD 启动器 + PowerShell 中文输出正常。"
    Write-Host "当前 scripts 目录：$PSScriptRoot"
    Write-Host ""
} catch {
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Read-Host "按 Enter 退出"
}
