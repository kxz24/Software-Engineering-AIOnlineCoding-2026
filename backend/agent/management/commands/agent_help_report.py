"""Generate an experimental, evidence-linked help report for one session."""

import json

from django.core.management.base import BaseCommand, CommandError

from agent.models import AgentSession
from agent.report import ReportError, report_for_session


class Command(BaseCommand):
    help = "按会话生成学生求助程度的试验性报告（不评分）"

    def add_arguments(self, parser):
        parser.add_argument("session_id", type=int)

    def handle(self, *args, **options):
        session = AgentSession.objects.filter(id=options["session_id"]).first()
        if session is None:
            raise CommandError("AI 会话不存在")
        try:
            report = report_for_session(session)
        except ReportError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({"sessionId": session.id, **report},
                                     ensure_ascii=False, indent=2))
