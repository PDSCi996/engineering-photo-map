# 群晖 Portainer 部署说明

本文给出通用的 Synology NAS + Portainer Stack 部署方式。文中的域名、IP、端口和路径都是示例，请按自己的环境修改。

## 推荐文件

- `docker-compose.synology.yml`
- `.env.synology.example`

部署前请复制 `.env.synology.example` 为 `.env`，并修改密码、域名、局域网 IP、端口和数据目录。

## 数据目录

示例路径：

```text
/volume1/docker/photo-map-v2/data
```

这只是群晖上的常见示例路径。你可以改成任何可持久化、空间充足、权限正确的目录。

## 示例环境变量

```text
POSTGRES_PASSWORD=change_this_password
HOST_DATA_DIR=/volume1/docker/photo-map-v2/data
PUBLIC_BASE_URL=https://photos.example.com:8443
API_BASE_URL=https://api.photos.example.com:8443
VITE_API_BASE_URL=https://api.photos.example.com:8443
CORS_ORIGINS=https://photos.example.com:8443,http://192.168.1.100:25173
VITE_ALLOWED_HOSTS=photos.example.com,api.photos.example.com,192.168.1.100
```

## Portainer Stack

1. 在 Portainer 中新建 Stack。
2. 粘贴 `docker-compose.synology.yml` 的内容，或使用仓库文件方式部署。
3. 在 Environment variables 区域填入 `.env` 中的变量。
4. 部署后检查 API 健康状态和前端页面。

## 反向代理

如果使用 HTTPS 反向代理，请确保：

- 前端域名指向前端服务端口。
- API 域名指向 API 服务端口。
- `CORS_ORIGINS` 包含前端公网地址。
- `VITE_ALLOWED_HOSTS` 包含访问前端时使用的 Host。