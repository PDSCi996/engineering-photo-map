# Engineering Photo Map

Engineering Photo Map is a Docker-based photo management and mapping application for field or construction photos. It supports photo upload, background media processing, map-based review, manual point correction, exports, and operational diagnostics.

## Features

- Project-based photo management
- Batch photo upload and background processing
- Preview and thumbnail generation
- Map display for photos with coordinates
- Manual coordinate correction for photos without GPS metadata
- CSV, GeoJSON, and QGIS package export
- FastAPI backend, Celery worker, Redis, PostgreSQL/PostGIS, and Vue frontend
- Docker Compose setup for local development and Synology Portainer deployment

## Privacy Notice

This public repository does not include real environment files, photos, thumbnails, previews, database files, logs, reports, backups, or deployment records. Do not commit `.env`, `data/`, `logs/`, `reports/`, or backup archives.

## Quick Start

1. Copy `.env.example` to `.env`.
2. Change `POSTGRES_PASSWORD` in `.env`.
3. Start the stack:

```powershell
docker compose up --build
```

4. Open the frontend:

```text
http://localhost:5173
```

5. Check the API health endpoint:

```text
http://localhost:8000/api/health
```

For details, see `docs/快速开始.md`, `docs/环境变量说明.md`, and `docs/群晖Portainer部署说明.md`.

## Repository Layout

```text
backend/                  FastAPI API service
worker/                   Celery media processing worker
frontend/                 Vue + Vite frontend
scripts/                  Local helper scripts
tests/                    Basic project tests
tools/                    Development check tools
docs/                     Public documentation
docker-compose.yml        Local development stack
docker-compose.synology.yml Synology Portainer-oriented stack
.env.example              Local environment template
.env.production.example   Production environment template
.env.synology.example     Synology environment template
```

## License

MIT License. See `LICENSE`.