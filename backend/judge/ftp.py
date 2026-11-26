"""课程 FTP 项目的评分与人工复核。"""

from django.db import transaction
from django.utils import timezone

from exam.models import ExamProblem, ProjectSubmission, Submission, SubmissionCase
from judge.constants import STATUS_JUDGED, VERDICT_ACCEPTED
from judge.ftp_sandbox import run_ftp_sandbox
from judge.project import read_project
from judge.sandbox import SandboxError
from judge.scoring import summarize


def project_score(project, submission):
    limit = ExamProblem.objects.get(exam_id=submission.exam_id, problem_id=submission.problem_id).score
    points = sum(value or 0 for value in (
        project.automatic_points, project.warmup_points, project.report_points, project.bonus_points,
    ))
    return round(points * limit / 100)


def judge_ftp(submission, project):
    result = run_ftp_sandbox(read_project(bytes(project.archive)), submission.problem.memory_limit_mb)
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
        judge_error="", needs_review=True, score=project_score(project, submission),
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


@transaction.atomic
def review_project(submission_id, warmup, report, bonus):
    submission = Submission.objects.select_for_update().get(pk=submission_id)
    project = ProjectSubmission.objects.defer("archive").get(submission=submission)
    if submission.status != STATUS_JUDGED or project.automatic_points is None:
        raise ValueError("自动评测结束后才能录入人工分")
    project.warmup_points = warmup
    project.report_points = report
    project.bonus_points = bonus
    project.save(update_fields=["warmup_points", "report_points", "bonus_points"])
    submission.score = project_score(project, submission)
    submission.needs_review = False
    submission.save(update_fields=["score", "needs_review"])
    return submission.score
