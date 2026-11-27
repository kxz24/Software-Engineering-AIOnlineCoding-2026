"""Asynchronous, explicitly authorized project harness runs."""

import logging

from celery import shared_task

from .models import AgentHarnessJob

logger = logging.getLogger(__name__)


@shared_task(bind=True, time_limit=900, soft_time_limit=870)
def run_agent_harness_job(self, job_id):
    job = AgentHarnessJob.objects.select_related("session__problem").get(pk=job_id)
    started = AgentHarnessJob.objects.filter(
        pk=job_id, status=AgentHarnessJob.STATUS_QUEUED,
    ).update(status=AgentHarnessJob.STATUS_RUNNING)
    if not started:
        return
    job.status = AgentHarnessJob.STATUS_RUNNING
    try:
        from .harness import execute_project_job
        execute_project_job(job)
    except Exception as exc:
        logger.exception("工程 Agent 任务失败 job=%s", job_id)
        job.refresh_from_db()
        if job.status == AgentHarnessJob.STATUS_CANCELLED:
            return
        job.status = AgentHarnessJob.STATUS_FAILED
        from .harness_scope import ScopeReviewError
        job.error = ("改动范围审查未通过，文件未应用。"
                     if isinstance(exc, ScopeReviewError)
                     else "工程任务执行失败，请查看服务端日志后重试。")
        job.save(update_fields=["status", "error", "updated"])
        raise
