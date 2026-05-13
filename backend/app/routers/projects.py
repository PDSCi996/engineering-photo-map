import csv
import io
import json
import os
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, List
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, Project
from app.schemas import AssetGpsUpdate, MapAssetRead, ProjectCreate, ProjectRead


router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
)

MEDIA_URL_PREFIX = os.getenv("MEDIA_URL_PREFIX", "/media").rstrip("/")

EXPORT_FIELDNAMES = [
    "point_no",
    "label",
    "asset_id",
    "project_id",
    "project_name",
    "project_code",
    "filename",
    "shot_at",
    "longitude",
    "latitude",
    "gps_source",
    "gps_status",
    "has_gps",
    "storage_path",
    "original_url",
    "preview_path",
    "preview_url",
    "thumb_path",
    "thumb_url",
    "created_at",
    "updated_at",
    "exported_at",
    "remark",
]


def _safe_export_name(value: str | None, fallback: str = "project") -> str:
    """生成适合下载文件名使用的项目名称片段。"""
    text = (value or "").strip() or fallback
    text = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip("._ ") or fallback
    return text[:60]


def _export_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _export_filename(project: Project, suffix: str) -> str:
    project_name = _safe_export_name(project.name, f"project_{project.id}")
    return f"{project_name}_点位导出_{_export_timestamp()}.{suffix}"


def _export_filename_with_label(
    project: Project,
    label: str,
    suffix: str,
    timestamp: str | None = None,
) -> str:
    project_name = _safe_export_name(project.name, f"project_{project.id}")
    export_time = timestamp or _export_timestamp()
    return f"{project_name}_{label}_{export_time}.{suffix}"


def _content_disposition(filename: str) -> str:
    """同时提供英文兜底文件名和 UTF-8 文件名，避免中文下载名乱码。"""
    fallback = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
    if not fallback or fallback.startswith("_"):
        fallback = "photo_points_export" + Path(filename).suffix
    encoded = quote(filename)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


def _ensure_exportable_assets(project: Project, assets: list[Asset]) -> None:
    if assets:
        return

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            f"项目“{project.name}”当前没有可导出的 GPS 点位。"
            "请先上传带 GPS 的照片，或在“无GPS”标签中补点后再导出。"
        ),
    )


def _qgis_qml_style() -> str:
    """生成 QGIS 图层样式：蓝色圆点 + point_no 编号标注。"""
    return """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34" styleCategories="Symbology|Labeling|Fields|Forms">
  <renderer-v2 type="singleSymbol" symbollevels="0" enableorderby="0" forceraster="0">
    <symbols>
      <symbol type="marker" name="0" alpha="1" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleMarker" enabled="1" pass="0" locked="0">
          <Option type="Map">
            <Option name="name" type="QString" value="circle"/>
            <Option name="color" type="QString" value="37,99,235,255"/>
            <Option name="outline_color" type="QString" value="255,255,255,255"/>
            <Option name="outline_width" type="QString" value="0.55"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="size" type="QString" value="4.2"/>
            <Option name="size_unit" type="QString" value="MM"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fieldName="point_no" isExpression="0" fontFamily="Microsoft YaHei" fontSize="9" fontSizeUnit="Point" fontWeight="75" namedStyle="Bold" textColor="255,255,255,255"/>
      <text-format multilineHeight="1" wrapChar="" formatNumbers="0" decimals="0"/>
      <placement placement="0" dist="0" distUnits="MM" offsetType="0" xOffset="0" yOffset="0"/>
      <rendering drawLabels="1" scaleMin="0" scaleMax="0" scaleVisibility="0"/>
      <buffer bufferDraw="0" bufferNoFill="1" bufferSize="0.8" bufferSizeUnits="MM" bufferColor="255,255,255,255"/>
      <background shapeDraw="0"/>
      <shadow shadowDraw="0"/>
    </settings>
  </labeling>
  <customproperties>
    <Option type="Map">
      <Option name="labeling" type="QString" value="pal"/>
      <Option name="labeling/enabled" type="QString" value="true"/>
      <Option name="labeling/fieldName" type="QString" value="point_no"/>
      <Option name="labeling/isExpression" type="QString" value="false"/>
      <Option name="labeling/fontFamily" type="QString" value="Microsoft YaHei"/>
      <Option name="labeling/fontSize" type="QString" value="9"/>
      <Option name="labeling/textColorR" type="QString" value="255"/>
      <Option name="labeling/textColorG" type="QString" value="255"/>
      <Option name="labeling/textColorB" type="QString" value="255"/>
      <Option name="labeling/placement" type="QString" value="0"/>
    </Option>
  </customproperties>
</qgis>
"""


