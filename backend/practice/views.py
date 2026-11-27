# -*- coding: utf-8 -*-
"""自由练习接口：题目浏览、练习提交与评论区。"""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.jwt import login_required

from . import controllers
from .models import PracticeSubmission, ProblemComment


class PracticeProblemListView(APIView):
    """开放自由练习的算法题列表。"""

    @extend_schema(
        responses={200: OpenApiResponse(description="练习题目列表")},
        description="返回 practice_enabled=True 的算法题，支持关键字 / 难度 / 语言筛选",
        summary="自由练习题目",
    )
    @login_required
    def get(self, request, *args, **kwargs):
        problems = controllers.practice_problems(
            keyword=request.query_params.get("keyword") or None,
            difficulty=request.query_params.get("difficulty") or None,
            language=request.query_params.get("language") or None,
        )
        return Response(
            {"problems": [controllers.problem_summary(p) for p in problems]},
            status=status.HTTP_200_OK,
        )


class PracticeProblemDetailView(APIView):
    """题目详情：题面 + 公开样例 + 初始代码（隐藏用例不下发）。"""

    @login_required
    def get(self, request, problem_id, *args, **kwargs):
        problem = controllers.get_practice_problem(problem_id)
        if problem is None:
            return Response({"message": "题目不存在或未开放练习"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(controllers.problem_detail(problem), status=status.HTTP_200_OK)


class PracticeSubmissionView(APIView):
    """某道题的练习提交：GET 我的提交历史 / POST 提交代码。"""

    @login_required
    def get(self, request, problem_id, *args, **kwargs):
        problem = controllers.get_practice_problem(problem_id)
        if problem is None:
            return Response({"message": "题目不存在或未开放练习"},
                            status=status.HTTP_404_NOT_FOUND)
        submissions = (
            PracticeSubmission.objects.filter(student=request.user, problem=problem)
            .order_by("-id")[:20]
        )
        return Response(
            {"submissions": [controllers.submission_payload(s) for s in submissions]},
            status=status.HTTP_200_OK,
        )

    @login_required
    def post(self, request, problem_id, *args, **kwargs):
        problem = controllers.get_practice_problem(problem_id)
        if problem is None:
            return Response({"message": "题目不存在或未开放练习"},
                            status=status.HTTP_404_NOT_FOUND)
        content = request.data or {}
        try:
            submission = controllers.create_submission(
                request.user,
                problem,
                content.get("code"),
                str(content.get("language") or ""),
            )
        except controllers.PracticeError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"submission": controllers.submission_payload(submission)},
            status=status.HTTP_201_CREATED,
        )


class PracticeSubmissionDetailView(APIView):
    """单次练习提交的结果（仅本人可见）。"""

    @login_required
    def get(self, request, submission_id, *args, **kwargs):
        submission = (
            PracticeSubmission.objects.select_related("problem")
            .filter(id=submission_id)
            .first()
        )
        if submission is None:
            return Response({"message": "提交不存在"}, status=status.HTTP_404_NOT_FOUND)
        if submission.student_id != request.user.id:
            return Response({"message": "无权查看该提交"},
                            status=status.HTTP_403_FORBIDDEN)
        return Response(
            {
                "submission": controllers.submission_payload(submission),
                "problemTitle": submission.problem.title,
            },
            status=status.HTTP_200_OK,
        )


class PracticeCommentView(APIView):
    """题目的评论区：GET 列表 / POST 发布评论（可附带代码）。"""

    @login_required
    def get(self, request, problem_id, *args, **kwargs):
        problem = controllers.get_practice_problem(problem_id)
        if problem is None:
            return Response({"message": "题目不存在或未开放练习"},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            limit = int(request.query_params.get("limit") or 100)
        except (TypeError, ValueError):
            limit = 100
        comments = controllers.list_comments(problem, limit)
        return Response(
            {"comments": [controllers.comment_payload(c) for c in comments]},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "讨论内容"},
                    "code": {"type": "string", "description": "可选：附带的代码"},
                    "language": {"type": "string", "description": "代码语言"},
                    "parentId": {"type": "integer", "description": "回复的评论 id，省略为顶层评论"},
                },
            }
        },
        description="发布评论；content 与 code 至少填一项，可用 parentId 回复某条评论",
        summary="发布题目评论",
    )
    @login_required
    def post(self, request, problem_id, *args, **kwargs):
        problem = controllers.get_practice_problem(problem_id)
        if problem is None:
            return Response({"message": "题目不存在或未开放练习"},
                            status=status.HTTP_404_NOT_FOUND)
        content = request.data or {}
        try:
            comment = controllers.create_comment(
                request.user,
                problem,
                content.get("content"),
                content.get("code"),
                str(content.get("language") or ""),
                content.get("parentId"),
            )
        except controllers.PracticeError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"comment": controllers.comment_payload(comment)},
            status=status.HTTP_201_CREATED,
        )


class PracticeCommentDetailView(APIView):
    """删除自己的评论（教师 / 管理员可删除任意评论）。"""

    @login_required
    def delete(self, request, comment_id, *args, **kwargs):
        comment = ProblemComment.objects.select_related("author").filter(
            id=comment_id
        ).first()
        if comment is None:
            return Response({"message": "评论不存在"}, status=status.HTTP_404_NOT_FOUND)
        if not controllers.can_delete_comment(request.user, comment):
            return Response({"message": "无权删除该评论"},
                            status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({"message": "已删除"}, status=status.HTTP_200_OK)
