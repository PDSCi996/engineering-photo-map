# 工程照片地图管理系统 / Engineering Photo Map

工程照片地图管理系统是一套面向工程现场、施工记录和巡检照片的 Docker 化照片管理与地图查看应用。它支持项目化管理、批量上传、后台媒体处理、地图定位查看、无坐标照片的人工补点、导出和基础运维检查。

Engineering Photo Map is a Docker-based photo management and map review application for field, construction, and inspection photos. It supports project-based organization, batch uploads, background media processing, map-based review, manual coordinate correction, exports, and basic operational diagnostics.

## 功能 / Features

- 项目化照片管理 / Project-based photo management
- 批量照片上传与后台处理 / Batch photo upload and background processing
- 缩略图与预览图生成 / Thumbnail and preview generation
- 基于坐标的地图查看 / Map display for geotagged photos
- 无 GPS 照片的人工坐标修正 / Manual coordinate correction for photos without GPS metadata
- CSV、GeoJSON 和 QGIS 资料包导出 / CSV, GeoJSON, and QGIS package exports
- FastAPI 后端、Celery Worker、Redis、PostgreSQL/PostGIS 与 Vue 前端 / FastAPI backend, Celery worker, Redis, PostgreSQL/PostGIS, and Vue frontend
- 支持源码构建部署与 GHCR 镜像部署 / Supports source-built deployment and GHCR image-based deployment

## 快速开始 / Quick Start

中文：

1. 复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

2. 修改 `.env` 中的 `POSTGRES_PASSWORD`，不要使用示例密码。
3. 启动本地源码构建服务：

```powershell
docker compose up --build
```

4. 打开前端页面，使用 `.env` 中配置的 `FRONTEND_PORT`。
5. 检查 API 健康状态，使用 `.env` 中配置的 `API_PORT`。

English:

1. Copy the environment template:

```powershell
Copy-Item .env.example .env
```

2. Change `POSTGRES_PASSWORD` in `.env`; do not use the sample value in production.
3. Start the local source-built stack:

```powershell
docker compose up --build
```

4. Open the frontend with the `FRONTEND_PORT` configured in `.env`.
5. Check the API health endpoint with the `API_PORT` configured in `.env`.

更多说明见 [快速开始](docs/快速开始.md)、[环境变量说明](docs/环境变量说明.md) 和 [群晖 Portainer 部署说明](docs/群晖Portainer部署说明.md)。

For details, see [Quick Start](docs/快速开始.md), [Environment Variables](docs/环境变量说明.md), and [Synology Portainer Deployment](docs/群晖Portainer部署说明.md).

## 部署方式 / Deployment Options

源码构建部署：

- 本地开发使用 `docker-compose.yml`。
- 群晖 Portainer 源码构建使用 `docker-compose.synology.yml`。
- Compose 会从 `frontend/Dockerfile`、`backend/Dockerfile` 和 `worker/Dockerfile` 构建镜像。

Source-built deployment:

- Use `docker-compose.yml` for local development.
- Use `docker-compose.synology.yml` for source-built Synology Portainer deployment.
- Compose builds images from `frontend/Dockerfile`, `backend/Dockerfile`, and `worker/Dockerfile`.

GHCR 镜像部署：

- 使用 `docker-compose.image.yml`。
- 该文件直接拉取 GHCR 镜像，不在部署机器上 build 源码。
- 群晖 Portainer 推荐使用 `docker-compose.image.yml` 部署公开 Release 镜像。

GHCR image deployment:

- Use `docker-compose.image.yml`.
- This file pulls GHCR images directly and does not build source code on the deployment host.
- For Synology Portainer, `docker-compose.image.yml` is recommended for public Release images.

## GHCR 镜像 / GHCR Images

默认公开 Release 镜像标签为 `v0.4.7-public-initial`：

```text
ghcr.io/pdsci996/engineering-photo-map-frontend:v0.4.7-public-initial
ghcr.io/pdsci996/engineering-photo-map-api:v0.4.7-public-initial
ghcr.io/pdsci996/engineering-photo-map-worker:v0.4.7-public-initial
```

The default public Release image tag is `v0.4.7-public-initial`.

## 群晖 Portainer 部署入口 / Synology Portainer Deployment Entry

中文：

- 推荐使用 `docker-compose.image.yml` 作为 Portainer Stack 的 Compose 文件。
- 以 `.env.synology.example` 为模板创建部署环境变量。
- 部署前必须替换示例域名、示例地址、示例端口、示例路径和示例密码。
- 镜像版 Portainer 长期部署可参考 `docker-compose.portainer-image.yml`；frontend 容器内部端口固定为 `5173`，API 容器内部端口固定为 `8000`。
- 真实部署信息、NAS 截图、日志和备份文件不要提交到公开仓库。

English:

- Use `docker-compose.image.yml` as the recommended Portainer Stack compose file.
- Create deployment environment variables from `.env.synology.example`.
- Replace all sample domains, addresses, ports, paths, and passwords before deployment.
- For long-running image-based Portainer stacks, see `docker-compose.portainer-image.yml`; the frontend container listens on `5173`, and the API container listens on `8000`.
- Do not commit real deployment details, NAS screenshots, logs, or backup files to the public repository.

## 隐私与安全提醒 / Privacy And Security Notice

中文：

本公开仓库不包含真实环境文件、真实照片、缩略图、预览图、数据库文件、日志、报告、备份或部署记录。请不要提交 `.env`、`data/`、`logs/`、`reports/`、备份压缩包、真实域名、真实 IP、真实端口、账号、密码或 token。

English:

This public repository does not include real environment files, photos, thumbnails, previews, database files, logs, reports, backups, or deployment records. Do not commit `.env`, `data/`, `logs/`, `reports/`, backup archives, real domains, real IP addresses, real ports, accounts, passwords, or tokens.

## 目录结构 / Repository Layout

```text
backend/                    FastAPI API service
worker/                     Celery media processing worker
frontend/                   Vue + Vite frontend
scripts/                    Local helper scripts
tests/                      Basic project tests
tools/                      Development check tools
docs/                       Public documentation
docker-compose.yml          Local development stack
docker-compose.synology.yml Synology Portainer source-build stack
docker-compose.image.yml    GHCR image-based deployment stack
.env.example                Local environment template
.env.production.example     Production environment template
.env.synology.example       Synology environment template
```

## 许可证 / License

MIT License. See [LICENSE](LICENSE).