def _qgis_readme_text(project: Project, point_count: int, exported_at: str) -> str:
    """生成 QGIS 导出使用说明，便于和 GeoJSON / CSV / QML 一起留档。"""
    project_name = project.name or f"project_{project.id}"
    return f"""工程照片地图管理系统｜QGIS 点位导出使用说明

一、项目与导出信息
- 项目名称：{project_name}
- 项目编号：{project.code or ""}
- 项目 ID：{project.id}
- 可导出 GPS 点位数量：{point_count}
- 说明生成时间：{exported_at}

二、建议导出的文件
1. GeoJSON / QGIS 图层：项目名称_点位导出_日期时间.geojson
   - 推荐直接拖入 QGIS。
   - 坐标为 WGS84 经纬度，GeoJSON 坐标顺序为 longitude, latitude。

2. CSV 点位表：项目名称_点位导出_日期时间.csv
   - 可用 Excel 打开。
   - 在 QGIS 中作为分隔文本图层加载时，经度字段选 longitude，纬度字段选 latitude。

3. QGIS 样式文件：项目名称_QGIS样式_日期时间.qml
   - 先导入 GeoJSON 图层，再给该图层加载 QML 样式。
   - 用途：统一点位样式，并按 point_no 字段尝试显示编号。

三、QGIS 推荐操作步骤
1. 打开 QGIS。
2. 先加载 OpenStreetMap 或其他底图。
3. 将 .geojson 文件拖入 QGIS。
4. 在左侧图层列表中右键点位图层。
5. 选择“属性” → “符号化”或“样式” → “加载样式”。
6. 选择同一批次导出的 .qml 文件。
7. 如编号不明显，可进入“标注”，字段选择 point_no，字号调大并加白色描边。
8. 保存 QGIS 工程文件 .qgz，作为本项目的制图工程。

四、主要字段说明
- point_no：导出点位序号，建议用于地图编号标注。
- label：点位标签，格式通常为“序号 + 文件名”。
- asset_id：系统内部照片 ID。
- project_id：系统内部项目 ID。
- project_name：项目名称。
- project_code：项目编号。
- filename：照片文件名。
- shot_at：照片拍摄时间。
- longitude：经度。
- latitude：纬度。
- gps_source：GPS 来源，常见值为 exif / manual / edited。
- gps_status：GPS 状态，常见值为 valid / edited / none。
- original_url：原图访问地址。
- preview_url：预览图访问地址。
- thumb_url：缩略图访问地址。

五、当前阶段说明
- V0.3 阶段重点是“照片上地图”和“点位导出”。
- QML 样式属于辅助文件，后续闭环前还会继续优化标注清晰度。
- 后续可扩展导出 QGIS 工程模板、打印布局、PDF 出图等能力。
"""


def make_media_url(relative_path: str | None) -> str | None:
    if not relative_path:
        return None

    return f"{MEDIA_URL_PREFIX}/{relative_path.lstrip('/')}"


def check_project_exists(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目不存在：{project_id}",
        )

    return project


