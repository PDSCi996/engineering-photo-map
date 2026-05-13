import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.celery_client import celery_app
from app.database import get_db
from app.models import Asset, Project, TaskRecord
from app.schemas import AssetRead


router = APIRouter(
    prefix="/api/projects/{project_id}/assets",
    tags=["assets"],
)

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
MEDIA_URL_PREFIX = os.getenv("MEDIA_URL_PREFIX", "/media").rstrip("/")

MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "999"))

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
    ".bmp",
    ".tif",
    ".tiff",
}


def make_media_url(relative_path: str | None) -> str | None:
    """
    将数据库中的相对路径转换为浏览器可访问的 URL。

    例如：
    thumbnails/1/a.jpg
    转成：
    /media/thumbnails/1/a.jpg
    """
    if not relative_path:
        return None

    return f"{MEDIA_URL_PREFIX}/{relative_path.lstrip('/')}"


def asset_to_read(asset: Asset) -> AssetRead:
    """
    将 Asset 数据库对象转换为前端返回结构。

    V0.2.6 在原始字段基础上额外增加：
    original_url / preview_url / thumb_url

    V0.3.1 继续返回：
    latitude / longitude / gps_source / gps_status
    """
    data = AssetRead.model_validate(asset).model_dump()

    data["original_url"] = make_media_url(asset.storage_path)
    data["preview_url"] = make_media_url(asset.preview_path)
    data["thumb_url"] = make_media_url(asset.thumb_path)

    # 兼容旧数据。正常启动迁移后 gps_status 不会为空，这里只是兜底。
    data["gps_status"] = data.get("gps_status") or "none"

    return AssetRead(**data)


def make_safe_filename(original_filename: str) -> str:
    """
    根据原始文件名生成一个安全、不容易重名的保存文件名。
    保留中文、英文、数字、横线、下划线和点号。
    """
    original_name = Path(original_filename or "uploaded_photo").name
    suffix = Path(original_name).suffix.lower()

    stem = Path(original_name).stem
    safe_stem = re.sub(r"[^0-9A-Za-z一-鿿._-]+", "_", stem)
    safe_stem = safe_stem.strip("._-")

    if not safe_stem:
        safe_stem = "photo"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    short_id = uuid4().hex[:8]

    return f"{timestamp}_{short_id}_{safe_stem}{suffix}"


def check_project_exists(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目不存在：{project_id}",
        )

    return project


def validate_upload_file(file: UploadFile) -> str:
    original_filename = file.filename or "uploaded_photo"
    suffix = Path(original_filename).suffix.lower()

    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型：{suffix}。当前仅支持常见图片文件。",
        )

    return original_filename


def save_uploaded_file(project_id: int, file: UploadFile) -> tuple[str, Path]:
    original_filename = validate_upload_file(file)
    saved_filename = make_safe_filename(original_filename)

    project_original_dir = DATA_DIR / "originals" / str(project_id)
    project_original_dir.mkdir(parents=True, exist_ok=True)

    storage_path = project_original_dir / saved_filename

    try:
        with storage_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存上传文件失败：{exc}",
        ) from exc
    finally:
        file.file.close()

    relative_storage_path = Path("originals") / str(project_id) / saved_filename

    return original_filename, relative_storage_path


def create_asset_and_task(
    *,
    project_id: int,
    original_filename: str,
    relative_storage_path: Path,
    db: Session,
) -> tuple[Asset, TaskRecord]:
    asset = Asset(
        project_id=project_id,
        filename=original_filename,
        storage_path=relative_storage_path.as_posix(),
        preview_path=None,
        thumb_path=None,
        shot_at=None,
        exif_json=None,
        has_gps=False,
        latitude=None,
        longitude=None,
        gps_source=None,
        gps_status="none",
    )

    db.add(asset)
    db.flush()

    task_record = TaskRecord(
        type="media.process_asset",
        status="pending",
        progress=0,
        celery_task_id=None,
        payload_json={
            "project_id": project_id,
            "asset_id": asset.id,
            "filename": original_filename,
            "storage_path": relative_storage_path.as_posix(),
        },
        result_json=None,
        error_message=None,
    )

    db.add(task_record)
    db.flush()

    return asset, task_record


def queue_media_process_task(asset: Asset, task_record: TaskRecord, db: Session) -> None:
    try:
        celery_task = celery_app.send_task(
            "media.process_asset",
            kwargs={
                "asset_id": asset.id,
                "task_record_id": task_record.id,
            },
        )
    except Exception as exc:
        task_record.status = "failed"
        task_record.progress = 100
        task_record.error_message = f"创建 Celery 后台任务失败：{exc}"
        task_record.finished_at = datetime.utcnow()
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建后台处理任务失败：{exc}",
        ) from exc

    task_record.celery_task_id = celery_task.id
    db.add(task_record)


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="上传照片到项目并创建后台处理任务，支持单张和多张",
)
def upload_asset(
    project_id: int,
    file: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    v0.4.3a：上传接口增强版。

    兼容两种情况：
    1. 前端只传 1 张照片；
    2. 前端一次传多张照片，字段名仍然叫 file。

    返回中保留 asset / task 字段，用于兼容旧前端；
    同时增加 assets / tasks / total / success_count，供后续批量上传前端使用。
    """
    check_project_exists(project_id, db)

    files = file or []

    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有收到任何上传文件。",
        )

    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"一次最多上传 {MAX_UPLOAD_FILES} 张照片，当前选择了 {len(files)} 张。",
        )

    created_assets: list[Asset] = []
    created_tasks: list[TaskRecord] = []

    for upload_file in files:
        original_filename, relative_storage_path = save_uploaded_file(
            project_id=project_id,
            file=upload_file,
        )

        asset, task_record = create_asset_and_task(
            project_id=project_id,
            original_filename=original_filename,
            relative_storage_path=relative_storage_path,
            db=db,
        )

        created_assets.append(asset)
        created_tasks.append(task_record)

    db.commit()

    for asset in created_assets:
        db.refresh(asset)

    for task_record in created_tasks:
        db.refresh(task_record)

    for asset, task_record in zip(created_assets, created_tasks):
        queue_media_process_task(asset, task_record, db)

    db.commit()

    for task_record in created_tasks:
        db.refresh(task_record)

    first_asset = created_assets[0]
    first_task = created_tasks[0]

    return {
        "status": "queued",
        "message": f"已上传 {len(created_assets)} 张照片，后台处理任务已创建。",
        "total": len(files),
        "success_count": len(created_assets),
        "failed_count": 0,

        # 兼容旧前端：旧代码如果读取 data.asset / data.task，仍然能拿到第一张。
        "asset": asset_to_read(first_asset),
        "task": first_task,

        # 批量上传增强字段。
        "assets": [asset_to_read(asset) for asset in created_assets],
        "tasks": created_tasks,
    }


@router.get(
    "",
    response_model=list[AssetRead],
    summary="获取项目照片列表",
)
def list_assets(
    project_id: int,
    db: Session = Depends(get_db),
):
    check_project_exists(project_id, db)

    statement = (
        select(Asset)
        .where(Asset.project_id == project_id)
        .order_by(Asset.created_at.desc())
    )

    assets = db.scalars(statement).all()

    return [asset_to_read(asset) for asset in assets]