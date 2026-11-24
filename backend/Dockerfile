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

FROM nginx:1.28-alpine AS nginx
COPY backend/nginx/app.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend /frontend/build /code/build