def _safe_datetime(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _valid_asset_coordinate(asset: Asset) -> tuple[float, float] | None:
    latitude = _safe_float(getattr(asset, "latitude", None))
    longitude = _safe_float(getattr(asset, "longitude", None))

    if latitude is None or longitude is None:
        return None

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None

    return latitude, longitude


def _asset_export_row(
    project: Project,
    asset: Asset,
    point_no: int,
    exported_at: str,
) -> dict[str, Any]:
    coordinate = _valid_asset_coordinate(asset)
    latitude, longitude = coordinate if coordinate else (None, None)
    label = f"{point_no:03d} {asset.filename}"

    return {
        "point_no": point_no,
        "label": label,
        "asset_id": asset.id,
        "project_id": project.id,
        "project_name": project.name,
        "project_code": project.code or "",
        "filename": asset.filename,
        "shot_at": _safe_datetime(asset.shot_at),
        "longitude": longitude if longitude is not None else "",
        "latitude": latitude if latitude is not None else "",
        "gps_source": getattr(asset, "gps_source", None) or "",
        "gps_status": getattr(asset, "gps_status", None) or "",
        "has_gps": bool(asset.has_gps),
        "storage_path": asset.storage_path,
        "original_url": make_media_url(asset.storage_path) or "",
        "preview_path": asset.preview_path or "",
        "preview_url": make_media_url(asset.preview_path) or "",
        "thumb_path": asset.thumb_path or "",
        "thumb_url": make_media_url(asset.thumb_path) or "",
        "created_at": _safe_datetime(asset.created_at),
        "updated_at": _safe_datetime(asset.updated_at),
        "exported_at": exported_at,
        "remark": "",
    }


def _project_point_assets(project_id: int, db: Session) -> list[Asset]:
    statement = (
        select(Asset)
        .where(Asset.project_id == project_id)
        .where(Asset.latitude.is_not(None))
        .where(Asset.longitude.is_not(None))
        .order_by(Asset.created_at.desc())
    )

    return [asset for asset in db.scalars(statement).all() if _valid_asset_coordinate(asset)]


def asset_to_map_asset(asset: Asset) -> MapAssetRead:
    return MapAssetRead(
        id=asset.id,
        project_id=asset.project_id,
        filename=asset.filename,
        latitude=asset.latitude,
        longitude=asset.longitude,
        gps_source=asset.gps_source,
        gps_status=asset.gps_status or "valid",
        shot_at=asset.shot_at,
        storage_path=asset.storage_path,
        preview_path=asset.preview_path,
        thumb_path=asset.thumb_path,
        original_url=make_media_url(asset.storage_path),
        preview_url=make_media_url(asset.preview_path),
        thumb_url=make_media_url(asset.thumb_path),
        has_gps=asset.has_gps,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建项目",
)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
):
    project = Project(
        name=project_in.name.strip(),
        code=project_in.code.strip() if project_in.code else None,
        description=project_in.description.strip() if project_in.description else None,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get(
    "",
    response_model=List[ProjectRead],
    summary="获取项目列表",
)
def list_projects(
    db: Session = Depends(get_db),
):
    statement = select(Project).order_by(Project.created_at.desc())
    projects = db.scalars(statement).all()

    return projects


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="获取项目详情",
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = check_project_exists(project_id, db)
    return project


@router.get(
    "/{project_id}/map-assets",
    response_model=List[MapAssetRead],
    summary="获取当前项目有 GPS 经纬度的照片点位",
)
def list_project_map_assets(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    V0.3.1：地图数据 API。

    返回当前项目中已经具备 latitude / longitude 的照片。
    """
    check_project_exists(project_id, db)
    assets = _project_point_assets(project_id, db)

    return [asset_to_map_asset(asset) for asset in assets]


@router.get(
    "/{project_id}/exports/points.csv",
    summary="导出当前项目照片点位 CSV",
)
def export_project_points_csv(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    V0.3.13：QGIS / Excel CSV 点位导出。

    CSV 使用 UTF-8 BOM，方便 Excel 直接打开中文不乱码；
    QGIS 导入时经度字段选 longitude，纬度字段选 latitude。
    """
    project = check_project_exists(project_id, db)
    assets = _project_point_assets(project_id, db)
    _ensure_exportable_assets(project, assets)

    exported_at = datetime.now().isoformat(timespec="seconds")
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDNAMES, extrasaction="ignore")
    writer.writeheader()

    for point_no, asset in enumerate(assets, start=1):
        writer.writerow(_asset_export_row(project, asset, point_no, exported_at))

    filename = _export_filename(project, "csv")

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get(
    "/{project_id}/exports/points.geojson",
    summary="导出当前项目照片点位 GeoJSON",
)
def export_project_points_geojson(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    V0.3.13：QGIS GeoJSON 点位导出。

    坐标顺序按 GeoJSON 标准写入：[longitude, latitude]。
    """
    project = check_project_exists(project_id, db)
    assets = _project_point_assets(project_id, db)
    _ensure_exportable_assets(project, assets)

    exported_at = datetime.now().isoformat(timespec="seconds")
    features = []
    for point_no, asset in enumerate(assets, start=1):
        coordinate = _valid_asset_coordinate(asset)
        if coordinate is None:
            continue

        latitude, longitude = coordinate
        row = _asset_export_row(project, asset, point_no, exported_at)

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
                "properties": row,
            }
        )

    payload = {
        "type": "FeatureCollection",
        "name": _safe_export_name(project.name, f"project_{project_id}") + "_photo_points",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    filename = _export_filename(project, "geojson")

    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/geo+json; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get(
    "/{project_id}/exports/points.qml",
    summary="导出当前项目 QGIS 点位样式 QML",
)
def export_project_points_qml(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    V0.3.15：QGIS 样式导出。

    用法：先把 GeoJSON 图层导入 QGIS，再在图层属性里加载这个 QML，
    即可用蓝色圆点显示点位，并按 point_no 字段标注编号。
    """
    project = check_project_exists(project_id, db)
    filename = _export_filename(project, "qml").replace("点位导出", "QGIS样式")

    return Response(
        content=_qgis_qml_style(),
        media_type="application/xml; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get(
    "/{project_id}/exports/qgis-readme.txt",
    summary="导出当前项目 QGIS 使用说明 TXT",
)
def export_project_qgis_readme(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    V0.3.16：QGIS 导出说明文件。

    用于和 CSV / GeoJSON / QML 放在同一目录，方便后期复查字段含义和 QGIS 加载步骤。
    """
    project = check_project_exists(project_id, db)
    assets = _project_point_assets(project_id, db)
    exported_at = datetime.now().isoformat(timespec="seconds")
    filename = _export_filename(project, "txt").replace("点位导出", "QGIS使用说明")

    return Response(
        content="\ufeff" + _qgis_readme_text(project, len(assets), exported_at),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(filename)},
    )



@router.get(
    "/{project_id}/exports/qgis-package.zip",
    summary="一键导出当前项目 QGIS 资料包 ZIP",
)
def export_project_qgis_package(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    V0.3.17：QGIS 资料包导出。

    一个 ZIP 内同时包含 CSV、GeoJSON、QML 和 TXT 说明，方便整包留档或发送给同事。
    """
    project = check_project_exists(project_id, db)
    assets = _project_point_assets(project_id, db)
    _ensure_exportable_assets(project, assets)

    timestamp = _export_timestamp()
    exported_at = datetime.now().isoformat(timespec="seconds")

    csv_filename = _export_filename_with_label(project, "点位导出", "csv", timestamp)
    geojson_filename = _export_filename_with_label(project, "点位导出", "geojson", timestamp)
    qml_filename = _export_filename_with_label(project, "QGIS样式", "qml", timestamp)
    readme_filename = _export_filename_with_label(project, "QGIS使用说明", "txt", timestamp)
    package_filename = _export_filename_with_label(project, "QGIS资料包", "zip", timestamp)

    csv_buffer = io.StringIO()
    csv_buffer.write("\ufeff")
    writer = csv.DictWriter(csv_buffer, fieldnames=EXPORT_FIELDNAMES, extrasaction="ignore")
    writer.writeheader()

    features = []
    for point_no, asset in enumerate(assets, start=1):
        coordinate = _valid_asset_coordinate(asset)
        if coordinate is None:
            continue

        latitude, longitude = coordinate
        row = _asset_export_row(project, asset, point_no, exported_at)
        writer.writerow(row)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "properties": row,
            }
        )

    geojson_payload = {
        "type": "FeatureCollection",
        "name": _safe_export_name(project.name, f"project_{project_id}") + "_photo_points",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    geojson_text = json.dumps(geojson_payload, ensure_ascii=False, indent=2)
    readme_text = "\ufeff" + _qgis_readme_text(project, len(assets), exported_at)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr(csv_filename, csv_buffer.getvalue().encode("utf-8"))
        package.writestr(geojson_filename, geojson_text.encode("utf-8"))
        package.writestr(qml_filename, _qgis_qml_style().encode("utf-8"))
        package.writestr(readme_filename, readme_text.encode("utf-8"))

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": _content_disposition(package_filename)},
    )

@router.patch(
    "/{project_id}/assets/{asset_id}/gps",
    response_model=MapAssetRead,
    summary="给照片手工补充或修正 GPS 点位",
)
def update_asset_gps(
    project_id: int,
    asset_id: int,
    gps_in: AssetGpsUpdate,
    db: Session = Depends(get_db),
):
    """
    V0.3.4 / V0.3.5：无 GPS 补点与已有 GPS 修改保存接口。

    设计原则：
    - 只写数据库，不直接改原图 EXIF；
    - 保存后 has_gps=True；
    - exif_json 中追加 manual_gps_history 记录，方便以后追踪手工补点或修改来源。
    """
    check_project_exists(project_id, db)

    asset = db.get(Asset, asset_id)

    if asset is None or asset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"照片不存在或不属于当前项目：asset_id={asset_id}",
        )

    asset.latitude = round(float(gps_in.latitude), 8)
    asset.longitude = round(float(gps_in.longitude), 8)
    asset.has_gps = True
    asset.gps_source = (gps_in.gps_source or "manual").strip() or "manual"
    asset.gps_status = (gps_in.gps_status or "valid").strip() or "valid"
    asset.updated_at = datetime.utcnow()

    exif_json = dict(asset.exif_json or {})
    manual_history = list(exif_json.get("manual_gps_history") or [])
    manual_record = {
        "latitude": asset.latitude,
        "longitude": asset.longitude,
        "gps_source": asset.gps_source,
        "gps_status": asset.gps_status,
        "saved_at": asset.updated_at.isoformat(timespec="seconds"),
    }
    manual_history.append(manual_record)
    exif_json["manual_gps"] = manual_record
    exif_json["manual_gps_history"] = manual_history[-20:]
    asset.exif_json = exif_json

    db.commit()
    db.refresh(asset)

    return asset_to_map_asset(asset)
