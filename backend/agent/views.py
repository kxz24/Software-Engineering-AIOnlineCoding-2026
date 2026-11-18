# -*- coding: utf-8 -*-
"""AI 助教接口。

学生端：能力查询、会话、消息（SSE）、工作区、修改记录与撤销；
教师端：按考试的用量与 AI 修改汇总、会话转录。
"""
import json
import logging

from django.conf import settings
from django.http import StreamingHttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from exam.controllers import is_candidate
from exam.models import Exam
from user.models import User
from utils.jwt import login_required, role_required

from . import service
from .levels import LEVEL_LABELS, can_edit_code, level_for_exam, tools_for_level
from .models import AgentMessage, AgentSession, CodeChange, WorkspaceFile
from .providers import provider_info
from .tools import ensure_workspace

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------
def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _iso(value):
    return value.isoformat() if value else None


def _load_exam(exam_id):
    return Exam.objects.filter(id=exam_id).first()


def _load_problem_in_exam(exam, problem_id):
    item = exam.exam_problems.filter(problem_id=problem_id).select_related("problem").first()
    return item.problem if item else None


def _window_error(exam):
    """AI 只在考试进行中可用。"""
    if exam.status != Exam.STATUS_PUBLISHED:
        return "考试未发布或已归档"
    now = timezone.now()
    if exam.start_time and now < exam.start_time:
        return "考试尚未开始"
    if exam.end_time and now > exam.end_time:
        return "考试已结束"
    return None


def _student_exam_error(user, exam, problem_id=None, require_window=True):
    if not is_candidate(exam, user):
        return "不在本场考试的名单中"
    if problem_id is not None and _load_problem_in_exam(exam, problem_id) is None:
        return "本场考试没有这道题"
    if require_window:
        return _window_error(exam)
    return None


def _session_for_user(session_id, user):
    session = (
        AgentSession.objects.select_related("exam", "problem", "student")
        .filter(id=session_id)
        .first()
    )
    if session is None or session.student_id != user.id:
        return None
    return session


def _session_for_staff_or_owner(session_id, user):
    session = (
        AgentSession.objects.select_related("exam", "problem", "student")
        .filter(id=session_id)
        .first()
    )
    if session is None:
        return None
    if session.student_id == user.id or user.role in (User.ROLE_TEACHER, User.ROLE_ADMIN):
        return session
    return None


def _message_payload(message):
    return {
        "seq": message.seq,
        "role": message.role,
        "content": message.content,
        "toolCalls": message.tool_calls,
        "toolCallId": message.tool_call_id,
        "name": message.name,
        "usage": message.usage,
        "inputTokens": message.input_tokens,
        "outputTokens": message.output_tokens,
        "finishReason": message.finish_reason,
        "created": _iso(message.created),
    }


def _file_payload(file):
    return {
        "path": file.path,
        "content": file.content,
        "revision": file.revision,
        "updatedAt": _iso(file.updated_at),
    }


def _change_payload(change):
    return {
        "changeId": change.id,
        "path": change.file_path,
        "revisionBefore": change.revision_before,
        "revisionAfter": change.revision_after,
        "diff": change.diff,
        "status": change.status,
        "created": _iso(change.created),
        "revertedAt": _iso(change.reverted_at),
    }


# ---------------------------------------------------------------------------
# 学生端
# ---------------------------------------------------------------------------
class AgentCapabilitiesView(APIView):
    """当前考试的 AI 级别、可用工具与剩余额度。"""

    @extend_schema(
        responses={
            200: OpenApiResponse(description="级别与能力"),
            403: OpenApiResponse(description="未开启 AI / 不在名单"),
            404: OpenApiResponse(description="考试或题目不存在"),
        },
        description="查询当前考试的 AI 级别、可用工具与剩余 token 额度",
        summary="AI 能力",
    )
    @login_required
    def get(self, request, *args, **kwargs):
        exam = _load_exam(request.query_params.get("examId"))
        if exam is None:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        problem_id = request.query_params.get("problemId")
        error = _student_exam_error(request.user, exam, problem_id, require_window=False)
        if error:
            return Response({"message": error}, status=status.HTTP_403_FORBIDDEN)
        level = level_for_exam(exam)
        if level == AgentSession.LEVEL_NONE:
            return Response(
                {"message": "本场考试未开启 AI"}, status=status.HTTP_403_FORBIDDEN
            )
        info = provider_info()
        return Response({
            "enabled": True,
            "level": level,
            "levelLabel": LEVEL_LABELS.get(level, level),
            "canEditCode": can_edit_code(level),
            "tools": list(tools_for_level(level)),
            "provider": info["provider"],
            "model": info["model"],
            "mock": info["mock"],
            "ready": info["mock"] or info["configured"],
            "promptVersion": getattr(settings, "AGENT_PROMPT_VERSION", "v1"),
            "quota": service.quota_info(exam, request.user),
        }, status=status.HTTP_200_OK)


