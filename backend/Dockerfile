# 清软论坛容器化部署
#
# 注意：本 Dockerfile 的构建上下文是仓库根目录（见 docker-compose.yml 中的
# context: ..），因为前端 frontend/ 与后端 backend/ 是同级目录，前端产物需要
# 在构建阶段由 node 生成后交给 Nginx 托管。
#
# 镜像分为两个可用的 target：
#   app   —— Django + Gunicorn 后端服务（容器名 app）
#   nginx —— Nginx 静态文件服务 + 反向代理（容器名 nginx）


# ---------------------------------------------------------------------------
# 阶段一：构建前端，产出 React 静态文件
# ---------------------------------------------------------------------------
FROM node:18 AS frontend-builder

WORKDIR /frontend

# 使用国内镜像源，避免在国内服务器上拉取依赖过慢
RUN npm config set registry https://registry.npmmirror.com

# 先只拷贝依赖清单，利用 Docker 层缓存，代码变动时不必重装依赖
COPY frontend/package.json frontend/package-lock.json ./

# 严格按照 package-lock.json 安装，保证构建结果可复现
RUN npm ci

# 拷贝前端源码并打包
COPY frontend/ ./

# react-scripts 3.4.3 基于 webpack 4，在 Node 17+ 上需要 openssl-legacy-provider
ENV NODE_OPTIONS=--openssl-legacy-provider

RUN npm run build


# ---------------------------------------------------------------------------
# 阶段二：后端运行环境（target: app）
# ---------------------------------------------------------------------------
FROM python:3.9 AS app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=app.settings_prod

WORKDIR /code

# 使用国内镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# mysqlclient 需要 MySQL 客户端库与编译工具
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 同样先装依赖，利用层缓存
COPY backend/requirements.txt /code/
RUN pip install -r requirements.txt

# 后端代码
COPY backend/ /code/

# 前端构建产物放到后端的 build 目录下，由 Nginx 提供静态文件服务
COPY --from=frontend-builder /frontend/build /code/build

EXPOSE 8000

CMD ["gunicorn", "-w4", "-b", "0.0.0.0:8000", "--log-level=debug", "app.wsgi"]


# ---------------------------------------------------------------------------
# 阶段三：Nginx（target: nginx）
# ---------------------------------------------------------------------------
FROM nginx:latest AS nginx

# 把配置文件放到 conf.d 下（nginx.conf 会 include conf.d/*.conf），
# 并删掉官方默认站点，避免容器内残留一个监听 80 端口的 server 块
COPY backend/nginx/app.conf /etc/nginx/conf.d/app.conf
RUN rm -f /etc/nginx/conf.d/default.conf

# 前端构建产物放到后端的 build 目录下，Nginx 直接对该目录提供静态文件服务
COPY --from=frontend-builder /frontend/build /code/build

EXPOSE 8000
