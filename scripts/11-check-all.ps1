. "$PSScriptRoot\_common.ps1"

function Test-ApiUrl {
    param(
        [string]$Name,
        [string]$Url
    )

    Write-Host ""
    Write-Host "检查：$Name" -ForegroundColor Cyan
    Write-Host $Url

    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $res = Invoke-RestMethod -Uri $Url -TimeoutSec 25
        $sw.Stop()
        Write-Host "结果：正常，用时 $($sw.ElapsedMilliseconds) ms" -ForegroundColor Green

        if ($res -is [string]) {
            Write-Host $res
        } else {
            $res | ConvertTo-Json -Depth 8
        }
        return $true
    } catch {
        Write-Host "结果：失败：$($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

try {
    Enter-ProjectRoot

    $ok = 0
    $fail = 0

    $tests = @(
        @{ Name = "API 健康检查"; Url = "http://localhost:8000/api/health" },
        @{ Name = "数据库连接检查"; Url = "http://localhost:8000/api/db-check" },
        @{ Name = "项目接口检查"; Url = "http://localhost:8000/api/projects" },
        @{ Name = "任务列表接口检查"; Url = "http://localhost:8000/api/tasks" },
        @{ Name = "任务汇总接口检查"; Url = "http://localhost:8000/api/tasks/summary" },
        @{ Name = "Worker / Redis 深度检测"; Url = "http://localhost:8000/api/diagnostics/worker" }
    )

    foreach ($t in $tests) {
        if (Test-ApiUrl -Name $t.Name -Url $t.Url) {
            $ok += 1
        } else {
            $fail += 1
        }
    }

    Write-Host ""
    Write-Host "检测完成：正常 $ok 项，失败 $fail 项。" -ForegroundColor Cyan
    Write-Host "前端系统检测页：http://localhost:5173/#/diagnostics" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pause-End
}
