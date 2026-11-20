from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import User
from utils.jwt import login_required, role_required

from . import controllers
from .models import Exam


def _parse_time(value):
    """前端时间字符串 → 带时区 datetime；非法返回 None"""
    parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _validate_fields(content, partial=False):
    """校验考试字段，返回 (fields, error)。partial=True 用于 PATCH。"""
    fields = {}

    def has(key):
        return key in content and content[key] is not None

    if has("title") or not partial:
        title = str(content.get("title") or "").strip()
        if not title or len(title) > 128:
            return None, "考试名称不能为空且不超过 128 个字符"
        fields["title"] = title
    if has("course"):
        fields["course"] = str(content.get("course") or "").strip()[:64]
    if has("description"):
        fields["description"] = str(content.get("description") or "")
    if has("notice"):
        fields["notice"] = str(content.get("notice") or "")

    for key, column in (("startTime", "start_time"), ("endTime", "end_time")):
        if has(key):
            if str(content.get(key) or "").strip() == "":
                fields[column] = None
                continue
            parsed = _parse_time(content.get(key))
            if parsed is None:
                return None, f"{key} 格式不正确，应为 YYYY-MM-DD HH:MM"
            fields[column] = parsed

    if has("durationMinutes"):
        try:
            duration = int(content.get("durationMinutes"))
        except (TypeError, ValueError):
            return None, "考试时长应为分钟数"
        if duration < 1 or duration > 24 * 60:
            return None, "考试时长应在 1–1440 分钟之间"
        fields["duration_minutes"] = duration
    if has("submitLimit"):
        try:
            limit = int(content.get("submitLimit"))
        except (TypeError, ValueError):
            return None, "提交次数应为整数"
        if limit < 1 or limit > 99:
            return None, "提交次数应在 1–99 之间"
        fields["submit_limit"] = limit
    ai_choices = [key for key, _ in Exam.AI_MODE_CHOICES]
    if has("aiMode"):
        value = content.get("aiMode")
        if value not in ai_choices:
            return None, f"AI 策略仅支持 {'/'.join(ai_choices)}"
        fields["ai_mode"] = value

    if fields.get("start_time") and fields.get("end_time") \
            and fields["end_time"] <= fields["start_time"]:
        return None, "结束时间必须晚于开始时间"
    return fields, None


def _validate_problem_items(content):
    """组卷载荷：[{problemId, score}]，顺序即题序。"""
    raw = content.get("problems")
    if not isinstance(raw, list):
        return None, "problems 需为数组"
    if len(raw) > 50:
        return None, "单场考试题目过多（上限 50）"
    items = []
    for entry in raw:
        if not isinstance(entry, dict):
            return None, "题目条目格式不正确"
        try:
            problem_id = int(entry.get("problemId"))
        except (TypeError, ValueError):
            return None, "problemId 不能为空"
        score = entry.get("score", 100)
        try:
            score = int(score)
        except (TypeError, ValueError):
            return None, "分值应为整数"
        if score < 1 or score > 1000:
            return None, "分值应在 1–1000 之间"
        items.append({"problemId": problem_id, "score": score})
    return items, None


def _load_exam(exam_id):
    return controllers.get_exam(exam_id)


def _exam_response_or_error(result):
    """控制器返回 (reason, False) 时统一包装成 400 响应"""
    reason, ok = result
    if ok:
        return None
    return Response({"message": reason}, status=status.HTTP_400_BAD_REQUEST)


def _frozen_error(exam):
    """开始后 / 归档后的编辑限制；返回 None 表示可编辑"""
    if exam.status == Exam.STATUS_PUBLISHED:
        if exam.start_time and timezone.now() >= exam.start_time:
            return Response(
                {"message": "考试已开始，配置已冻结；请先撤回（开始前）或等待结束"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    if exam.status == Exam.STATUS_ARCHIVED:
        return Response(
            {"message": "已归档的考试不能编辑"}, status=status.HTTP_400_BAD_REQUEST
        )
    return None


class ExamListView(APIView):
    """考试列表 / 创建考试（教师与管理员）"""

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def get(self, request, *args, **kwargs):
        exams = controllers.list_exams(status=request.query_params.get("status") or None)
        return Response(
            {"exams": [controllers.exam_summary(exam) for exam in exams]},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "考试名称"},
                    "course": {"type": "string", "description": "课程"},
                    "description": {"type": "string", "description": "考试说明"},
                    "notice": {"type": "string", "description": "考试须知"},
                    "startTime": {"type": "string", "description": "开始时间 YYYY-MM-DD HH:MM"},
                    "endTime": {"type": "string", "description": "结束时间 YYYY-MM-DD HH:MM"},
                    "durationMinutes": {"type": "integer", "description": "时长（分钟）"},
                    "submitLimit": {"type": "integer", "description": "每题提交次数上限"},
                    "aiMode": {"type": "string", "description": "limited / open / closed"},
                },
                "required": ["title"],
            }
        },
        description="创建考试（保存为草稿，组卷与名单随后配置）",
        summary="创建考试",
    )
    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def post(self, request, *args, **kwargs):
        fields, error = _validate_fields(request.data or {}, partial=False)
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)
        exam, ok = controllers.create_exam(request.user, fields)
        return Response(controllers.exam_detail(exam), status=status.HTTP_201_CREATED)


