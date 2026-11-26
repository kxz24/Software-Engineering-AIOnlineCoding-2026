# -*- coding: utf-8 -*-
"""判题结果查询接口。"""

from django.http import HttpResponse

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from exam.models import ProjectSubmission, Submission
from judge.ftp import review_project
from user.controllers import record_audit
from user.models import User
from utils.jwt import login_required, role_required


def _iso(value):
    return value.isoformat() if value else None


def _serialize_case(case, *, project=False):
    data = {
        "name": case.name,
        "isSample": case.is_sample,
        "verdict": case.verdict,
        "timeMs": case.time_ms,
        "memoryKb": case.memory_kb,
    }
    # 隐藏用例只返回判定与资源用量，不返回输入/期望输出/实际输出
    if case.is_sample or project:
        data["outputExcerpt"] = case.output_excerpt
        data["errorExcerpt"] = case.error_excerpt
    return data


def _serialize_submission(submission):
    project = ProjectSubmission.objects.defer("archive").filter(submission=submission).first()
    return {
        "id": submission.id,
        "examId": submission.exam_id,
        "problemId": submission.problem_id,
        "problemTitle": submission.problem.title,
        "username": submission.student.username,
        "nickname": submission.student.nickname,
        "language": submission.language,
        "status": submission.status,
        "verdict": submission.verdict,
        "score": submission.score,
        "passedCount": submission.passed_count,
        "totalCount": submission.total_count,
        "samplePassed": submission.sample_passed,
        "sampleTotal": submission.sample_total,
        "hiddenPassed": submission.hidden_passed,
        "hiddenTotal": submission.hidden_total,
        "timeMs": submission.time_ms,
        "memoryKb": submission.memory_kb,
        "compileOutput": submission.compile_output,
        "judgeError": submission.judge_error,
        "needsReview": submission.needs_review,
        "created": _iso(submission.created),
        "judgedAt": _iso(submission.judged_at),
        "code": submission.code,
        "cases": [_serialize_case(case, project=project is not None) for case in submission.cases.all()],
        "project": {
            "automaticPoints": project.automatic_points,
            "warmupPoints": project.warmup_points,
            "reportPoints": project.report_points,
            "bonusPoints": project.bonus_points,
        } if project else None,
    }


class SubmissionDetailView(APIView):
    """单条提交详情：本人或教师 / 管理员可查看。"""

    @extend_schema(
        responses={
            200: OpenApiResponse(description="提交详情与用例判定"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权查看"),
            404: OpenApiResponse(description="提交不存在"),
        },
        description="提交详情。隐藏用例只返回判定、耗时与内存，不返回输入/期望/实际输出。",
        summary="提交详情",
    )
    @login_required
    def get(self, request, submission_id, *args, **kwargs):
        submission = (
            Submission.objects.select_related("exam", "problem", "student")
            .filter(id=submission_id)
            .first()
        )
        if not submission:
            return Response(
                {"message": "提交不存在"}, status=status.HTTP_404_NOT_FOUND
            )
        is_owner = submission.student_id == request.user.id
        is_staff = request.user.role in (User.ROLE_ADMIN, User.ROLE_TEACHER)
        if not (is_owner or is_staff):
            return Response(
                {"message": "无权查看该提交"}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(
            _serialize_submission(submission), status=status.HTTP_200_OK
        )


class ProjectReviewView(APIView):
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def patch(self, request, submission_id, *args, **kwargs):
        if not ProjectSubmission.objects.filter(submission_id=submission_id).exists():
            return Response({"message": "工程提交不存在"}, status=status.HTTP_404_NOT_FOUND)
        fields = (("warmupPoints", 10), ("reportPoints", 20), ("bonusPoints", 10))
        body = request.data if isinstance(request.data, dict) else {}
        points = [body.get(key) for key, _ in fields]
        if any(type(value) is not int or not 0 <= value <= maximum
               for value, (_, maximum) in zip(points, fields)):
            return Response({"message": "预习、报告和加分的范围分别为 0–10、0–20、0–10 的整数"}, status=400)
        try:
            score = review_project(submission_id, *points)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        record_audit(request.user, "submission.project_review", f"{submission_id} {score}分")
        return Response({"score": score})


class ProjectArchiveView(APIView):
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def get(self, request, submission_id, *args, **kwargs):
        project = ProjectSubmission.objects.filter(submission_id=submission_id).first()
        if project is None:
            return Response({"message": "工程提交不存在"}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(bytes(project.archive), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="submission-{submission_id}.zip"'
        return response
