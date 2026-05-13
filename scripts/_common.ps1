# 工程照片地图管理系统：脚本公共函数
# V0.2.9.3f：参考旧版 CMD 结构
# 规则：
# 1. .cmd 只做 ASCII 启动器，不在 CMD 文件内容里写中文。
# 2. .cmd 调用英文文件名的 .ps1，避免 CMD 解析中文脚本名。
# 3. .ps1 负责中文提示和实际 Docker / API 检测。

$ErrorActionPreference = "Stop"

function Set-ConsoleUtf8 {
    try {
        chcp 65001 | Out-Null
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $OutputEncoding = [System.Text.Encoding]::UTF8
    } catch {
        Write-Host "提示：控制台编码设置失败，不影响后续命令执行。" -ForegroundColor Yellow
    }
}

function Get-ProjectRoot {
    $scriptDir = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $scriptDir "docker-compose.yml")) {
        return $scriptDir
    }

    $current = (Get-Location).Path
    if (Test-Path (Join-Path $current "docker-compose.yml")) {
        return $current
    }

    throw "没有找到 docker-compose.yml。请确认 scripts 文件夹位于项目根目录下。"
}

function Enter-ProjectRoot {
    Set-ConsoleUtf8
    $root = Get-ProjectRoot
    Set-Location $root
    Write-Host ""
    Write-Host "当前项目目录：$root" -ForegroundColor Cyan
    Write-Host ""
}

function Invoke-DockerCompose {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$ArgsList
    )

    Write-Host "执行：docker compose $($ArgsList -join ' ')" -ForegroundColor Green
    & docker compose @ArgsList

    if ($LASTEXITCODE -ne 0) {
        throw "docker compose 命令执行失败，退出码：$LASTEXITCODE"
    }
}

function Pause-End {
    Write-Host ""
    Read-Host "按 Enter 退出"
}
