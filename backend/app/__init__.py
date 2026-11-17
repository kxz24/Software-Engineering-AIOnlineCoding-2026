# 确保 Django 启动时完成 Celery 应用的加载，@shared_task 才能正确注册。
from .celery import app as celery_app

__all__ = ("celery_app",)
