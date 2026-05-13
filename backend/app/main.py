import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app import models  # noqa: F401
from app.celery_client import REDIS_URL, celery_app
from app.database import Base, engine
from app.routers.assets import router as assets_router
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router


APP_VERSION = "0.3.1"
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))

# v0.4.3a：API 启动等待数据库配置
# DB_STARTUP_RETRY_SECONDS=0 表示一直等待，直到数据库可连接。
DB_STARTUP_RETRY_SECONDS = int(os.getenv("DB_STARTUP_RETRY_SECONDS", "0"))
DB_STARTUP_RETRY_INTERVAL = int(os.getenv("DB_STARTUP_RETRY_INTERVAL", "3"))

app = FastAPI(
    title="工程照片地图管理系统 API",
    version=APP_VERSION,
)


def parse_cors_origins() -> list[str]:
    """
    v0.4.5：从环境变量读取 CORS 白名单。

    用法：
    CORS_ORIGINS=https://photos.example.com:8443,http://localhost:5173

    说明：
    - 本地开发时如果不设置 CORS_ORIGINS，则使用默认 localhost 白名单；
    - 群晖远程访问时，应设置为前端公网地址；
    - 多个来源用英文逗号分隔。
    """
    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://172.18.0.6:5173",
    ]

    raw_value = os.getenv("CORS_ORIGINS", "").strip()

    if not raw_value:
        return default_origins

    origins = [
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    ]

    return origins or default_origins


CORS_ORIGINS = parse_cors_origins()

print(f"[v0.4.5] CORS origins: {CORS_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V0.2.6：开放照片文件访问入口
# 浏览器可访问：
# /media/originals/...
# /media/previews/...
# /media/thumbnails/...
DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(DATA_DIR)), name="media")

app.include_router(projects_router)
app.include_router(assets_router)
app.include_router(tasks_router)


def wait_for_database() -> None:
    """
    v0.4.3a：API 启动时等待 PostgreSQL 真正可连接。

    配置说明：
    - DB_STARTUP_RETRY_SECONDS=0：一直等待，直到数据库可连接；
    - DB_STARTUP_RETRY_SECONDS>0：最多等待指定秒数；
    - DB_STARTUP_RETRY_INTERVAL：每次重试间隔秒数。

    解决问题：
    - PostgreSQL / PostGIS 首次初始化可能较慢；
    - Docker Compose 中 db healthy 后，API 仍可能过早连接失败；
    - 通过启动前主动等待数据库，避免手工重启 API。
    """
    attempt = 0
    last_error: Exception | None = None
    wait_forever = DB_STARTUP_RETRY_SECONDS <= 0
    deadline = None if wait_forever else time.monotonic() + DB_STARTUP_RETRY_SECONDS

    print(
        "[v0.4.3a] Waiting for database before API startup. "
        f"mode={'forever' if wait_forever else str(DB_STARTUP_RETRY_SECONDS) + 's'}, "
        f"interval={DB_STARTUP_RETRY_INTERVAL}s"
    )

    while True:
        attempt += 1

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            print(f"[v0.4.3a] Database is ready. attempts={attempt}")
            return

        except Exception as exc:
            last_error = exc

            if not wait_forever and deadline is not None and time.monotonic() >= deadline:
                raise RuntimeError(
                    "Database was not ready before API startup timeout. "
                    f"timeout={DB_STARTUP_RETRY_SECONDS}s, "
                    f"attempts={attempt}, "
                    f"last_error={last_error}"
                )

            print(
                "[v0.4.3a] Database is not ready yet. "
                f"attempt={attempt}, "
                f"next_retry={DB_STARTUP_RETRY_INTERVAL}s, "
                f"last_error={exc}"
            )

            time.sleep(DB_STARTUP_RETRY_INTERVAL)