class AgentSessionView(APIView):
    """创建或取回某场考试某道题的 AI 会话。"""

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "examId": {"type": "integer"},
                    "problemId": {"type": "integer"},
                },
                "required": ["examId", "problemId"],
            }
        },
        responses={201: OpenApiResponse(description="会话信息")},
        description="创建或取回会话；每场考试每道题只有一个会话，可续聊",
        summary="创建 AI 会话",
    )
    @login_required
    def post(self, request, *args, **kwargs):
        content = request.data or {}
        exam = _load_exam(content.get("examId"))
        if exam is None:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        problem_id = content.get("problemId")
        error = _student_exam_error(request.user, exam, problem_id, require_window=True)
        if error:
            return Response({"message": error}, status=status.HTTP_403_FORBIDDEN)
        problem = _load_problem_in_exam(exam, problem_id)
        try:
            session = service.get_or_create_session(exam, request.user, problem)
        except service.AgentError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        info = provider_info()
        return Response({
            "sessionId": session.id,
            "level": session.level,
            "levelLabel": LEVEL_LABELS.get(session.level, session.level),
            "provider": info["provider"],
            "model": session.model or info["model"],
            "canEditCode": can_edit_code(session.level),
            "createdAt": _iso(session.created),
            "quota": service.quota_info(exam, request.user),
        }, status=status.HTTP_201_CREATED)


class AgentMessageListView(APIView):
    """会话消息历史（增量拉取）。"""

    @login_required
    def get(self, request, session_id, *args, **kwargs):
        session = _session_for_user(session_id, request.user)
        if session is None:
            return Response({"message": "会话不存在"}, status=status.HTTP_404_NOT_FOUND)
        after = request.query_params.get("afterSeq")
        queryset = session.messages.all()
        try:
            after = int(after) if after not in (None, "") else 0
        except (TypeError, ValueError):
            after = 0
        if after:
            queryset = queryset.filter(seq__gt=after)
        try:
            limit = min(200, max(1, int(request.query_params.get("limit") or 100)))
        except (TypeError, ValueError):
            limit = 100
        return Response(
            {"messages": [_message_payload(item) for item in queryset[:limit]]},
            status=status.HTTP_200_OK,
        )


