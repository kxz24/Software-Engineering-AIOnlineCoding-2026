import os

from .settings import *

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
    if host.strip()
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": "mysql",
        "PORT": "3306",
        "NAME": os.environ["MYSQL_DATABASE"],
        "USER": os.environ["MYSQL_USER"],
        "PASSWORD": os.environ["MYSQL_PASSWORD"],
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

# 项目未提交迁移文件，部署时生成并随数据一并持久化。
MIGRATION_MODULES = {
    app_label: f"aicoding_migrations.{app_label}"
    for app_label in ("user", "problem", "exam", "agent")
}

STATIC_URL = "/django-static/"
STATIC_ROOT = "/django-static"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.environ["DJANGO_SECURE_COOKIES"] == "1"
