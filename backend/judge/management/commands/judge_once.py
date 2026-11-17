# -*- coding: utf-8 -*-
"""同步判一条提交，便于本地调试（不经过 Celery/Redis）。"""

from django.core.management.base import BaseCommand, CommandError

from exam.models import Submission
from judge.constants import STATUS_PENDING
from judge.tasks import judge_submission


class Command(BaseCommand):
    help = "同步判一条提交（调试用，不经过 Celery）"

    def add_arguments(self, parser):
        parser.add_argument("submission_id", type=int)
        parser.add_argument(
            "--force", action="store_true",
            help="先把提交重置为 pending，再重新判",
        )

    def handle(self, *args, **options):
        submission_id = options["submission_id"]
        submission = Submission.objects.filter(id=submission_id).first()
        if not submission:
            raise CommandError(f"提交 {submission_id} 不存在")

        if options["force"]:
            Submission.objects.filter(id=submission_id).update(
                status=STATUS_PENDING, judge_started_at=None
            )
        elif submission.status != STATUS_PENDING:
            self.stdout.write(
                self.style.WARNING(
                    f"提交当前状态为 {submission.status}，跳过；可加 --force 重新判"
                )
            )
            return

        judge_submission(submission_id)
        submission.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(
            f"提交 {submission_id}: status={submission.status} "
            f"verdict={submission.verdict} score={submission.score} "
            f"passed={submission.passed_count}/{submission.total_count}"
        ))