class AgentMessageCreateView(APIView):
    """发送一条消息，返回 SSE 流。"""

    def perform_content_negotiation(self, request, force=False):
        """SSE 响应不走 DRF 渲染器；固定按 JSON 协商，避免 Accept: text/event-stream 返回 406。"""
        return JSONRenderer(), "application/json"

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "clientMessageId": {"type": "string", "description": "幂等键"},
                    "content": {"type": "string", "description": "考生消息"},
                    "activeFile": {"type": "string", "description": "当前文件路径"},
                    "code": {"type": "string", "description": "当前编辑器内容"},
                    "workspaceRevision": {"type": "integer", "description": "前端持有的版本号"},
                },
                "required": ["content"],
            }
        },
        responses={200: OpenApiResponse(description="SSE 事件流")},
        description="发送消息。返回 text/event-stream：delta / tool_call / tool_result / "
                    "change / usage / done / error",
        summary="发送消息",
    )
    @login_required
    def post(self, request, session_id, *args, **kwargs):
        session = _session_for_user(session_id, request.user)
        if session is None:
            return Response({"message": "会话不存在"}, status=status.HTTP_404_NOT_FOUND)
        error = _student_exam_error(request.user, session.exam, session.problem_id, True)
        if error:
            return Response({"message": error}, status=status.HTTP_403_FORBIDDEN)

        content = request.data or {}
        text = str(content.get("content") or "").strip()
        if not text:
            return Response({"message": "消息不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        if len(text) > 8000:
            return Response({"message": "消息过长（上限 8000 字）"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            service.ensure_quota(session.exam, request.user)
        except service.QuotaExceeded as exc:
            return Response({"message": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # 同步前端当前代码到服务端工作区（三级模式下不覆盖较新的 AI 写入）
        active_file = str(content.get("activeFile") or "").strip()
        code = content.get("code")
        if active_file and isinstance(code, str):
            revision = content.get("workspaceRevision")
            try:
                revision = int(revision) if revision is not None else None
            except (TypeError, ValueError):
                revision = None
            try:
                ensure_workspace(session, active_file, code, expected_revision=revision)
            except ValueError as exc:
                return Response({"message": str(exc)},
                                status=status.HTTP_400_BAD_REQUEST)

        user_message = service.add_user_message(session, text)

        def stream():
            yield _sse("meta", {
                "sessionId": session.id,
                "userSeq": user_message.seq,
            })
            try:
                for event in service.generate_events(session):
                    event_type = event.pop("type")
                    if event_type == "done":
                        last = (
                            session.messages.filter(role=AgentMessage.ROLE_ASSISTANT)
                            .order_by("-seq").first()
                        )
                        event["assistantSeq"] = last.seq if last else None
                    yield _sse(event_type, event)
            except Exception:  # noqa: BLE001 —— 流已开始，只能以事件形式报错
                logger.exception("AI 回复生成失败 session=%s", session.id)
                yield _sse("error", {"code": "internal", "message": "生成回复失败"})
                yield _sse("done", {"finishReason": "error"})

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AgentMessagesView(AgentMessageListView, AgentMessageCreateView):
    """同一路径上的消息读取（GET）与发送（POST）。"""


class AgentWorkspaceView(APIView):
    """三级模式的工作区读写。"""

    @login_required
    def get(self, request, *args, **kwargs):
        exam = _load_exam(request.query_params.get("examId"))
        if exam is None:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        problem_id = request.query_params.get("problemId")
        error = _student_exam_error(request.user, exam, problem_id, require_window=False)
        if error:
            return Response({"message": error}, status=status.HTTP_403_FORBIDDEN)
        problem = _load_problem_in_exam(exam, problem_id)
        files = WorkspaceFile.objects.filter(
            exam=exam, student=request.user, problem=problem
        ).order_by("path")
        return Response({"files": [_file_payload(item) for item in files]},
                        status=status.HTTP_200_OK)

    @login_required
    def put(self, request, *args, **kwargs):
        content = request.data or {}
        exam = _load_exam(content.get("examId"))
        if exam is None:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        problem_id = content.get("problemId")
        error = _student_exam_error(request.user, exam, problem_id, require_window=True)
        if error:
            return Response({"message": error}, status=status.HTTP_403_FORBIDDEN)
        problem = _load_problem_in_exam(exam, problem_id)
        path = str(content.get("path") or "").strip()
        if not path or path.startswith("/") or ".." in path.split("/"):
            return Response({"message": "非法的文件路径"},
                            status=status.HTTP_400_BAD_REQUEST)
        file, _created = WorkspaceFile.objects.get_or_create(
            exam=exam, student=request.user, problem=problem, path=path,
            defaults={"content": "", "revision": 1},
        )
        expected = content.get("expectedRevision")
        if expected is not None:
            try:
                expected = int(expected)
            except (TypeError, ValueError):
                return Response({"message": "expectedRevision 必须是整数"},
                                status=status.HTTP_400_BAD_REQUEST)
            if file.revision != expected:
                return Response(
                    {"message": f"文件已被修改（当前版本 {file.revision}），请刷新后重试"},
                    status=status.HTTP_409_CONFLICT,
                )
        file.content = str(content.get("content") or "")
        file.revision += 1
        file.save(update_fields=["content", "revision", "updated_at"])
        return Response(_file_payload(file), status=status.HTTP_200_OK)


class AgentChangeListView(APIView):
    """会话内 AI 对代码的修改记录。"""

    @login_required
    def get(self, request, session_id, *args, **kwargs):
        session = _session_for_staff_or_owner(session_id, request.user)
        if session is None:
            return Response({"message": "会话不存在"}, status=status.HTTP_404_NOT_FOUND)
        changes = session.code_changes.all()[:200]
        return Response({"changes": [_change_payload(item) for item in changes]},
                        status=status.HTTP_200_OK)


class AgentChangeRevertView(APIView):
    """撤销一次 AI 修改（恢复到修改前的正文）。"""

    @login_required
    def post(self, request, change_id, *args, **kwargs):
        change = CodeChange.objects.select_related("session").filter(id=change_id).first()
        if change is None or change.student_id != request.user.id:
            return Response({"message": "修改记录不存在"}, status=status.HTTP_404_NOT_FOUND)
        error = _window_error(change.exam)
        if error:
            return Response({"message": error}, status=status.HTTP_403_FORBIDDEN)
        if change.status != CodeChange.STATUS_APPLIED:
            return Response({"message": "该修改已撤销"}, status=status.HTTP_400_BAD_REQUEST)

        file = WorkspaceFile.objects.filter(
            exam=change.exam, student=change.student, problem=change.problem,
            path=change.file_path,
        ).first()
        if file is None:
            return Response({"message": "文件不存在"}, status=status.HTTP_404_NOT_FOUND)

        expected = (request.data or {}).get("expectedRevision")
        if expected is not None:
            try:
                expected = int(expected)
            except (TypeError, ValueError):
                return Response({"message": "expectedRevision 必须是整数"},
                                status=status.HTTP_400_BAD_REQUEST)
            if file.revision != expected:
                return Response(
                    {"message": f"文件已被修改（当前版本 {file.revision}），请刷新后重试"},
                    status=status.HTTP_409_CONFLICT,
                )

        file.content = change.before_text
        file.revision += 1
        file.save(update_fields=["content", "revision", "updated_at"])
        change.status = CodeChange.STATUS_REVERTED
        change.reverted_at = timezone.now()
        change.save(update_fields=["status", "reverted_at"])
        return Response({
            "path": file.path,
            "revision": file.revision,
            "content": file.content,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 教师端
# ---------------------------------------------------------------------------
class AgentExamSummaryView(APIView):
    """按考试汇总每个学生的 AI 用量与修改次数。"""

    @extend_schema(
        responses={200: OpenApiResponse(description="按学生的用量汇总")},
        description="按学生汇总 token、消息数、AI 修改次数；教师 / 管理员可看",
        summary="AI 用量汇总",
    )
    @role_required(User.ROLE_TEACHER, User.ROLE_ADMIN)
    def get(self, request, exam_id, *args, **kwargs):
        exam = _load_exam(exam_id)
        if exam is None:
            return Response({"message": "考试不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(service.exam_summary(exam), status=status.HTTP_200_OK)


class AgentSessionTranscriptView(APIView):
    """单条会话的完整转录（本人或教师 / 管理员）。"""

    @login_required
    def get(self, request, session_id, *args, **kwargs):
        session = _session_for_staff_or_owner(session_id, request.user)
        if session is None:
            return Response({"message": "会话不存在"}, status=status.HTTP_404_NOT_FOUND)
        tool_calls = [
            {
                "callId": item.call_id,
                "name": item.name,
                "arguments": item.arguments,
                "ok": item.ok,
                "resultExcerpt": item.result_excerpt,
                "durationMs": item.duration_ms,
                "created": _iso(item.created),
            }
            for item in session.tool_calls.all()[:500]
        ]
        return Response({
            "session": {
                "id": session.id,
                "examId": session.exam_id,
                "problemId": session.problem_id,
                "problemTitle": session.problem.title,
                "student": session.student.username,
                "level": session.level,
                "levelLabel": LEVEL_LABELS.get(session.level, session.level),
                "provider": session.provider,
                "model": session.model,
                "promptVersion": session.prompt_version,
                "status": session.status,
                "inputTokens": session.input_tokens,
                "outputTokens": session.output_tokens,
                "cacheHitTokens": session.cache_hit_tokens,
                "cacheMissTokens": session.cache_miss_tokens,
                "created": _iso(session.created),
                "lastActiveAt": _iso(session.last_active_at),
                "endedAt": _iso(session.ended_at),
            },
            "messages": [_message_payload(item) for item in session.messages.all()],
            "toolCalls": tool_calls,
            "changes": [_change_payload(item) for item in session.code_changes.all()],
        }, status=status.HTTP_200_OK)
