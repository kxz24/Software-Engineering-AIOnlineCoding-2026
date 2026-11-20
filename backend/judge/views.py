# -*- coding: utf-8 -*-
"""判题结果查询接口。"""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from exam.models import Submission
from user.models import User
from utils.jwt import login_required


def _iso(value):
    return value.isoformat() if value else None


def _serialize_case(case):
    data = {
        "name": case.name,
        "isSample": case.is_sample,
        "verdict": case.verdict,
        "timeMs": case.time_ms,
        "memoryKb": case.memory_kb,
    }
    # 隐藏用例只返回判定与资源用量，不返回输入/期望输出/实际输出
    if case.is_sample:
        data["outputExcerpt"] = case.output_excerpt
        data["errorExcerpt"] = case.error_excerpt
    return data


def _serialize_submission(submission):
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
        "cases": [_serialize_case(case) for case in submission.cases.all()],
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
