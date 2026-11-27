# 构建上下文是仓库根目录（见 backend/docker-compose.yml）。
# 镜像阶段：
#   frontend      —— 构建前端静态资源
#   backend       —— Django + Gunicorn 生产服务
#   agent_worker  —— 工程题 AI harness worker（额外安装 mini-swe-agent）
#   nginx         —— 静态资源 + 反向代理

FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
COPY frontend/scripts/copy-monaco.js ./scripts/copy-monaco.js
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code:/deploy-data \
    DJANGO_SETTINGS_MODULE=app.settings_prod
WORKDIR /code
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "300"]

# 工程题 AI harness worker：单独镜像，避免主后端携带 LiteLLM / mini-swe-agent。
FROM python:3.11-slim-bookworm AS agent_worker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code:/deploy-data \
    DJANGO_SETTINGS_MODULE=app.settings_prod \
    LITELLM_LOCAL_MODEL_COST_MAP=True
WORKDIR /code
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc default-libmysqlclient-dev pkg-config docker-cli \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/requirements-harness.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-harness.txt
COPY backend/ ./

FROM nginx:1.28-alpine AS nginx
COPY backend/nginx/app.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend /frontend/build /code/build
