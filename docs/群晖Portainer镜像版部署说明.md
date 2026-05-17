# 群晖 Portainer 镜像版部署说明

> English summary: This guide explains how to deploy Engineering Photo Map on Synology Portainer by pulling GHCR images, with separate long-term production and test stacks.

本文说明如何在群晖 Portainer 中使用 `docker-compose.portainer-image.yml` 部署镜像拉取版，并长期维护两个堆栈：

- 正式堆栈：`photo-map-prod`
- 测试堆栈：`photo-map-test`

## 镜像版和 Git 仓库部署的区别

Git 仓库部署通常会让 Portainer 从仓库源码执行 `build`，在 NAS 上构建 `frontend`、`api` 和 `worker` 镜像。这个方式适合开发验证，但会占用 NAS 的 CPU、内存和网络时间。

镜像版部署使用 `docker-compose.portainer-image.yml`，不包含 `build:`。Portainer 只从 GHCR 拉取已经构建好的镜像：

```text
ghcr.io/pdsci996/engineering-photo-map-frontend:${IMAGE_TAG}
ghcr.io/pdsci996/engineering-photo-map-api:${IMAGE_TAG}
ghcr.io/pdsci996/engineering-photo-map-worker:${IMAGE_TAG}
```

群晖 Portainer 长期部署推荐使用镜像版。源码构建版仍可用于本地开发或排查 Dockerfile。

## 为什么分正式堆栈和测试堆栈

正式堆栈保存真实生产数据，应追求稳定。测试堆栈用于验证新版本、环境变量、反向代理、上传和导出流程。

建议：

- 正式堆栈名：`photo-map-prod`
- 测试堆栈名：`photo-map-test`
- 正式数据目录：`/volume1/docker/photo-map/data`
- 测试数据目录：`/volume1/docker/photo-map-test/data`
- 正式堆栈使用：`IMAGE_TAG=stable`
- 测试堆栈使用：`IMAGE_TAG=v0.4.7-public-initial` 或其他具体版本号
- 正式堆栈建议：`FRONTEND_PORT=25173`、`API_PORT=18000`
- 测试堆栈建议：`FRONTEND_PORT=35173`、`API_PORT=29000`

正式堆栈升级前，应先在测试堆栈验证。测试通过后，再把该版本标记为 `stable`，然后升级正式堆栈。

## 文件选择

公开仓库中可以提交：

- `docker-compose.portainer-image.yml`
- `.env.portainer-prod.example`
- `.env.portainer-test.example`
- `docs/群晖Portainer镜像版部署说明.md`

本地真实配置不能提交：

- `photo-map-prod.local.env`
- `photo-map-test.local.env`
- 其他 `*.local.env`

这些本地文件应由 `.gitignore` 忽略。

## 正式堆栈 env

正式堆栈可参考 `.env.portainer-prod.example`。复制后在本地保存为 `photo-map-prod.local.env`，再按自己的部署环境修改。

关键项：

```text
COMPOSE_PROJECT_NAME=photo-map-prod
IMAGE_TAG=stable
HOST_DATA_DIR=/volume1/docker/photo-map/data
FRONTEND_PORT=25173
API_PORT=18000
PUBLIC_BASE_URL=https://photos.example.com
API_BASE_URL=https://api.photos.example.com
VITE_API_BASE_URL=https://api.photos.example.com
CORS_ORIGINS=https://photos.example.com
```

`POSTGRES_PASSWORD` 必须改成强密码。不要把真实密码提交到 GitHub。

## 测试堆栈 env

测试堆栈可参考 `.env.portainer-test.example`。复制后在本地保存为 `photo-map-test.local.env`，再按自己的测试环境修改。

关键项：

```text
COMPOSE_PROJECT_NAME=photo-map-test
IMAGE_TAG=v0.4.7-public-initial
HOST_DATA_DIR=/volume1/docker/photo-map-test/data
FRONTEND_PORT=35173
API_PORT=29000
PUBLIC_BASE_URL=https://phototest.example.com
API_BASE_URL=https://api-test.example.com
VITE_API_BASE_URL=https://api-test.example.com
CORS_ORIGINS=https://phototest.example.com
```

以后测试新版本时，通常只需要改 `IMAGE_TAG`，例如改成新的 Release 标签。

## 远程域名和跨域

建议把前端域名和 API 域名分开：

- `PUBLIC_BASE_URL`：外部访问前端的地址。
- `API_BASE_URL`：外部访问 API 的地址。
- `VITE_API_BASE_URL`：浏览器中的前端访问 API 的完整地址，通常和 `API_BASE_URL` 一致。
- `CORS_ORIGINS`：允许访问 API 的前端地址，通常填写 `PUBLIC_BASE_URL`。

如果有多个前端来源，可以用英文逗号分隔。不要把不需要的域名加入 `CORS_ORIGINS`。

`VITE_ALLOWED_HOSTS` / `ALLOWED_HOSTS` 用于限制允许的 Host。建议包含前端域名、API 域名、`localhost` 和 `127.0.0.1`。生产环境中不要随意使用通配符。

## 端口映射和反向代理

