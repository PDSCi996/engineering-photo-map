# 群晖 Portainer 部署说明

> English summary: This document describes a generic Synology NAS and Portainer Stack deployment path. Domains, addresses, ports, passwords, and paths are placeholders and must be replaced privately. For Synology Portainer, the image-based compose file is recommended after GHCR images are published.

本文给出通用的 Synology NAS + Portainer Stack 部署方式。文中的域名、地址、端口、密码和路径都是示例或占位符，请按自己的环境在私有配置中修改，不要提交真实部署信息。

## 部署方式

源码构建部署：

- 使用 `docker-compose.synology.yml`。
- Portainer 会从仓库源码构建 `frontend`、`api` 和 `worker` 镜像。
- 适合需要本地改代码或验证 Dockerfile 的场景。

GHCR 镜像部署：

- 使用 `docker-compose.image.yml`。
- Portainer 直接拉取 `ghcr.io/pdsci996/engineering-photo-map-*` 镜像，不在 NAS 上 build 源码。
- 推荐用于群晖 Portainer 的公开发布版部署，速度更快，也更接近 Release 产物。

## 推荐文件

- `docker-compose.image.yml`
- `.env.synology.example`

如果需要源码构建，可改用 `docker-compose.synology.yml`。

部署前请以 `.env.synology.example` 为模板创建 `.env`，并修改密码、域名、访问地址、端口和数据目录。

## 数据目录

示例路径：

```text
/volume1/docker/engineering-photo-map/data
```

这只是群晖上常见的示例路径。你可以改成任何可持久化、空间充足、权限正确的目录。

## 示例环境变量

```text
POSTGRES_PASSWORD=change_this_password
FRONTEND_PORT=<FRONTEND_PORT>
API_PORT=<API_PORT>
HOST_DATA_DIR=/volume1/docker/engineering-photo-map/data
PUBLIC_HTTPS_PORT=<PUBLIC_HTTPS_PORT>
PUBLIC_BASE_URL=https://photos.example.com:${PUBLIC_HTTPS_PORT}
API_BASE_URL=https://api.photos.example.com:${PUBLIC_HTTPS_PORT}
VITE_API_BASE_URL=https://api.photos.example.com:${PUBLIC_HTTPS_PORT}
NAS_LAN_IP=<NAS_LAN_IP>
CORS_ORIGINS=https://photos.example.com:${PUBLIC_HTTPS_PORT},http://${NAS_LAN_IP}:${FRONTEND_PORT}
VITE_ALLOWED_HOSTS=photos.example.com,api.photos.example.com,${NAS_LAN_IP}
```

请将 `<PUBLIC_HTTPS_PORT>`、`<NAS_LAN_IP>`、`<API_PORT>` 和 `<FRONTEND_PORT>` 替换为你的私有部署值。不要把真实值提交到公开仓库。

## Portainer Stack

1. 在 Portainer 中新建 Stack。
2. 推荐粘贴 `docker-compose.image.yml` 的内容，或使用仓库文件方式选择该文件。
3. 在 Environment variables 区域填入 `.env` 中的变量。
4. 部署后检查 API 健康状态和前端页面。

如果 GHCR 镜像包设为私有，需要先在 Portainer 中配置可读取 GHCR 的 registry 凭据。公开镜像无需额外凭据。

## 反向代理

如果使用 HTTPS 反向代理，请确保：

- 前端域名指向前端服务端口。
- API 域名指向 API 服务端口。
- `CORS_ORIGINS` 包含前端公开访问地址。
- `VITE_ALLOWED_HOSTS` 包含访问前端时使用的 Host。

公开仓库中只保留示例域名和占位符，不记录真实反向代理规则。
