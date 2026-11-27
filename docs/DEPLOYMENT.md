# AICoding 部署说明

## 访问地址

公网地址为 `https://82.157.147.142:8043`。Caddy 在公网 `8043` 端口接收加密访问，并把请求转发给 `127.0.0.1:8000` 上的项目 Nginx。Nginx 提供前端页面，并将后端请求交给 Django。MySQL 和 Redis 使用 Docker 内部网络。

使用公网地址时须带上 `:8043`。公网 `80` 将普通网页请求跳转到 `8043`，也用于 Let's Encrypt 的证书签发与续期验证。云端入站规则需允许 `80/tcp` 和 `8043/tcp`，证书及续期状态存放在 `caddy_data` 数据卷。[证书说明](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability)

## 配置文件

| 文件 | 用途 |
| --- | --- |
| `backend/docker-compose.yml` | 应用、数据库、队列、判题服务和项目 Nginx |
| `backend/docker-compose.public.yml` | 启动公网入口，设置 Django 接受的主机地址和安全 Cookie |
| `backend/Caddyfile` | 公网地址、证书签发方式及转发目标 |
| `backend/.env` | 服务器实际运行参数和密钥。初次部署参考 `.env.example` 填写并保存在服务器 |

涉及公网地址的修改需要同时更新 `Caddyfile` 和 `docker-compose.public.yml`。部署配置先在本地 `lh` 分支维护，再同步到服务器。应用监听地址保持为 `127.0.0.1:8000`。

## 启动与更新

在服务器进入项目的 `backend` 目录。首次部署或更新应用代码时，执行以下命令：

```bash
cd ~/Software-Engineering-AIOnlineCoding-2026/backend
docker compose -f docker-compose.yml -f docker-compose.public.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.public.yml --profile build build judge-base
docker compose -f docker-compose.yml -f docker-compose.public.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.public.yml ps -a
```

后续仅在判题镜像缺失、或 `backend/judge` 下的镜像构建内容变动时重建 `judge-base`。现有服务器目录有未提交的项目文件，更新前先用 `git status --short` 核对，并确认本次发布使用的源码版本。保留现有 `.env`、MySQL 数据卷和 Caddy 数据卷。涉及数据库结构的变更先备份数据库。

如果只改了 `Caddyfile`，同步后可以在运行中的容器内重新加载：

```bash
docker compose -f docker-compose.yml -f docker-compose.public.yml exec edge caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

## 发布后检查

- `migrate` 应显示 `Exited (0)`，MySQL 和 Redis 应为 `healthy`，应用、判题、Nginx 和 Caddy 应为运行状态。
- 从服务器外访问 `https://82.157.147.142:8043`，确认首页正常且浏览器信任证书。使用测试账号登录后，再按本次改动检查助教或判题功能。
- 若公网 `8043` 超时，检查云控制台的入站规则。可在服务器上用下方第一条命令验证证书和网关，再用第二条查看入口日志。

```bash
curl -I --connect-to 82.157.147.142:8043:127.0.0.1:8043 https://82.157.147.142:8043/
docker compose -f docker-compose.yml -f docker-compose.public.yml logs --tail=80 edge
```
