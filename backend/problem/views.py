from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import User
from utils.jwt import role_required

from . import controllers
from .models import Problem


def _validate_fields(content, partial=False):
    """
    校验题目字段，返回 (fields, error)。
    partial=True 时只校验出现的字段（用于 PATCH）。
    """
    fields = {}

    def has(key):
        return key in content and content[key] is not None

    if has("title") or not partial:
        title = str(content.get("title") or "").strip()
        if not title or len(title) > 128:
            return None, "标题不能为空且不超过 128 个字符"
        fields["title"] = title
    if has("description"):
        fields["description"] = str(content.get("description") or "")
    if has("starterCode"):
        fields["starter_code"] = str(content.get("starterCode") or "")
    if has("image"):
        image = str(content.get("image") or "").strip()
        if len(image) > 128:
            return None, "依赖镜像名过长"
        fields["image"] = image

    type_choices = [key for key, _ in Problem.TYPE_CHOICES]
    if has("type") or not partial:
        value = content.get("type") or Problem.TYPE_ENGINEERING
        if value not in type_choices:
            return None, f"题型仅支持 {'/'.join(type_choices)}"
        fields["type"] = value
    language_choices = [key for key, _ in Problem.LANGUAGE_CHOICES]
    if has("language") or not partial:
        value = content.get("language") or Problem.LANGUAGE_PYTHON
        if value not in language_choices:
            return None, f"语言仅支持 {'/'.join(language_choices)}"
        fields["language"] = value
    difficulty_choices = [key for key, _ in Problem.DIFFICULTY_CHOICES]
    if has("difficulty") or not partial:
        value = content.get("difficulty") or Problem.DIFFICULTY_MEDIUM
        if value not in difficulty_choices:
            return None, f"难度仅支持 {'/'.join(difficulty_choices)}"
        fields["difficulty"] = value

    return fields, None


def _validate_samples(content):
    """
    校验用例列表，返回 (samples, error)。未提供 samples 键时返回 (None, None)
    表示「不修改用例」。
    """
    if "samples" not in content or content["samples"] is None:
        return None, None
    raw = content["samples"]
    if not isinstance(raw, list):
        return None, "samples 需为数组"
    if len(raw) > 100:
        return None, "用例数量过多（上限 100）"
    samples = []
    for item in raw:
        if not isinstance(item, dict):
            return None, "用例格式不正确"
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 64:
            return None, "用例名称不能为空且不超过 64 个字符"
        samples.append(
            {
                "name": name,
                "input": str(item.get("input") or ""),
                "expected": str(item.get("expected") or ""),
                "isSample": bool(item.get("isSample", True)),
            }
        )
    return samples, None


class ProblemListView(APIView):
    """
    题目列表 / 创建题目（教师与管理员）。

    学生在作答页看到的是组卷后的题目与样例测试，
    题库整体仅对教师 / 管理员开放（隐藏测试不可泄露给学生）。
    """

    @extend_schema(
        responses={
            200: OpenApiResponse(description="题目列表"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要教师或管理员）"),
        },
        description="题库列表，支持关键字搜索与题型 / 语言过滤",
        summary="题目列表",
    )
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def get(self, request, *args, **kwargs):
        problems = controllers.list_problems(
            keyword=request.query_params.get("keyword") or None,
            problem_type=request.query_params.get("type") or None,
            language=request.query_params.get("language") or None,
        )
        return Response(
            {"problems": [controllers.problem_summary(p) for p in problems]},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "题目标题"},
                    "description": {"type": "string", "description": "题面（Markdown）"},
                    "type": {"type": "string", "description": "engineering / algorithm"},
                    "language": {"type": "string", "description": "python / cpp / c / java"},
                    "difficulty": {"type": "string", "description": "easy / medium / hard"},
                    "starterCode": {"type": "string", "description": "初始代码"},
                    "image": {"type": "string", "description": "依赖镜像"},
                    "samples": {
                        "type": "array",
                        "description": "测试样例列表：{name, input, expected, isSample}",
                    },
                },
                "required": ["title"],
            }
        },
        responses={
            201: OpenApiResponse(description="创建成功"),
            400: OpenApiResponse(description="无效的参数"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要教师或管理员）"),
        },
        description="创建题目（工程题 / 算法题），可同时携带测试样例与隐藏测试",
        summary="创建题目",
    )
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def post(self, request, *args, **kwargs):
        content = request.data or {}
        fields, error = _validate_fields(content, partial=False)
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)
        samples, error = _validate_samples(content)
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)

        problem, ok = controllers.create_problem(
            request.user, fields, samples or []
        )
        if not ok:
            return Response(
                {"message": "创建失败，请稍后重试"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            controllers.problem_detail(problem), status=status.HTTP_201_CREATED
        )


class ProblemDetailView(APIView):
    """
    查看 / 编辑 / 删除单个题目（教师与管理员，含隐藏测试）
    """

    @extend_schema(
        responses={
            200: OpenApiResponse(description="题目详情（含全部用例）"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限"),
            404: OpenApiResponse(description="题目不存在"),
        },
        description="题目详情，含题面、初始代码与样例 / 隐藏测试",
        summary="题目详情",
    )
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def get(self, request, *args, **kwargs):
        problem, ok = controllers.get_problem(kwargs.get("problem_id"))
        if not ok:
            return Response({"message": "题目不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(controllers.problem_detail(problem), status=status.HTTP_200_OK)

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "type": {"type": "string"},
                    "language": {"type": "string"},
                    "difficulty": {"type": "string"},
                    "starterCode": {"type": "string"},
                    "image": {"type": "string"},
                    "samples": {"type": "array"},
                },
            }
        },
        responses={
            200: OpenApiResponse(description="更新成功"),
            400: OpenApiResponse(description="无效的参数"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限"),
            404: OpenApiResponse(description="题目不存在"),
        },
        description="编辑题目；携带 samples 时整体替换用例列表",
        summary="编辑题目",
    )
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def patch(self, request, *args, **kwargs):
        problem, ok = controllers.get_problem(kwargs.get("problem_id"))
        if not ok:
            return Response({"message": "题目不存在"}, status=status.HTTP_404_NOT_FOUND)

        content = request.data or {}
        fields, error = _validate_fields(content, partial=True)
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)
        samples, error = _validate_samples(content)
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)

        problem, ok = controllers.update_problem(
            request.user, problem, fields, samples
        )
        if not ok:
            return Response(
                {"message": "更新失败，请稍后重试"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(controllers.problem_detail(problem), status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(description="删除成功"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限"),
            404: OpenApiResponse(description="题目不存在"),
        },
        description="删除题目（级联删除其测试用例）",
        summary="删除题目",
    )
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def delete(self, request, *args, **kwargs):
        problem, ok = controllers.get_problem(kwargs.get("problem_id"))
        if not ok:
            return Response({"message": "题目不存在"}, status=status.HTTP_404_NOT_FOUND)
        if not controllers.delete_problem(request.user, problem):
            return Response(
                {"message": "删除失败，请稍后重试"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"message": "ok"}, status=status.HTTP_200_OK)
