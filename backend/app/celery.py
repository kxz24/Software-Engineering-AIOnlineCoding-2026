# -*- coding: utf-8 -*-
"""Celery 应用：判题等耗时任务放在独立 worker 中执行。"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("aicoding")
# 从 Django settings 读取 CELERY_* 配置
app.config_from_object("django.conf:settings", namespace="CELERY")
# 自动发现各应用下的 tasks.py（judge.tasks 等）
app.autodiscover_tasks()
