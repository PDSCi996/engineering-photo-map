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
- 支持本地 Docker Compose 与群晖 Portainer 部署入口 / Docker Compose setup for local development and Synology Portainer deployment entry

## 快速开始 / Quick Start

中文：

1. 复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

2. 修改 `.env` 中的 `POSTGRES_PASSWORD`，不要使用示例密码。
3. 启动服务：

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
3. Start the stack:

```powershell
docker compose up --build
```

4. Open the frontend with the `FRONTEND_PORT` configured in `.env`.
5. Check the API health endpoint with the `API_PORT` configured in `.env`.

更多说明见 [快速开始](docs/快速开始.md)、[环境变量说明](docs/环境变量说明.md) 和 [群晖 Portainer 部署说明](docs/群晖Portainer部署说明.md)。

For details, see [Quick Start](docs/快速开始.md), [Environment Variables](docs/环境变量说明.md), and [Synology Portainer Deployment](docs/群晖Portainer部署说明.md).

## 群晖 Portainer 部署入口 / Synology Portainer Deployment Entry

中文：

- 使用 `docker-compose.synology.yml` 作为 Portainer Stack 的 Compose 文件。
- 以 `.env.synology.example` 为模板创建部署环境变量。
- 部署前必须替换示例域名、示例地址、示例端口、示例路径和示例密码。
- 真实部署信息、NAS 截图、日志和备份文件不要提交到公开仓库。

English:

- Use `docker-compose.synology.yml` as the Portainer Stack compose file.
- Create deployment environment variables from `.env.synology.example`.
- Replace all sample domains, addresses, ports, paths, and passwords before deployment.
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
docker-compose.synology.yml Synology Portainer-oriented stack
.env.example                Local environment template
.env.production.example     Production environment template
.env.synology.example       Synology environment template
```

## 许可证 / License

MIT License. See [LICENSE](LICENSE).
