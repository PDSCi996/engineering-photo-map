from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


def payload_int(payload: dict[str, Any] | None, key: str) -> int | None:
    if not payload:
        return None

    value = payload.get(key)

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def payload_str(payload: dict[str, Any] | None, key: str) -> str | None:
    if not payload:
        return None

    value = payload.get(key)

    if value is None:
        return None

    return str(value)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    code: str | None = Field(default=None, max_length=100, description="项目编号")
    description: str | None = Field(default=None, description="项目说明")


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    storage_path: str
    preview_path: str | None = None
    thumb_path: str | None = None

    # V0.2.6：前端可直接使用的图片访问地址
    original_url: str | None = None
    preview_url: str | None = None
    thumb_url: str | None = None

    shot_at: datetime | None = None
    exif_json: dict[str, Any] | None = None
    has_gps: bool

    # V0.3.1：正式地图点位字段
    latitude: float | None = None
    longitude: float | None = None
    gps_source: str | None = None
    gps_status: str = "none"

    created_at: datetime
    updated_at: datetime


class MapAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str

    latitude: float
    longitude: float
    gps_source: str | None = None
    gps_status: str = "valid"

    shot_at: datetime | None = None

    storage_path: str
    preview_path: str | None = None
    thumb_path: str | None = None

    original_url: str | None = None
    preview_url: str | None = None
    thumb_url: str | None = None

    has_gps: bool
    created_at: datetime
    updated_at: datetime


class AssetGpsUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")
    gps_source: str = Field(default="manual", max_length=50, description="GPS 来源")
    gps_status: str = Field(default="valid", max_length=50, description="GPS 状态")


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    status: str
    progress: int
    celery_task_id: str | None = None
    payload_json: dict[str, Any] | None = None
    result_json: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None

    # V0.2.8.1：从 payload_json 派生出来的前端常用字段
    @computed_field
    @property
    def project_id(self) -> int | None:
        return payload_int(self.payload_json, "project_id")

    @computed_field
    @property
    def asset_id(self) -> int | None:
        return payload_int(self.payload_json, "asset_id")

    @computed_field
    @property
    def task_filename(self) -> str | None:
        return payload_str(self.payload_json, "filename")


class TaskStatusRead(TaskRead):
    celery_status: str | None = None
    ready: bool | None = None


class TaskSummaryRead(BaseModel):
    project_id: int | None = None
    asset_id: int | None = None
    total: int
    pending: int
    processing: int
    done: int
    failed: int
    by_status: dict[str, int]


class AssetUploadResponse(BaseModel):
    status: str
    message: str
    asset: AssetRead
    task: TaskRead