class ExamDetailView(APIView):
    """考试详情 / 编辑 / 删除（教师与管理员）"""

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def get(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(controllers.exam_detail(exam), status=status.HTTP_200_OK)

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def patch(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        frozen = _frozen_error(exam)
        if frozen:
            return frozen

        fields, error = _validate_fields(request.data or {}, partial=True)
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)
        exam, ok = controllers.update_exam(request.user, exam, fields)
        return Response(controllers.exam_detail(exam), status=status.HTTP_200_OK)

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def delete(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        error = _exam_response_or_error(controllers.delete_exam(request.user, exam))
        if error:
            return error
        return Response({"message": "ok"}, status=status.HTTP_200_OK)


class ExamProblemsView(APIView):
    """组卷：整体替换本场考试的题目与分值（教师与管理员）"""

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def put(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        frozen = _frozen_error(exam)
        if frozen:
            return frozen
        items, error = _validate_problem_items(request.data or {})
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)
        error = _exam_response_or_error(controllers.set_exam_problems(request.user, exam, items))
        if error:
            return error
        return Response(controllers.exam_detail(exam), status=status.HTTP_200_OK)


class ExamCandidatesView(APIView):
    """考生名单：整体替换；空数组表示全体学生（教师与管理员）"""

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def put(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        frozen = _frozen_error(exam)
        if frozen:
            return frozen
        raw = (request.data or {}).get("candidates")
        if not isinstance(raw, list) or any(not isinstance(name, str) for name in raw):
            return Response({"message": "candidates 需为字符串数组"}, status=status.HTTP_400_BAD_REQUEST)
        usernames = [name.strip() for name in raw if name.strip()]
        if len(usernames) != len(set(usernames)):
            return Response({"message": "名单中有重复账号"}, status=status.HTTP_400_BAD_REQUEST)
        ok, valid = controllers.set_candidates(request.user, exam, usernames)
        if not valid:
            return Response({"message": ok}, status=status.HTTP_400_BAD_REQUEST)
        return Response(controllers.exam_detail(exam), status=status.HTTP_200_OK)


class ExamActionView(APIView):
    """发布 / 撤回 / 归档（教师与管理员）"""

    def _transition(self, request, exam_id, action):
        exam, ok = _load_exam(exam_id)
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        handler = {
            "publish": controllers.publish_exam,
            "withdraw": controllers.withdraw_exam,
            "archive": controllers.archive_exam,
        }[action]
        result = handler(request.user, exam)
        reason, ok = result
        if not ok:
            return Response({"message": reason}, status=status.HTTP_400_BAD_REQUEST)
        return Response(controllers.exam_detail(exam), status=status.HTTP_200_OK)

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def post(self, request, *args, **kwargs):
        action = kwargs.get("action")
        if action not in ("publish", "withdraw", "archive"):
            return Response({"message": "未知操作"}, status=status.HTTP_400_BAD_REQUEST)
        return self._transition(request, kwargs.get("exam_id"), action)


class ExamSubmissionsView(APIView):
    """管理端：本场考试的提交记录（教师与管理员）"""

    @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)
    def get(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        problem_id = request.query_params.get("problemId")
        submissions = controllers.exam_submissions(exam, problem_id)
        return Response(
            {"submissions": submissions, "total": len(submissions)},
            status=status.HTTP_200_OK,
        )


class MyExamListView(APIView):
    """学生侧：我可见的考试（已发布且在名单内，或名单为空）"""

    @login_required
    def get(self, request, *args, **kwargs):
        return Response(
            {"exams": controllers.student_exams(request.user)}, status=status.HTTP_200_OK
        )


class MyExamDetailView(APIView):
    """学生侧：考试详情（题面 + 样例测试 + 初始代码，不含隐藏测试）"""

    @login_required
    def get(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        detail, ok = controllers.student_exam_detail(request.user, exam)
        if not ok:
            return Response({"message": detail}, status=status.HTTP_403_FORBIDDEN)
        return Response(detail, status=status.HTTP_200_OK)


class MyExamSubmissionsView(APIView):
    """学生侧：我在本场考试的提交记录"""

    @login_required
    def get(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {"submissions": controllers.my_submissions(request.user, exam)},
            status=status.HTTP_200_OK,
        )


class MySubmissionView(APIView):
    """学生侧：对某道题提交代码 / 查看我的提交历史"""

    @login_required
    def get(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        result, ok = controllers.student_exam_detail(request.user, exam)
        if not ok:
            return Response({"message": result}, status=status.HTTP_403_FORBIDDEN)
        mine = [
            item for item in controllers.my_submissions(request.user, exam)
            if item["problemId"] == kwargs.get("problem_id")
        ]
        return Response({"submissions": mine}, status=status.HTTP_200_OK)

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "代码正文"},
                    "language": {"type": "string", "description": "语言，缺省用题目语言"},
                },
                "required": ["code"],
            }
        },
        description="提交代码。当前只收卷存档（status=pending），判题服务接入后回填结果",
        summary="提交代码",
    )
    @login_required
    def post(self, request, *args, **kwargs):
        exam, ok = _load_exam(kwargs.get("exam_id"))
        if not ok:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        content = request.data or {}
        code = str(content.get("code") or "")
        if not code.strip():
            return Response({"message": "代码不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        if len(code) > 200_000:
            return Response({"message": "代码过长（上限 200 KB）"}, status=status.HTTP_400_BAD_REQUEST)

        submission, code_status, ok = controllers.create_submission(
            request.user, exam, kwargs.get("problem_id"), code,
            str(content.get("language") or ""),
        )
        if not ok:
            return Response({"message": submission}, status=code_status)
        used = controllers.submission_count(exam, submission.problem_id, request.user)
        return Response(
            {
                "submission": {
                    "id": submission.id,
                    "problemId": submission.problem_id,
                    "status": submission.status,
                    "created": submission.created.isoformat(),
                    "language": submission.language,
                },
                "used": used,
                "remaining": max(0, exam.submit_limit - used),
            },
            status=status.HTTP_201_CREATED,
        )
