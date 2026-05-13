# -*- coding: utf-8 -*-
"""
工程照片地图管理系统 - V0.3.29c 正式本机检查脚本修正版

目标：
1. 恢复旧版详细检查项目；
2. 保留 V0.3.28 数据安全 / 运行目录 / 导出规则检查；
3. 增强 Docker frontend 内 npm 检查；
4. 输出正式 Markdown 报告 + 原始日志；
5. 尽量避免把检查脚本自身的低风险提示当成严重问题。

运行：
    tools\\check_all.cmd
或：
    .venv\\Scripts\\python.exe tools\\check_all.py
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
LOGS_DIR = ROOT / "logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

REPORT_FILE = REPORTS_DIR / f"dev-check-{TIMESTAMP}.md"
RAW_LOG_FILE = LOGS_DIR / f"dev-check-raw-{TIMESTAMP}.txt"

EXPECTED_SERVICES = ["db", "redis", "api", "frontend", "worker-media"]
PYTHON_TARGETS_CANDIDATES = ["backend", "worker", "tools"]
RUNTIME_DIRS = [
    "data",
    "data/db",
    "data/postgres",
    "data/uploads",
    "data/thumbnails",
    "data/previews",
    "data/exports",
    "data/backups",
    "logs",
    "reports",
]
DATA_SAFETY_DOCS = [
    "docs/数据目录说明.md",
    "docs/备份恢复说明.md",
    "docs/升级前检查清单.md",
    "docs/V0.4部署准备说明.md",
]

CORE_FILES = [
    "README.md",
    "docker-compose.yml",
    "frontend/package.json",
    "backend/Dockerfile",
    "worker/Dockerfile",
    ".gitignore",
]

GITIGNORE_CORE_RULES = [
    ".env",
    ".venv/",
    "node_modules/",
    "frontend/node_modules/",
    "data/",
    "logs/",
    "reports/",
]

GITIGNORE_EXPORT_RULES = [
    "*_QGIS资料包",
    "*_QGIS资料包_*.zip",
    "*_点位导出_*.csv",
    "*_点位导出_*.geojson",
    "*_QGIS样式_*.qml",
    "*_QGIS使用说明_*.txt",
]

SKIP_SCAN_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "data",
    "logs",
    "reports",
    "_scan_for_github",
}

TEXT_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".vue",
    ".json",
    ".yml",
    ".yaml",
    ".md",
    ".txt",
    ".cmd",
    ".ps1",
    ".env",
    ".example",
}

MEDIA_OR_BIG_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".heic",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".zip",
    ".7z",
    ".rar",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".dump",
    ".bak",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|access[_-]?key|private[_-]?key)\b\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})"),
    re.compile(r"(?i)\bpassword\b\s*[:=]\s*['\"]?([^'\"\s]{8,})"),
    re.compile(r"postgresql\+?[^:]*://[^:\s]+:([^@\s]+)@"),
]

PLACEHOLDER_WORDS = [
    "example",
    "change_me",
    "changeme",
    "your_",
    "placeholder",
    "dummy",
    "test",
    "change_this_password",
    "photo_user",
    "localhost",
    "redis://redis",
    "postgresql+psycopg://photo_user:change_this_password",
]


@dataclass
class Result:
    section: str
    name: str
    status: str
    detail: str = ""
    command: str = ""
    output: str = ""
    critical: bool = False
    advice: str = ""


@dataclass
class State:
    results: list[Result] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    tracked_files: list[str] = field(default_factory=list)
    python_targets: list[str] = field(default_factory=list)

    def add(
        self,
        section: str,
        name: str,
        status: str,
        detail: str = "",
        command: str = "",
        output: str = "",
        critical: bool = False,
        advice: str = "",
    ) -> None:
        self.results.append(
            Result(
                section=section,
                name=name,
                status=status,
                detail=detail,
                command=command,
                output=output,
                critical=critical,
                advice=advice,
            )
        )
        mark = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]", "SKIP": "[SKIP]", "INFO": "[INFO]"}.get(status, status)  # nosec B105
        print(f"{mark} {section} - {name}: {detail}")


def ensure_dirs() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def run_cmd(
    state: State,
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 120,
) -> tuple[int, str]:
    """Run fixed internal command list. User input is not passed to shell."""
    if cwd is None:
        cwd = ROOT
    rendered = " ".join(cmd)
    state.raw_lines.append(f"\n$ {rendered}\n")
    state.raw_lines.append(f"cwd: {cwd}\n")
    try:
        completed = subprocess.run(  # nosec B603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        state.raw_lines.append(output.rstrip() + "\n")
        return completed.returncode, output.strip()
    except FileNotFoundError as exc:
        msg = f"Command not found: {cmd[0]} ({exc})"
        state.raw_lines.append(msg + "\n")
        return 127, msg
    except subprocess.TimeoutExpired as exc:
        msg = f"Command timeout: {rendered} ({exc})"
        state.raw_lines.append(msg + "\n")
        return 124, msg


def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def load_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def tracked_file_list(state: State) -> list[str]:
    code, out = run_cmd(state, ["git", "ls-files", "-z"], timeout=60)
    if code != 0:
        return []
    return [x for x in out.split("\0") if x.strip()]


def has_gitignore_rule(text: str, rule: str) -> bool:
    """Return True if .gitignore contains the requested rule.

    The check is intentionally tolerant: the same rule may be written with a
    trailing slash, Windows separators, or a slightly broader wildcard. This
    avoids warning just because the ignore rule is equivalent but not identical.
    """
    target = rule.replace("\\", "/").strip().rstrip("/")
    lines = []
    for raw_line in text.replace("\\", "/").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line.rstrip("/"))

    if target in lines:
        return True

    # Flexible aliases for exported QGIS/browser results.
    if "QGIS资料包" in target:
        return any("QGIS资料包" in line for line in lines)
    if "点位导出" in target and target.endswith(".csv"):
        return any("点位导出" in line and line.endswith(".csv") for line in lines)
    if "点位导出" in target and target.endswith(".geojson"):
        return any("点位导出" in line and line.endswith(".geojson") for line in lines)
    if "QGIS样式" in target and target.endswith(".qml"):
        return any("QGIS样式" in line and line.endswith(".qml") for line in lines)
    if "QGIS使用说明" in target and target.endswith(".txt"):
        return any("QGIS使用说明" in line and line.endswith(".txt") for line in lines)

    return False


def extract_first_json_object(text: str) -> dict:
    """Extract the first complete JSON object from command output.

    Some tools, especially Bandit on Windows, may print warnings before or after
    the JSON payload. json.loads(text[text.find("{"):]) is therefore not stable.
    This function finds the matching closing brace of the first JSON object.
    """
    start = text.find("{")
    if start < 0:
        return {}

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start: idx + 1])
                except Exception:
                    return {}
    return {}


def is_text_candidate(path: Path) -> bool:
    if any(part in SKIP_SCAN_DIRS for part in path.parts):
        return False
    if path.suffix.lower() in TEXT_EXTS:
        return True
    return path.name.startswith(".env") or path.name in {"Dockerfile", ".gitignore"}


def iter_scan_files() -> Iterable[Path]:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(ROOT).parts
        if any(part in SKIP_SCAN_DIRS for part in rel_parts):
            continue
        if is_text_candidate(Path(*rel_parts)):
            yield path


def safe_read(path: Path, max_bytes: int = 300_000) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def check_basic_environment(state: State) -> None:
    code, out = run_cmd(state, [sys.executable, "--version"])
    state.add("基础环境", "Python 环境", "PASS" if code == 0 else "FAIL", out or "Python unavailable", command=f"{sys.executable} --version", output=out, critical=code != 0)

    code, out = run_cmd(state, ["git", "--version"])
    state.add("基础环境", "Git 环境", "PASS" if code == 0 else "FAIL", out or "Git unavailable", command="git --version", output=out, critical=code != 0)

    state.tracked_files = tracked_file_list(state)
    if state.tracked_files:
        state.add("基础环境", "Git 跟踪文件读取", "PASS", f"已读取 Git 跟踪文件 {len(state.tracked_files)} 个。")
    else:
        state.add("基础环境", "Git 跟踪文件读取", "WARN", "没有读到 Git 跟踪文件；可能不是 Git 仓库或 Git 不可用。")


def check_project_structure(state: State) -> None:
    missing = [p for p in CORE_FILES if not (ROOT / p).exists()]
    if missing:
        state.add("项目结构", "核心文件和目录", "FAIL", "缺失：" + "、".join(missing), critical=True)
    else:
        state.add("项目结构", "核心文件和目录", "PASS", "README、docker-compose、frontend、backend、worker、.gitignore 等核心文件存在。")

    py_targets = [p for p in PYTHON_TARGETS_CANDIDATES if (ROOT / p).exists()]
    state.python_targets = py_targets
    if py_targets:
        state.add("项目结构", "Python 代码目录自动识别", "PASS", "发现 Python 检查目标：" + "、".join(py_targets))
    else:
        state.add("项目结构", "Python 代码目录自动识别", "WARN", "未发现 backend / worker / tools 等 Python 检查目标。")

    runtime_missing = [p for p in RUNTIME_DIRS if not (ROOT / p).exists()]
    if runtime_missing:
        state.add("项目结构", "运行数据目录", "WARN", "缺失：" + "、".join(runtime_missing), advice="可运行 tools\\init_runtime_dirs.cmd 创建。")
    else:
        state.add("项目结构", "运行数据目录", "PASS", "data、logs、reports 及子目录存在。")

    docs_missing = [p for p in DATA_SAFETY_DOCS if not (ROOT / p).exists()]
    if docs_missing:
        state.add("项目结构", "V0.3.28 数据安全文档", "WARN", "缺失：" + "、".join(docs_missing))
    else:
        state.add("项目结构", "V0.3.28 数据安全文档", "PASS", "数据目录、备份恢复、升级前检查、V0.4 部署准备说明存在。")


def check_tools_versions(state: State) -> None:
    tools = [
        ("ruff", [sys.executable, "-m", "ruff", "--version"]),
        ("bandit", [sys.executable, "-m", "bandit", "--version"]),
        ("pip-audit", [sys.executable, "-m", "pip_audit", "--version"]),
        ("pytest", [sys.executable, "-m", "pytest", "--version"]),
    ]
    available = []
    missing = []
    for name, cmd in tools:
        code, out = run_cmd(state, cmd, timeout=60)
        if code == 0:
            available.append(name)
            state.add("检查工具", name, "PASS", out.splitlines()[0] if out else "OK", command=" ".join(cmd), output=out)
        else:
            missing.append(name)
            state.add("检查工具", name, "WARN", "不可用或未安装。", command=" ".join(cmd), output=out, advice="运行 tools\\install_dev_tools.cmd 安装。")
    if missing:
        state.add("检查工具", "开发检查工具完整性", "WARN", "缺少：" + "、".join(missing))
    else:
        state.add("检查工具", "开发检查工具完整性", "PASS", "ruff、bandit、pip-audit、pytest 均可用。")


def check_gitignore_and_privacy(state: State) -> None:
    gitignore_path = ROOT / ".gitignore"
    text = safe_read(gitignore_path)
    if not text:
        state.add("Git 与隐私", ".gitignore 读取", "FAIL", ".gitignore 不存在或无法读取。", critical=True)
        return

    missing_core = [r for r in GITIGNORE_CORE_RULES if not has_gitignore_rule(text, r)]
    if missing_core:
        state.add("Git 与隐私", ".gitignore 核心规则", "WARN", "建议补充：" + "、".join(missing_core))
    else:
        state.add("Git 与隐私", ".gitignore 核心规则", "PASS", "常见日志、报告、缓存、数据、上传目录已配置忽略。")

    missing_export = [r for r in GITIGNORE_EXPORT_RULES if not has_gitignore_rule(text, r)]
    if missing_export:
        state.add("Git 与隐私", ".gitignore 导出规则", "WARN", "建议补充 QGIS/导出成果忽略规则。")
    else:
        state.add("Git 与隐私", ".gitignore 导出规则", "PASS", "QGIS 资料包、点位导出、QML、说明 TXT 等导出成果已配置忽略。")

    tracked = set(state.tracked_files)
    sensitive_tracked = [
        f for f in tracked
        if f == ".env"
        or f.startswith("data/")
        or f.startswith("logs/")
        or f.startswith("reports/")
        or f.startswith("uploads/")
        or f.startswith("media/")
    ]
    if sensitive_tracked:
        state.add("Git 与隐私", "Git 隐私文件跟踪检查", "FAIL", "以下敏感路径被 Git 跟踪：" + "、".join(sensitive_tracked[:20]), critical=True)
    else:
        state.add("Git 与隐私", "Git 隐私文件跟踪检查", "PASS", ".env、logs、reports、data、uploads 等未被 Git 跟踪。")

    media_tracked = [f for f in tracked if Path(f).suffix.lower() in MEDIA_OR_BIG_EXTS]
    if media_tracked:
        state.add("Git 与隐私", "Git 大文件/媒体文件检查", "WARN", "发现可能不应提交的大文件/媒体：" + "、".join(media_tracked[:20]))
    else:
        state.add("Git 与隐私", "Git 大文件/媒体文件检查", "PASS", "未发现常见媒体/数据库/压缩包被 Git 跟踪。")

    code, out = run_cmd(state, ["git", "status", "--short"], timeout=60)
    if code == 0:
        state.add("Git 与隐私", "Git 当前状态", "PASS", "已读取 git status。", command="git status --short", output=out)
        risky = []
        for line in out.splitlines():
            item = line[3:].replace("\\", "/").strip().strip('"')
            if item.startswith(("data/", "logs/", "reports/", ".env")):
                risky.append(item)
        if risky:
            state.add("Git 与隐私", "Git 待提交敏感路径", "WARN", "发现可能误提交路径：" + "、".join(risky[:20]))
        else:
            state.add("Git 与隐私", "Git 待提交敏感路径", "PASS", "git status 中未发现 data/logs/reports/.env 等敏感路径。")
    else:
        state.add("Git 与隐私", "Git 当前状态", "WARN", "git status 执行失败。", command="git status --short", output=out)


def check_secret_scan(state: State) -> None:
    hits = []
    for path in iter_scan_files():
        text = safe_read(path)
        if not text:
            continue
        for pattern in SECRET_PATTERNS:
            for m in pattern.finditer(text):
                snippet = m.group(0)
                low = snippet.lower()
                if any(word in low for word in PLACEHOLDER_WORDS):
                    continue
                hits.append(f"{rel(path)}: {snippet[:80]}")
                if len(hits) >= 20:
                    break
            if len(hits) >= 20:
                break
        if len(hits) >= 20:
            break

    if hits:
        state.add("安全扫描", "敏感信息文本扫描", "WARN", "发现疑似密钥/密码，请人工确认。", output="\n".join(hits), advice="确认不是示例值后，应移入 .env。")
    else:
        state.add("安全扫描", "敏感信息文本扫描", "PASS", "未发现明显真实密钥；示例密码、环境变量占位符已自动忽略。")

    compose = safe_read(ROOT / "docker-compose.yml")
    if "change_this_password" in compose or "photo_user" in compose:
        state.add("安全扫描", "默认数据库账号提示", "INFO", "docker-compose.yml 仍使用开发默认账号 photo_user/change_this_password；本机开发可用，V0.4 部署前应改为 .env。")
    else:
        state.add("安全扫描", "默认数据库账号提示", "PASS", "未发现 photo_user/change_this_password 默认账号。")


def check_python_quality(state: State) -> None:
    targets = state.python_targets
    if not targets:
        state.add("Python 检查", "Python 代码规范/测试", "SKIP", "没有 Python 检查目标。")
        return

    # Syntax check by ast parse, clearer than compileall output for users.
    syntax_errors = []
    for target in targets:
        for path in (ROOT / target).rglob("*.py"):
            parts = path.relative_to(ROOT).parts
            if any(p in SKIP_SCAN_DIRS for p in parts):
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
            except SyntaxError as exc:
                syntax_errors.append(f"{rel(path)}:{exc.lineno} {exc.msg}")

    if syntax_errors:
        state.add("Python 检查", "Python 语法检查", "FAIL", "发现语法错误。", output="\n".join(syntax_errors), critical=True)
    else:
        state.add("Python 检查", "Python 语法检查", "PASS", "Python 文件语法正常。")

    code, out = run_cmd(state, [sys.executable, "-m", "ruff", "check", *targets], timeout=180)
    state.add(
        "Python 检查",
        "ruff 代码规范",
        "PASS" if code == 0 else "WARN",
        "未发现明显代码规范问题。" if code == 0 else f"ruff 返回码 {code}。",
        command=f"{sys.executable} -m ruff check {' '.join(targets)}",
        output=out,
        advice="按 ruff 输出修复未使用导入、格式和简单代码问题。",
    )

    bandit_cmd = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        *targets,
        "-x",
        ".git,.pytest_cache,.ruff_cache,.venv,__pycache__,build,data,dist,logs,media,node_modules,originals,previews,reports,thumbnails,uploads,venv",
        "-f",
        "json",
    ]
    code, out = run_cmd(state, bandit_cmd, timeout=240)
    data = extract_first_json_object(out)

    issues = data.get("results", []) if isinstance(data, dict) else []
    serious = []
    low_only = []
    for issue in issues:
        sev = str(issue.get("issue_severity", "")).upper()
        filename = str(issue.get("filename", ""))
        test_id = issue.get("test_id", "")
        line = issue.get("line_number", "")
        text = issue.get("issue_text", "")
        item = f"{filename}:{line} [{test_id}] {sev} {text}"
        if sev in {"MEDIUM", "HIGH"}:
            serious.append(item)
        else:
            low_only.append(item)

    if serious:
        state.add("Python 检查", "bandit 安全扫描", "WARN", f"发现 {len(serious)} 个中/高等级安全提示。", command=" ".join(bandit_cmd), output="\n".join(serious[:50]), advice="优先处理 MEDIUM/HIGH。")
    elif low_only:
        state.add("Python 检查", "bandit 安全扫描", "PASS", f"仅发现 {len(low_only)} 个 LOW 级提示，未作为阻断项。", command=" ".join(bandit_cmd), output="\n".join(low_only[:50]))
    elif code == 0:
        state.add("Python 检查", "bandit 安全扫描", "PASS", "未发现 bandit 安全问题。", command=" ".join(bandit_cmd), output=out)
    else:
        state.add("Python 检查", "bandit 安全扫描", "WARN", f"bandit 返回码 {code}，但未解析到明确问题。", command=" ".join(bandit_cmd), output=out)

    code, out = run_cmd(state, [sys.executable, "-m", "pip_audit", "-f", "json"], timeout=240)
    vulns = []
    data = extract_first_json_object(out)
    if isinstance(data, dict):
        for dep in data.get("dependencies", []):
            for vuln in dep.get("vulns", []):
                vulns.append(f"{dep.get('name')} {dep.get('version')}: {vuln.get('id', '')} {vuln.get('description', '')[:120]}")
    if vulns:
        state.add("Python 检查", "pip-audit 依赖漏洞", "WARN", f"发现 {len(vulns)} 个依赖漏洞。", command=f"{sys.executable} -m pip_audit -f json", output="\n".join(vulns[:50]), advice="先运行 tools\\install_dev_tools.cmd 或升级对应依赖。")
    elif code == 0:
        state.add("Python 检查", "pip-audit 依赖漏洞", "PASS", "未发现已知 Python 依赖漏洞。", command=f"{sys.executable} -m pip_audit -f json", output=out)
    else:
        state.add("Python 检查", "pip-audit 依赖漏洞", "WARN", f"pip-audit 返回码 {code}。", command=f"{sys.executable} -m pip_audit -f json", output=out)

    tests_dir = ROOT / "tests"
    if tests_dir.exists():
        code, out = run_cmd(state, [sys.executable, "-m", "pytest", "tests", "-q"], timeout=240)
        state.add("Python 检查", "pytest 自动测试", "PASS" if code == 0 else "FAIL", "pytest 自动测试通过。" if code == 0 else f"pytest 返回码 {code}。", command=f"{sys.executable} -m pytest tests -q", output=out, critical=code != 0)
    else:
        state.add("Python 检查", "pytest 自动测试", "SKIP", "暂未发现 tests 目录。")


def check_docker(state: State) -> None:
    code, out = run_cmd(state, ["docker", "version"], timeout=120)
    state.add("Docker 检查", "Docker 状态", "PASS" if code == 0 else "WARN", "Docker 可用，Docker Desktop 应已启动。" if code == 0 else "Docker 不可用或未启动。", command="docker version", output=out)

    code, out = run_cmd(state, ["docker", "compose", "config", "--services"], timeout=120)
    if code == 0:
        services = [s.strip() for s in out.splitlines() if s.strip()]
        state.services = services
        missing = [s for s in EXPECTED_SERVICES if s not in services]
        if missing:
            state.add("Docker 检查", "Docker Compose 服务识别", "WARN", "缺少服务：" + "、".join(missing), command="docker compose config --services", output=out)
        else:
            state.add("Docker 检查", "Docker Compose 服务识别", "PASS", "发现服务：" + "、".join(services), command="docker compose config --services", output=out)
    else:
        state.add("Docker 检查", "Docker Compose 服务识别", "WARN", "docker compose config 执行失败。", command="docker compose config --services", output=out)

    code, out = run_cmd(state, ["docker", "compose", "config"], timeout=120)
    state.add("Docker 检查", "Docker Compose 配置完整性", "PASS" if code == 0 else "WARN", "docker compose config 正常。" if code == 0 else "docker compose config 失败。", command="docker compose config", output=out)

    code, out = run_cmd(state, ["docker", "compose", "ps"], timeout=120)
    state.add("Docker 检查", "Docker Compose 运行状态", "PASS" if code == 0 else "WARN", "已读取 docker compose ps。" if code == 0 else "docker compose ps 失败。", command="docker compose ps", output=out)


def npm_in_frontend_container(state: State, args: list[str], timeout: int = 240) -> tuple[int, str, str]:
    cmd = ["docker", "compose", "exec", "-T", "frontend", "npm", *args]
    code, out = run_cmd(state, cmd, timeout=timeout)
    return code, out, " ".join(cmd)


def check_frontend(state: State) -> None:
    pkg_path = ROOT / "frontend" / "package.json"
    if not pkg_path.exists():
        state.add("前端检查", "前端项目识别", "SKIP", "未发现 frontend/package.json。")
        return

    pkg = load_json_file(pkg_path)
    scripts = pkg.get("scripts", {}) if isinstance(pkg.get("scripts", {}), dict) else {}
    state.add("前端检查", "前端项目识别", "PASS", f"发现前端项目：frontend；package：{pkg.get('name', '-')}；scripts：{', '.join(scripts.keys()) or '-'}")

    local_npm = command_exists("npm")
    if local_npm:
        code, out = run_cmd(state, ["npm", "--version"], cwd=ROOT / "frontend", timeout=60)
        state.add("前端检查", "npm 可用性：本机", "PASS" if code == 0 else "WARN", out or "npm unavailable", command="npm --version", output=out)
    else:
        state.add("前端检查", "npm 可用性：本机", "INFO", "本机未找到 npm，将优先使用 Docker frontend 容器。")

    if "frontend" in state.services:
        code, out, cmd = npm_in_frontend_container(state, ["--version"], timeout=60)
        npm_ok = code == 0
        state.add("前端检查", "npm 可用性：Docker frontend", "PASS" if npm_ok else "WARN", out if npm_ok else "frontend 容器 npm 不可用。", command=cmd, output=out)
    else:
        npm_ok = False
        state.add("前端检查", "npm 可用性：Docker frontend", "SKIP", "docker-compose 中未识别到 frontend 服务。")

    def run_script(script: str, title: str, critical: bool = False) -> None:
        if script not in scripts:
            state.add("前端检查", title, "SKIP", f"package.json 中没有 {script} 脚本。")
            return
        if not npm_ok:
            state.add("前端检查", title, "SKIP", "没有可用 npm 环境。")
            return
        code, out, cmd = npm_in_frontend_container(state, ["run", script], timeout=360)
        state.add(
            "前端检查",
            title,
            "PASS" if code == 0 else ("FAIL" if critical else "WARN"),
            f"{script} 通过。" if code == 0 else f"{script} 返回码 {code}。",
            command=cmd,
            output=out,
            critical=critical and code != 0,
            advice="优先查看 tsconfig.json、package.json、App.vue / style.css 最近修改。",
        )

    run_script("typecheck", "前端 TypeScript 类型检查", critical=False)
    run_script("lint", "前端 lint/type-check", critical=False)
    run_script("build", "前端生产构建 build", critical=True)
    run_script("test", "前端 test", critical=False)

    if not npm_ok:
        state.add("前端检查", "npm audit high", "SKIP", "没有可用 npm 环境。")
    else:
        # npm audit depends on lock file. In this project frontend/package-lock.json should exist.
        if not (ROOT / "frontend" / "package-lock.json").exists():
            state.add("前端检查", "npm audit high", "WARN", "frontend/package-lock.json 不存在，npm audit 结果可能不可用。")
        code, out, cmd = npm_in_frontend_container(state, ["audit", "--audit-level=high"], timeout=240)
        state.add("前端检查", "npm audit high", "PASS" if code == 0 else "WARN", "未发现 high 及以上 npm 依赖漏洞。" if code == 0 else f"npm audit 返回码 {code}。", command=cmd, output=out)


def check_api_health(state: State) -> None:
    import urllib.error
    import urllib.request

    targets = [
        ("后端健康检查", "http://localhost:8000/api/health"),
        ("前端页面访问", "http://localhost:5173/"),
    ]
    for name, url in targets:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:  # nosec B310
                body = resp.read(300).decode("utf-8", errors="replace")
                status = getattr(resp, "status", 0)
            if 200 <= status < 400:
                state.add("运行连通性", name, "PASS", f"{url} 返回 HTTP {status}。", output=body)
            else:
                state.add("运行连通性", name, "WARN", f"{url} 返回 HTTP {status}。", output=body)
        except Exception as exc:
            state.add("运行连通性", name, "WARN", f"{url} 暂不可访问：{exc}", advice="如未启动 Docker，可先运行 docker compose up -d。")


def write_report(state: State) -> None:
    counts = {k: sum(1 for r in state.results if r.status == k) for k in ["PASS", "WARN", "FAIL", "SKIP", "INFO"]}
    critical_fail = any(r.status == "FAIL" and r.critical for r in state.results)

    sections: dict[str, list[Result]] = {}
    for r in state.results:
        sections.setdefault(r.section, []).append(r)

    lines: list[str] = []
    lines.append("# 工程照片地图管理系统 - V0.3.29b 正式本机检查报告")
    lines.append("")
    lines.append(f"- 检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 项目目录：`{ROOT}`")
    lines.append(f"- Python：`{sys.executable}`")
    lines.append("")
    lines.append("## 一、检查结果汇总")
    lines.append("")
    lines.append(f"- 通过 PASS：{counts['PASS']} 项")
    lines.append(f"- 警告 WARN：{counts['WARN']} 项")
    lines.append(f"- 失败 FAIL：{counts['FAIL']} 项")
    lines.append(f"- 跳过 SKIP：{counts['SKIP']} 项")
    lines.append(f"- 信息 INFO：{counts['INFO']} 项")
    lines.append(f"- 是否存在关键失败：{'是' if critical_fail else '否'}")
    lines.append("")
    lines.append("## 二、检查项目总表")
    lines.append("")
    lines.append("| 状态 | 分类 | 检查项 | 说明 |")
    lines.append("|---|---|---|---|")
    for r in state.results:
        lines.append(f"| {r.status} | {r.section} | {r.name} | {r.detail.replace('|', '/')} |")
    lines.append("")
    lines.append("## 三、分项详情")
    lines.append("")
    for section, items in sections.items():
        lines.append(f"### {section}")
        lines.append("")
        for i, r in enumerate(items, 1):
            zh = {"PASS": "通过", "WARN": "警告", "FAIL": "失败", "SKIP": "跳过", "INFO": "信息"}.get(r.status, r.status)  # nosec B105
            lines.append(f"#### {i}. {zh}：{r.name}")
            lines.append("")
            lines.append(f"- 状态：`{r.status}`")
            lines.append(f"- 说明：{r.detail or '-'}")
            if r.advice:
                lines.append(f"- 建议：{r.advice}")
            if r.command:
                lines.append(f"- 命令：`{r.command}`")
            if r.output:
                lines.append("")
                lines.append("<details>")
                lines.append("<summary>查看详情</summary>")
                lines.append("")
                lines.append("```text")
                # Avoid massive report; raw log has full output.
                output = r.output
                if len(output) > 12000:
                    output = output[:12000] + "\n\n……后续内容已截断，请查看 raw 日志。"
                lines.append(output)
                lines.append("```")
                lines.append("")
                lines.append("</details>")
            lines.append("")
    lines.append("## 四、建议处理顺序")
    lines.append("")
    lines.append("1. 先处理 `FAIL`，尤其是“是否存在关键失败：是”的情况。")
    lines.append("2. 再处理 `WARN`，优先处理前端 build、依赖漏洞、安全扫描、Git 隐私路径。")
    lines.append("3. `INFO` 只是提示，不影响继续开发。")
    lines.append("4. `SKIP` 不一定是错误，通常表示当前项目暂时没有对应脚本或环境。")
    lines.append("5. `logs/` 和 `reports/` 是本机检查报告目录，应保留在本机，但不要提交到 GitHub。")
    lines.append("")
    lines.append("## 五、原始日志")
    lines.append("")
    lines.append(f"- 原始日志文件：`{rel(RAW_LOG_FILE)}`")
    lines.append("")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    RAW_LOG_FILE.write_text("".join(state.raw_lines), encoding="utf-8")

    print("\n" + "=" * 72)
    print("Check report written:")
    print(f"  {REPORT_FILE}")
    print(f"  {RAW_LOG_FILE}")
    print("=" * 72)


def main() -> int:
    ensure_dirs()
    state = State()

    print("=" * 72)
    print("Photo Map - V0.3.29b formal local check")
    print(f"Project root: {ROOT}")
    print("=" * 72)

    check_basic_environment(state)
    check_project_structure(state)
    check_tools_versions(state)
    check_gitignore_and_privacy(state)
    check_secret_scan(state)
    check_python_quality(state)
    check_docker(state)
    check_frontend(state)
    check_api_health(state)
    write_report(state)

    counts = {k: sum(1 for r in state.results if r.status == k) for k in ["PASS", "WARN", "FAIL", "SKIP", "INFO"]}
    critical_fail = any(r.status == "FAIL" and r.critical for r in state.results)

    print("\nSummary:")
    print(f"  PASS: {counts['PASS']}")
    print(f"  WARN: {counts['WARN']}")
    print(f"  FAIL: {counts['FAIL']}")
    print(f"  SKIP: {counts['SKIP']}")
    print(f"  INFO: {counts['INFO']}")
    print(f"  Critical failure: {'YES' if critical_fail else 'NO'}")

    return 1 if critical_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