def ensure_v031_asset_gps_columns() -> None:
    """
    V0.3.1：给已有 assets 表补充正式地图点位字段。

    注意：
    - SQLAlchemy 的 create_all 只能创建新表，不会自动给旧表加字段；
    - 所以这里用 PostgreSQL 的 ALTER TABLE ADD COLUMN IF NOT EXISTS 做轻量迁移；
    - 同时把旧 exif_json.gps 中已有的经纬度回填到 latitude / longitude。
    """
    statements = [
        "ALTER TABLE assets ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION",
        "ALTER TABLE assets ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION",
        "ALTER TABLE assets ADD COLUMN IF NOT EXISTS gps_source VARCHAR(50)",
        "ALTER TABLE assets ADD COLUMN IF NOT EXISTS gps_status VARCHAR(50) DEFAULT 'none'",
        "UPDATE assets SET gps_status = 'none' WHERE gps_status IS NULL",
        "CREATE INDEX IF NOT EXISTS ix_assets_gps_status ON assets (gps_status)",
        "CREATE INDEX IF NOT EXISTS ix_assets_project_gps ON assets (project_id, latitude, longitude)",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

    backfill_sql = """
    UPDATE assets
    SET
        latitude = NULLIF(exif_json #>> '{gps,latitude}', '')::double precision,
        longitude = NULLIF(exif_json #>> '{gps,longitude}', '')::double precision,
        gps_source = 'exif',
        gps_status = 'valid',
        has_gps = TRUE
    WHERE
        exif_json IS NOT NULL
        AND NULLIF(exif_json #>> '{gps,latitude}', '') IS NOT NULL
        AND NULLIF(exif_json #>> '{gps,longitude}', '') IS NOT NULL
        AND (
            latitude IS NULL
            OR longitude IS NULL
            OR gps_status IS NULL
            OR gps_status = 'none'
        )
    """

    try:
        with engine.begin() as conn:
            conn.execute(text(backfill_sql))
    except Exception as exc:
        print(f"[V0.3.1] GPS 字段回填失败，但不影响 API 启动：{exc}")


@app.on_event("startup")
def on_startup() -> None:
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    ensure_v031_asset_gps_columns()


def _safe_json(data: Any) -> Any:
    """把 Celery inspect 返回对象转成稳定 JSON，避免队列对象无法序列化。"""
    return json.loads(json.dumps(data, default=str, ensure_ascii=False))


def _mask_url(url: str) -> str:
    """隐藏连接串里的密码，避免检测页泄露敏感信息。"""
    if not url:
        return ""

    if "://" not in url or "@" not in url:
        return url

    scheme, rest = url.split("://", 1)
    userinfo, hostinfo = rest.split("@", 1)

    if ":" not in userinfo:
        return url

    username = userinfo.split(":", 1)[0]
    return f"{scheme}://{username}:***@{hostinfo}"


def _build_worker_diagnostics_response(
    *,
    overall_status: str,
    checked_at: str,
    redis_info: dict[str, Any],
    worker_info: dict[str, Any],
    celery_info: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    return {
        "status": overall_status,
        "component": "worker-redis",
        "service": "photo-map-api",
        "version": APP_VERSION,
        "checked_at": checked_at,
        "message": message,
        "redis": redis_info,
        "worker": worker_info,
        "celery": celery_info,
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "photo-map-api",
        "version": APP_VERSION,
        "time": datetime.now().isoformat(timespec="seconds"),
        "media_prefix": "/media",
        "data_dir": str(DATA_DIR),
    }


@app.get("/api/db-check")
def db_check():
    with engine.connect() as conn:
        value = conn.execute(text("SELECT 1")).scalar()

    return {
        "status": "ok",
        "database": "connected",
        "result": value,
    }


@app.get("/api/diagnostics/worker")
def diagnostics_worker():
    """
    V0.2.8.0：Worker / Redis 深度检测接口，作为任务状态中心整理版的系统检测能力继续保留。

    检测内容：
    1. API 容器能否连接 Redis/Celery broker；
    2. worker-media 是否能响应 Celery ping；
    3. worker 是否注册了 media.process_asset 任务；
    4. 返回 worker 队列、任务注册、并发池等简要信息。
    """
    checked_at = datetime.now().isoformat(timespec="seconds")
    required_tasks = ["media.process_asset", "demo.ping"]

    redis_info: dict[str, Any] = {
        "status": "checking",
        "broker_url": _mask_url(REDIS_URL),
    }

    try:
        with celery_app.connection_for_read() as connection:
            connection.ensure_connection(max_retries=1)

        redis_info.update(
            {
                "status": "ok",
                "message": "API 容器可以连接 Redis/Celery broker。",
            }
        )
    except Exception as exc:
        redis_info.update(
            {
                "status": "failed",
                "message": "API 容器无法连接 Redis/Celery broker。",
                "error": str(exc),
            }
        )

        response = _build_worker_diagnostics_response(
            overall_status="failed",
            checked_at=checked_at,
            redis_info=redis_info,
            worker_info={
                "status": "not_checked",
                "message": "Redis 连接失败，未继续检测 worker。",
            },
            celery_info={},
            message="Redis/Celery broker 连接失败。",
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response,
        )

    inspect_client = celery_app.control.inspect(timeout=2)

    try:
        ping_result = _safe_json(inspect_client.ping() or {})
        registered_result = _safe_json(inspect_client.registered() or {})
        active_queues_result = _safe_json(inspect_client.active_queues() or {})
        stats_result = _safe_json(inspect_client.stats() or {})
    except Exception as exc:
        response = _build_worker_diagnostics_response(
            overall_status="failed",
            checked_at=checked_at,
            redis_info=redis_info,
            worker_info={
                "status": "failed",
                "message": "Celery inspect 检测失败。",
                "error": str(exc),
            },
            celery_info={},
            message="Redis 可连接，但无法通过 Celery inspect 检测 worker。",
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response,
        )

    worker_names = sorted(
        set(ping_result.keys())
        | set(registered_result.keys())
        | set(active_queues_result.keys())
        | set(stats_result.keys())
    )

    registered_tasks: list[str] = sorted(
        {
            task_name
            for tasks in registered_result.values()
            for task_name in tasks
        }
    )

    active_queue_names = {
        worker_name: [queue.get("name", "-") for queue in queues]
        for worker_name, queues in active_queues_result.items()
    }

    required_task_status = {
        task_name: task_name in registered_tasks
        for task_name in required_tasks
    }

    worker_info: dict[str, Any] = {
        "status": "ok" if worker_names else "failed",
        "online_count": len(worker_names),
        "workers": worker_names,
        "ping": ping_result,
        "active_queues": active_queue_names,
        "registered_tasks_count": len(registered_tasks),
        "required_tasks": required_task_status,
        "media_process_asset_registered": required_task_status["media.process_asset"],
    }

    celery_info: dict[str, Any] = {
        "required_tasks": required_tasks,
        "registered_tasks": registered_tasks,
        "stats_workers": list(stats_result.keys()),
    }

    if not worker_names:
        response = _build_worker_diagnostics_response(
            overall_status="failed",
            checked_at=checked_at,
            redis_info=redis_info,
            worker_info={
                **worker_info,
                "message": "Redis 可连接，但没有任何 worker 响应 ping。",
            },
            celery_info=celery_info,
            message="Redis 可连接，但 worker-media 可能没有启动或无法连接 Redis。",
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response,
        )

    if not required_task_status["media.process_asset"]:
        return _build_worker_diagnostics_response(
            overall_status="warning",
            checked_at=checked_at,
            redis_info=redis_info,
            worker_info={
                **worker_info,
                "status": "warning",
                "message": "worker 在线，但未检测到 media.process_asset 注册任务。",
            },
            celery_info=celery_info,
            message="worker 在线，但核心照片处理任务未在注册任务列表中出现。",
        )

    return _build_worker_diagnostics_response(
        overall_status="ok",
        checked_at=checked_at,
        redis_info=redis_info,
        worker_info={
            **worker_info,
            "message": "Redis 正常，worker 在线，核心照片处理任务已注册。",
        },
        celery_info=celery_info,
        message="Worker / Redis 深度检测通过。",
    )


@app.post("/api/dev/init-db")
def init_db():
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    ensure_v031_asset_gps_columns()

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    return {
        "status": "ok",
        "message": "数据库表已初始化，并已检查 V0.3.1 GPS 字段",
        "tables": tables,
    }


@app.get("/api/dev/tables")
def list_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    table_columns = {}

    for table_name in tables:
        columns = inspector.get_columns(table_name)
        table_columns[table_name] = [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
            }
            for column in columns
        ]

    return {
        "status": "ok",
        "tables": table_columns,
    }


@app.get("/api/dev/task-records")
def list_task_records():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    return {
        "status": "ok",
        "message": "如需查看任务详情，请使用 /api/tasks 接口。",
        "tables": tables,
    }


@app.post("/api/tasks/demo")
def create_demo_task():
    task = celery_app.send_task(
        "demo.ping",
        kwargs={"message": "来自 FastAPI 的测试任务"},
    )

    return {
        "status": "queued",
        "task_id": task.id,
    }


@app.get("/api/tasks/demo/{task_id}")
def get_demo_task(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }

    if result.ready():
        response["result"] = result.result

    return response