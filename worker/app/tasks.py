import os
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any

import exifread
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import text

from app.celery_app import celery_app
from app.database import SessionLocal, engine
from app.models import Asset, TaskRecord


DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))

PREVIEW_MAX_SIZE = (1600, 1600)
THUMBNAIL_MAX_SIZE = (360, 360)

_SCHEMA_READY = False


@celery_app.task(name="demo.ping")
def demo_ping(message: str):
    sleep(2)

    return {
        "message": message,
        "worker": "worker-media",
        "status": "done",
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


def _ensure_asset_gps_columns() -> None:
    """
    V0.3.1：worker 侧兜底检查 GPS 字段。

    正常情况下 API 启动时已经完成字段迁移。
    这里保留兜底，是为了避免 worker 比 API 更早处理任务时因为缺字段报错。
    """
    global _SCHEMA_READY

    if _SCHEMA_READY:
        return

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

    _SCHEMA_READY = True


def _ratio_to_float(value: Any) -> float:
    if hasattr(value, "num") and hasattr(value, "den"):
        return float(value.num) / float(value.den)
    return float(value)


def _gps_to_decimal(gps_value: Any, ref_value: Any) -> float | None:
    try:
        values = gps_value.values
        degrees = _ratio_to_float(values[0])
        minutes = _ratio_to_float(values[1])
        seconds = _ratio_to_float(values[2])

        decimal = degrees + minutes / 60 + seconds / 3600

        ref_text = str(ref_value).strip().upper()
        if ref_text in {"S", "W"}:
            decimal = -decimal

        return round(decimal, 8)
    except Exception:
        return None


def _parse_shot_at(tags: dict[str, Any]) -> datetime | None:
    for key in ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"):
        value = tags.get(key)
        if not value:
            continue

        text = str(value).strip()

        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

    return None


def _read_exif(
    original_path: Path,
) -> tuple[dict[str, Any] | None, datetime | None, bool, float | None, float | None]:
    try:
        with original_path.open("rb") as image_file:
            tags = exifread.process_file(image_file, details=False)
    except Exception:
        return None, None, False, None, None

    if not tags:
        return None, None, False, None, None

    make = str(tags.get("Image Make", "")).strip() or None
    model = str(tags.get("Image Model", "")).strip() or None

    shot_at = _parse_shot_at(tags)

    latitude = None
    longitude = None

    gps_latitude = tags.get("GPS GPSLatitude")
    gps_latitude_ref = tags.get("GPS GPSLatitudeRef")
    gps_longitude = tags.get("GPS GPSLongitude")
    gps_longitude_ref = tags.get("GPS GPSLongitudeRef")

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        latitude = _gps_to_decimal(gps_latitude, gps_latitude_ref)
        longitude = _gps_to_decimal(gps_longitude, gps_longitude_ref)

    has_gps = latitude is not None and longitude is not None

    selected_raw_tags = {}

    for key in (
        "Image Make",
        "Image Model",
        "EXIF DateTimeOriginal",
        "EXIF DateTimeDigitized",
        "Image DateTime",
        "GPS GPSLatitude",
        "GPS GPSLatitudeRef",
        "GPS GPSLongitude",
        "GPS GPSLongitudeRef",
        "GPS GPSAltitude",
    ):
        if key in tags:
            selected_raw_tags[key] = str(tags[key])

    exif_json = {
        "camera": {
            "make": make,
            "model": model,
        },
        "time": {
            "shot_at": shot_at.isoformat(timespec="seconds") if shot_at else None,
        },
        "gps": {
            "latitude": latitude,
            "longitude": longitude,
            "latitude_ref": str(gps_latitude_ref).strip() if gps_latitude_ref else None,
            "longitude_ref": str(gps_longitude_ref).strip() if gps_longitude_ref else None,
        },
        "raw": selected_raw_tags,
    }

    return exif_json, shot_at, has_gps, latitude, longitude


def _to_rgb_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", rgba_image.size, (255, 255, 255))
        background.paste(rgba_image, mask=rgba_image.split()[-1])
        return background

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


def _save_resized_jpeg(source_image: Image.Image, output_path: Path, max_size: tuple[int, int]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = source_image.copy()
    image.thumbnail(max_size)

    image.save(
        output_path,
        format="JPEG",
        quality=88,
        optimize=True,
    )


def _mark_task(
    db,
    task_record: TaskRecord | None,
    status: str,
    progress: int,
    result_json: dict[str, Any] | None = None,
    error_message: str | None = None,
    finished: bool = False,
) -> None:
    if not task_record:
        return

    task_record.status = status
    task_record.progress = progress
    task_record.result_json = result_json
    task_record.error_message = error_message

    if finished:
        task_record.finished_at = datetime.utcnow()

    db.commit()


@celery_app.task(name="media.process_asset")
def process_asset(asset_id: int, task_record_id: int | None = None):
    _ensure_asset_gps_columns()

    db = SessionLocal()
    task_record = None

    try:
        asset = db.get(Asset, asset_id)

        if asset is None:
            raise FileNotFoundError(f"资产记录不存在：asset_id={asset_id}")

        if task_record_id is not None:
            task_record = db.get(TaskRecord, task_record_id)

        _mark_task(
            db=db,
            task_record=task_record,
            status="processing",
            progress=10,
        )

        original_path = DATA_DIR / asset.storage_path

        if not original_path.exists():
            raise FileNotFoundError(f"原图文件不存在：{original_path}")

        relative_preview_path = Path("previews") / str(asset.project_id) / f"{Path(asset.storage_path).stem}.jpg"
        relative_thumb_path = Path("thumbnails") / str(asset.project_id) / f"{Path(asset.storage_path).stem}.jpg"

        preview_path = DATA_DIR / relative_preview_path
        thumb_path = DATA_DIR / relative_thumb_path

        exif_json, shot_at, has_gps, latitude, longitude = _read_exif(original_path)

        _mark_task(
            db=db,
            task_record=task_record,
            status="processing",
            progress=35,
        )

        try:
            with Image.open(original_path) as image:
                source_image = _to_rgb_image(image)

                _save_resized_jpeg(
                    source_image=source_image,
                    output_path=preview_path,
                    max_size=PREVIEW_MAX_SIZE,
                )

                _save_resized_jpeg(
                    source_image=source_image,
                    output_path=thumb_path,
                    max_size=THUMBNAIL_MAX_SIZE,
                )
        except UnidentifiedImageError as exc:
            raise ValueError(f"Pillow 无法识别该图片格式：{original_path.name}") from exc

        asset.preview_path = relative_preview_path.as_posix()
        asset.thumb_path = relative_thumb_path.as_posix()
        asset.shot_at = shot_at
        asset.exif_json = exif_json
        asset.has_gps = has_gps

        # V0.3.1：把 EXIF GPS 正式同步写入地图字段
        asset.latitude = latitude
        asset.longitude = longitude
        asset.gps_source = "exif" if has_gps else None
        asset.gps_status = "valid" if has_gps else "none"

        asset.updated_at = datetime.utcnow()

        result_json = {
            "asset_id": asset.id,
            "project_id": asset.project_id,
            "preview_path": asset.preview_path,
            "thumb_path": asset.thumb_path,
            "shot_at": asset.shot_at.isoformat(timespec="seconds") if asset.shot_at else None,
            "has_gps": asset.has_gps,
            "latitude": asset.latitude,
            "longitude": asset.longitude,
            "gps_source": asset.gps_source,
            "gps_status": asset.gps_status,
        }

        if task_record:
            task_record.status = "done"
            task_record.progress = 100
            task_record.result_json = result_json
            task_record.error_message = None
            task_record.finished_at = datetime.utcnow()

        db.commit()

        return result_json

    except Exception as exc:
        db.rollback()

        if task_record_id is not None:
            failed_task = db.get(TaskRecord, task_record_id)
            if failed_task:
                failed_task.status = "failed"
                failed_task.progress = 100
                failed_task.error_message = str(exc)
                failed_task.finished_at = datetime.utcnow()
                db.commit()

        raise

    finally:
        db.close()
