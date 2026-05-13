from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.celery_client import celery_app
from app.database import get_db
from app.models import TaskRecord
from app.schemas import TaskRead, TaskStatusRead, TaskSummaryRead


router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
)


VALID_TASK_STATUSES = {"pending", "processing", "done", "failed"}


def normalize_task_status(
    status_filter: str | None,
    task_status: str | None,
) -> str | None:
    """
    V0.2.8.1：
    新参数使用 status，例如：
    /api/tasks?status=done

    同时保留旧参数 task_status，避免旧调用失效：
    /api/tasks?task_status=done
    """
    value = status_filter or task_status

    if value is None:
        return None

    value = value.strip().lower()

    if not value:
        return None

    if value not in VALID_TASK_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"不支持的任务状态：{value}。"
                "当前支持：pending、processing、done、failed。"
            ),
        )

    return value


def apply_task_filters(
    statement,
    project_id: int | None,
    asset_id: int | None,
    final_status: str | None,
):
    if project_id is not None:
        statement = statement.where(
            TaskRecord.payload_json["project_id"].as_integer() == project_id
        )

    if asset_id is not None:
        statement = statement.where(
            TaskRecord.payload_json["asset_id"].as_integer() == asset_id
        )

    if final_status is not None:
        statement = statement.where(TaskRecord.status == final_status)

    return statement


@router.get(
    "",
    response_model=list[TaskRead],
    summary="获取任务列表",
)
def list_tasks(
    project_id: int | None = Query(default=None, description="按项目 ID 过滤"),
    asset_id: int | None = Query(default=None, description="按照片资产 ID 过滤"),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="按任务状态过滤：pending / processing / done / failed",
    ),
    task_status: str | None = Query(
        default=None,
        description="兼容旧参数：按任务状态过滤",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="最多返回任务数量"),
    db: Session = Depends(get_db),
):
    final_status = normalize_task_status(status_filter, task_status)

    statement = select(TaskRecord).order_by(TaskRecord.created_at.desc())

    statement = apply_task_filters(
        statement=statement,
        project_id=project_id,
        asset_id=asset_id,
        final_status=final_status,
    )

    statement = statement.limit(limit)

    tasks = db.scalars(statement).all()

    return tasks


@router.get(
    "/summary",
    response_model=TaskSummaryRead,
    summary="获取任务统计汇总",
)
def get_task_summary(
    project_id: int | None = Query(default=None, description="按项目 ID 过滤"),
    asset_id: int | None = Query(default=None, description="按照片资产 ID 过滤"),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="按任务状态过滤：pending / processing / done / failed",
    ),
    task_status: str | None = Query(
        default=None,
        description="兼容旧参数：按任务状态过滤",
    ),
    db: Session = Depends(get_db),
):
    final_status = normalize_task_status(status_filter, task_status)

    statement = (
        select(TaskRecord.status, func.count(TaskRecord.id))
        .group_by(TaskRecord.status)
        .order_by(TaskRecord.status)
    )

    statement = apply_task_filters(
        statement=statement,
        project_id=project_id,
        asset_id=asset_id,
        final_status=final_status,
    )

    rows = db.execute(statement).all()

    by_status = {row[0]: int(row[1]) for row in rows}

    return {
        "project_id": project_id,
        "asset_id": asset_id,
        "total": sum(by_status.values()),
        "pending": by_status.get("pending", 0),
        "processing": by_status.get("processing", 0),
        "done": by_status.get("done", 0),
        "failed": by_status.get("failed", 0),
        "by_status": by_status,
    }


@router.get(
    "/{task_id}",
    response_model=TaskStatusRead,
    summary="获取单个任务状态",
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task_record = db.get(TaskRecord, task_id)

    if task_record is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在：{task_id}",
        )

    celery_status = None
    ready = None

    if task_record.celery_task_id:
        celery_result = AsyncResult(task_record.celery_task_id, app=celery_app)
        celery_status = celery_result.status
        ready = celery_result.ready()

    data = TaskStatusRead.model_validate(task_record).model_dump()
    data["celery_status"] = celery_status
    data["ready"] = ready

    return data