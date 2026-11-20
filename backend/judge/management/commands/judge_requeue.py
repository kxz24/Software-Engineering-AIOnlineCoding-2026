# -*- coding: utf-8 -*-
"""重新入队未完成的提交（Redis 故障或 worker 中断后的兜底）。"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from exam.models import Submission
from judge.constants import STATUS_JUDGING, STATUS_PENDING
from judge.tasks import judge_submission


class Command(BaseCommand):
    help = "把长时间 pending / judging 的提交重新入队判题"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pending-age", type=int, default=120,
            help="pending 超过多少秒后重新入队（默认 120）",
        )
        parser.add_argument(
            "--judging-age", type=int, default=600,
            help="judging 超过多少秒视为中断（默认 600）",
        )
        parser.add_argument(
            "--limit", type=int, default=100,
            help="单次最多处理多少条（默认 100）",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="只打印，不实际入队",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        pending_cutoff = now - timedelta(seconds=options["pending_age"])
        judging_cutoff = now - timedelta(seconds=options["judging_age"])

        pending = list(
            Submission.objects.filter(
                status=STATUS_PENDING, created__lt=pending_cutoff
            ).order_by("id")[: options["limit"]]
        )
        stale = list(
            Submission.objects.filter(
                status=STATUS_JUDGING, judge_started_at__lt=judging_cutoff
            ).order_by("id")[: options["limit"]]
        )

        for submission in stale:
            if not options["dry_run"]:
                Submission.objects.filter(
                    id=submission.id, status=STATUS_JUDGING
                ).update(status=STATUS_PENDING, judge_started_at=None)
            self.stdout.write(f"重置中断的 judging 提交 #{submission.id}")

        for submission in pending + stale:
            if options["dry_run"]:
                self.stdout.write(f"[dry-run] 入队 #{submission.id}")
                continue
            try:
                judge_submission.delay(submission.id)
                self.stdout.write(f"已入队 #{submission.id}")
            except Exception as exc:  # noqa: BLE001 - Redis 不可用时提示运维
                self.stderr.write(f"入队失败 #{submission.id}: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"处理完成：pending={len(pending)} stale_judging={len(stale)}"
        ))
