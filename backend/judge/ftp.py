"""课程 FTP 项目的评分与人工复核。"""

from django.db import transaction
from django.utils import timezone

from exam.models import ExamProblem, Submission, SubmissionCase
from judge.constants import STATUS_JUDGED, VERDICT_ACCEPTED
from judge.ftp_sandbox import run_ftp_sandbox
from judge.project import read_project
from judge.sandbox import SandboxError
from judge.scoring import summarize


def judge_ftp(submission, project):
    result = run_ftp_sandbox(read_project(bytes(project.archive), ftp=True), submission.problem.memory_limit_mb)
    cases = result.cases
    if len(cases) != 18 or sum(case["points"] for case in cases) != 70:
        raise SandboxError("工程评测未返回完整的验收结果")

    summary = summarize(cases, 0)
    project.automatic_points = sum(
        case["points"] for case in cases if case["verdict"] == VERDICT_ACCEPTED
    )
    if "warning:" in result.compile_output:
        project.automatic_points = max(0, project.automatic_points - 1)
    summary.update(
        status=STATUS_JUDGED, judged_at=timezone.now(), compile_output=result.compile_output[:8192],
        judge_error="", needs_review=False,
        score=round(ExamProblem.objects.get(exam=submission.exam, problem=submission.problem).score
                    * project.automatic_points / 70),
    )
    with transaction.atomic():
        project.save(update_fields=["automatic_points"])
        Submission.objects.filter(pk=submission.pk).update(**summary)
        submission.cases.all().delete()
        SubmissionCase.objects.bulk_create([
            SubmissionCase(
                submission=submission, case_index=case["index"], name=case["name"],
                is_sample=False, verdict=case["verdict"], time_ms=case["time_ms"],
                error_excerpt=case["error_excerpt"][:300],
            )
            for case in cases
        ])

