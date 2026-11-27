"""脚本工程题的分值校验和结果存档。"""
from django.db import transaction
from django.utils import timezone

from exam.models import ExamProblem, Submission, SubmissionCase
from judge.constants import STATUS_JUDGED
from judge.ftp_sandbox import run_script_sandbox
from judge.project import read_project
from judge.scoring import summarize


def grade_script(files, script, memory_limit_mb):
    raw = run_script_sandbox(files, script, memory_limit_mb).cases
    if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
        raise ValueError("评分脚本应返回 1–100 项评分结果")
    cases = []
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("评分项格式无效")
        earned, maximum = row.get("points"), row.get("max_points")
        name = row.get("name")
        if (
            not isinstance(name, str) or not name.strip()
            or type(earned) is not int or type(maximum) is not int
            or not 0 <= earned <= maximum <= 1000 or maximum == 0
        ):
            raise ValueError("评分项名称或分值无效")
        cases.append({
            "name": name.strip()[:64],
            "earned_points": earned,
            "max_points": maximum,
            "verdict": "accepted" if earned == maximum else "partial" if earned else "wrong_answer",
            "error_excerpt": str(row.get("feedback") or "")[:1000],
        })
    return cases


def project_preview(files, script, memory_limit_mb):
    cases = grade_script(files, script, memory_limit_mb)
    return {"status": "completed", "compileOk": True, "compileOutput": "", "cases": [
        {"index": index, "name": row["name"], "verdict": row["verdict"], "timeMs": 0,
         "expectedOutput": "", "outputExcerpt": "", "errorExcerpt": row["error_excerpt"],
         "earnedPoints": row["earned_points"], "maxPoints": row["max_points"]}
        for index, row in enumerate(cases, 1)
    ]}


def judge_project(submission, project):
    files = read_project(bytes(project.archive))
    cases = [
        {**case, "is_sample": is_public}
        for script, is_public in ((project.public_script, True), (project.hidden_script, False))
        for case in grade_script(files, script, submission.problem.memory_limit_mb)
    ]
    awarded = sum(row["earned_points"] for row in cases)
    maximum = sum(row["max_points"] for row in cases)
    limit = ExamProblem.objects.get(exam_id=submission.exam_id, problem_id=submission.problem_id).score
    summary = summarize(cases, 0)
    summary.update(
        status=STATUS_JUDGED, judged_at=timezone.now(), score=round(limit * awarded / maximum),
        verdict="accepted" if awarded == maximum else "partial" if awarded else "wrong_answer",
        needs_review=False,
    )
    with transaction.atomic():
        Submission.objects.filter(pk=submission.pk).update(**summary)
        submission.cases.all().delete()
        SubmissionCase.objects.bulk_create([
            SubmissionCase(submission=submission, case_index=index, **case)
            for index, case in enumerate(cases, 1)
        ])