frontend 容器内部端口固定为 `5173`，不使用 `80`。`FRONTEND_PORT` 是群晖宿主机映射端口：

- 正式堆栈建议：`FRONTEND_PORT=25173`
- 测试堆栈建议：`FRONTEND_PORT=35173`

api 容器内部端口固定为 `8000`。`API_PORT` 是群晖宿主机映射端口：

- 正式堆栈建议：`API_PORT=18000`
- 测试堆栈建议：`API_PORT=29000`

群晖反向代理中，前端域名应指向群晖本机对应的 `FRONTEND_PORT`，API 域名应指向群晖本机对应的 `API_PORT`。例如测试域名 `phototest` 指向测试堆栈的 `FRONTEND_PORT`，正式域名 `photo` 指向正式堆栈的 `FRONTEND_PORT`。

外网 `80/443`、反向代理监听端口、群晖宿主机映射端口、容器内部端口是四层不同概念。Compose 中只配置宿主机端口到容器内部端口的映射，外网入口由群晖反向代理负责。

## 固定 Docker 网络地址

如果 Portainer / Docker 网络地址池提示用尽，或自动分配网段失败，可以使用固定网段：

```text
DOCKER_NETWORK_SUBNET=10.77.46.0/24
DOCKER_NETWORK_GATEWAY=10.77.46.1
```

测试堆栈必须使用另一个网段，例如：

```text
DOCKER_NETWORK_SUBNET=10.77.47.0/24
DOCKER_NETWORK_GATEWAY=10.77.47.1
```

如果部署时报 `network overlaps`，说明这个网段已经被其他 Docker 网络占用。处理方法：

1. 在 Portainer 或 Docker 中查看已有 network。
2. 给当前堆栈换一个未被占用的私有网段。
3. 同时修改 `DOCKER_NETWORK_SUBNET` 和 `DOCKER_NETWORK_GATEWAY`。
4. 重新部署 Stack。

正式堆栈和测试堆栈不能使用同一个 `DOCKER_NETWORK_SUBNET`。

## Portainer 部署步骤

1. 打开 Portainer，进入目标 Environment。
2. 进入 `Stacks`，点击 `Add stack`。
3. Stack 名称填写 `photo-map-prod` 或 `photo-map-test`。
4. 选择 `Web editor`。
5. 复制 `docker-compose.portainer-image.yml` 的全部内容，粘贴到 Web editor。
6. 在环境变量区域点击 `Load variables from .ENV file`。
7. 正式堆栈导入 `photo-map-prod.local.env`，测试堆栈导入 `photo-map-test.local.env`。
8. 检查 `IMAGE_TAG`、端口、域名、数据目录和 Docker 网络网段。
9. 点击部署。

如果使用公开 GHCR 镜像，通常不需要配置 registry 凭据。如果镜像是私有包，需要先在 Portainer 中配置可读取 GHCR 的 registry 凭据。

## Missing mandatory value

如果 Portainer 提示变量缺失或 `Missing mandatory value`，通常是 env 没有导入完整。处理方法：

1. 检查 env 文件是否包含 compose 中引用的所有变量。
2. 确认没有把变量名写错。
3. 确认 `COMPOSE_PROJECT_NAME`、`IMAGE_TAG`、`HOST_DATA_DIR`、`FRONTEND_PORT`、`API_PORT`、`DOCKER_NETWORK_SUBNET` 和 `DOCKER_NETWORK_GATEWAY` 都已填写。
4. 重新点击 `Load variables from .ENV file` 导入。

## 访问和健康检查

部署完成后：

- 前端访问：打开 `PUBLIC_BASE_URL`，或用群晖地址加 `FRONTEND_PORT` 访问。
- API 健康检查：打开 `API_BASE_URL/api/health`，或用群晖地址加 `API_PORT` 访问 `/api/health`。

如果页面能打开但 API 失败，优先检查 `VITE_API_BASE_URL`、`CORS_ORIGINS`、反向代理和 API 容器日志。

## 查看日志

在 Portainer Stack 页面中分别查看这些服务日志：

- `frontend`：前端页面服务日志。
- `api`：后端 API 请求、错误和健康检查日志。
- `worker`：后台照片处理任务日志。
- `db`：PostgreSQL/PostGIS 数据库日志。
- `redis`：Redis 队列和缓存日志。

上传失败、预览图不生成、任务不执行时，通常需要同时看 `api`、`worker` 和 `redis`。

## 升级和数据保护

升级应用时可以删除应用容器和旧镜像，但不能删除 `HOST_DATA_DIR`。

`HOST_DATA_DIR` 中保存数据库、原图、缩略图、预览图、导出文件、日志和备份。删除这个目录会导致数据丢失。

推荐升级流程：

1. 在测试堆栈修改 `IMAGE_TAG` 为新版本。
2. 部署测试堆栈并验证上传、地图、导出、后台处理和 API 健康检查。
3. 测试通过后，把该版本标记为 `stable`。
4. 正式堆栈继续使用 `IMAGE_TAG=stable`，重新拉取镜像并部署。

正式堆栈升级前，应先备份 `.env` 和 `HOST_DATA_DIR`。
