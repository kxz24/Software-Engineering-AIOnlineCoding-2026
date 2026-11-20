# -*- coding: utf-8 -*-
"""AI 会话的核心流程：组装上下文、调用模型、执行工具、落库与用量统计。

SSE 的传输细节由视图负责；本模块只产出结构化事件：
  delta / tool_call / tool_result / change / usage / done / error
"""
import json
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from . import tools
from .levels import LEVEL_LABELS, can_edit_code, level_for_exam, tools_for_level
from .models import AgentMessage, AgentSession
from .policy import sanitize_advise_text
from .providers import ProviderError, get_provider, provider_info

logger = logging.getLogger(__name__)

MAX_SYSTEM_FILE_CHARS = 12000
MAX_SYSTEM_SAMPLE_CHARS = 4000


class AgentError(Exception):
    """业务层错误：返回给前端 4xx。"""


class QuotaExceeded(AgentError):
    """本场考试的 AI token 额度已用完。"""


# ---------------------------------------------------------------------------
# 会话与额度
# ---------------------------------------------------------------------------
def usage_used(exam, student):
    """本场考试该学生已用的 token（所有题目合计）。"""
    agg = AgentSession.objects.filter(exam=exam, student=student).aggregate(
        input=Sum("input_tokens"), output=Sum("output_tokens")
    )
    return int(agg["input"] or 0) + int(agg["output"] or 0)


def quota_info(exam, student):
    limit = int(getattr(exam, "agent_token_quota", 0) or 0)
    used = usage_used(exam, student)
    return {
        "limit": limit,
        "used": used,
        "remaining": max(0, limit - used) if limit else None,
    }


def ensure_quota(exam, student):
    info = quota_info(exam, student)
    if info["limit"] and info["used"] >= info["limit"]:
        raise QuotaExceeded("本场考试的 AI 使用额度已用完")


def get_or_create_session(exam, student, problem):
    """取回或创建会话；级别在创建时快照。"""
    level = level_for_exam(exam)
    if level == AgentSession.LEVEL_NONE:
        raise AgentError("本场考试未开启 AI")
    info = provider_info()
    session, _created = AgentSession.objects.get_or_create(
        exam=exam,
        student=student,
        problem=problem,
        defaults={
            "level": level,
            "provider": info["provider"],
            "model": info["model"],
            "prompt_version": getattr(settings, "AGENT_PROMPT_VERSION", "v1"),
        },
    )
    return session


def level_capabilities(session):
    return {
        "level": session.level,
        "levelLabel": LEVEL_LABELS.get(session.level, session.level),
        "canEditCode": can_edit_code(session.level),
        "tools": list(tools_for_level(session.level)),
    }


# ---------------------------------------------------------------------------
# 消息落库
# ---------------------------------------------------------------------------
def next_seq(session):
    last = session.messages.order_by("-seq").values_list("seq", flat=True).first()
    return (last or 0) + 1


def add_user_message(session, content):
    with transaction.atomic():
        return AgentMessage.objects.create(
            session=session, seq=next_seq(session), role=AgentMessage.ROLE_USER,
            content=str(content or "")[:20000],
        )


def _add_message(session, role, content="", tool_calls=None, tool_call_id="",
                 name="", usage=None, finish_reason=""):
    input_tokens = int((usage or {}).get("inputTokens") or 0)
    output_tokens = int((usage or {}).get("outputTokens") or 0)
    return AgentMessage.objects.create(
        session=session,
        seq=next_seq(session),
        role=role,
        content=content or "",
        tool_calls=tool_calls or None,
        tool_call_id=tool_call_id or "",
        name=name or "",
        usage=(usage or {}).get("usage") if usage else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        finish_reason=finish_reason or "",
    )


def _add_usage(session, totals):
    if not totals:
        return
    AgentSession.objects.filter(id=session.id).update(
        input_tokens=F("input_tokens") + int(totals.get("input", 0)),
        output_tokens=F("output_tokens") + int(totals.get("output", 0)),
        cache_hit_tokens=F("cache_hit_tokens") + int(totals.get("cache_hit", 0)),
        cache_miss_tokens=F("cache_miss_tokens") + int(totals.get("cache_miss", 0)),
        # QuerySet.update 不会触发 auto_now，这里手动刷新「最近活跃」
        last_active_at=timezone.now(),
    )


# ---------------------------------------------------------------------------
# 上下文组装
# ---------------------------------------------------------------------------
def _system_prompt(session):
    problem = session.problem
    samples = list(problem.samples.filter(is_sample=True).order_by("id"))
    sample_text = "\n".join(
        f"- {sample.name}\n  输入：{sample.input_data[:500]}\n  期望输出：{sample.expected_output[:500]}"
        for sample in samples
    ) or "（本题没有公开样例）"
    if len(sample_text) > MAX_SYSTEM_SAMPLE_CHARS:
        sample_text = sample_text[:MAX_SYSTEM_SAMPLE_CHARS] + "\n…（样例已截断）"

    files = list(tools.workspace_files(session))
    file_text = ""
    for file in files:
        content = file.content or ""
        if len(content) > MAX_SYSTEM_FILE_CHARS:
            content = content[:MAX_SYSTEM_FILE_CHARS] + "\n…（内容已截断）"
        file_text += f"\n### {file.path}（版本 {file.revision}）\n```\n{content}\n```\n"
    if not file_text:
        file_text = "（工作区还没有文件）"

    if can_edit_code(session.level):
        ability = (
            "你可以直接修改工作区代码：先用 read_workspace 读取文件，再用 write_file "
            "写入完整的新内容；每次写入前确认文件版本，避免覆盖。"
        )
    else:
        ability = (
            "你只能给思路、检查点和调试方向，不能修改工作区。"
            "禁止输出完整代码、完整函数或完整程序，也不要把答案写成 Markdown 代码块；"
            "可以用行内短代码提及 API 或表达式名称。"
            "如果考生要求完整代码，必须明确拒绝，并引导其按思路自己实现。"
            "不要假装已经改过文件。"
        )

    return f"""你是 AI Coding 考试平台里的编程助教，正在协助一名考生完成考试题目。

【考试规则】
- 只能讨论本题；不提供与考试无关的答案。
- 隐藏测试用例对你不可见，不要尝试获取或猜测其内容，也不要声称能访问判题系统。
- 你的所有行为会被记录，用于过程评分与审计。

【当前级别】{LEVEL_LABELS.get(session.level, session.level)}
{ability}

题目：{problem.title}
语言：{problem.language}
单用例时限：{problem.time_limit_ms} ms
题目描述：
{problem.description or "（无题面）"}

公开样例：
{sample_text}

考生当前工作区：{file_text}

回答要求：使用中文，简洁直接；涉及代码时给出可运行的完整片段或明确的行级修改建议。
"""


def _history_messages(session):
    limit = int(getattr(settings, "AGENT_HISTORY_MESSAGES", 40))
    messages = list(
        session.messages.filter(
            role__in=[
                AgentMessage.ROLE_USER,
                AgentMessage.ROLE_ASSISTANT,
                AgentMessage.ROLE_TOOL,
            ]
        ).order_by("seq")
    )
    if len(messages) > limit:
        messages = messages[-limit:]
        # 不要从一条孤立的工具结果开始
        while messages and messages[0].role == AgentMessage.ROLE_TOOL:
            messages.pop(0)

    payload = []
    for message in messages:
        if message.role == AgentMessage.ROLE_USER:
            payload.append({"role": "user", "content": message.content})
        elif message.role == AgentMessage.ROLE_ASSISTANT:
            item = {"role": "assistant", "content": message.content or ""}
            if message.tool_calls:
                item["tool_calls"] = message.tool_calls
            payload.append(item)
        else:
            payload.append({
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "name": message.name,
                "content": message.content,
            })
    return payload


def build_messages(session):
    return [{"role": "system", "content": _system_prompt(session)}] + _history_messages(session)


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------
def _assistant_tool_calls(tool_calls):
    """把 provider 的工具调用事件转成 OpenAI 兼容的 assistant.tool_calls。"""
    return [
        {
            "id": call["id"],
            "type": "function",
            "function": {
                "name": call["name"],
                "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False),
            },
        }
        for call in tool_calls
    ]


def _empty_totals():
    return {"input": 0, "output": 0, "cache_hit": 0, "cache_miss": 0}


def _accumulate(totals, usage_event):
    totals["input"] += int(usage_event.get("inputTokens") or 0)
    totals["output"] += int(usage_event.get("outputTokens") or 0)
    totals["cache_hit"] += int(usage_event.get("cacheHitTokens") or 0)
    totals["cache_miss"] += int(usage_event.get("cacheMissTokens") or 0)


def generate_events(session, provider=None):
    """
    生成一次 AI 回复的事件流（同步生成器）。

    调用前用户消息已经落库；调用方负责把事件写成 SSE。
    """
    try:
        provider = provider or get_provider()
    except ProviderError as exc:
        yield {"type": "error", "code": "provider_config", "message": str(exc)}
        yield {"type": "done", "finishReason": "error"}
        return

    max_rounds = max(1, int(getattr(settings, "AGENT_MAX_TOOL_ROUNDS", 6)))
    max_tokens = int(getattr(settings, "AGENT_MAX_OUTPUT_TOKENS", 1024))
    specifications = tools.tool_specs_for(session.level)
    context = build_messages(session)
    totals = _empty_totals()
    collected_tool_calls = []
    finish_reason = "stop"

    def emit(event_name, data):
        # 工具内部通过它发 change 事件；这里转成 (type, data) 由上层处理
        events.append({"type": event_name, **data})

    events = []
    tool_context = tools.ToolContext(session, emit)
    # 二级会话在服务端过滤完整代码，不能只依赖提示词
    redact_code = not can_edit_code(session.level)

    try:
        for _round in range(max_rounds):
            text_parts = []
            tool_calls = []
            usage_event = None
            finish_reason = "stop"

            for event in provider.stream(context, specifications, max_tokens=max_tokens):
                if event["type"] == "delta":
                    text_parts.append(event["text"])
                    if not redact_code:
                        yield event
                elif event["type"] == "tool_call":
                    tool_calls.append(event)
                elif event["type"] == "usage":
                    usage_event = event
                elif event["type"] == "done":
                    finish_reason = event.get("finishReason") or "stop"

            content = "".join(text_parts)
            if redact_code:
                content = sanitize_advise_text(content)
                if content:
                    yield {"type": "delta", "text": content}
            assistant_calls = _assistant_tool_calls(tool_calls)
            _add_message(
                session,
                AgentMessage.ROLE_ASSISTANT,
                content=content,
                tool_calls=assistant_calls or None,
                usage=usage_event,
                finish_reason=finish_reason,
            )
            if usage_event:
                _accumulate(totals, usage_event)
                yield {"type": "usage", **usage_event}

            context.append({
                "role": "assistant",
                "content": content,
                **({"tool_calls": assistant_calls} if assistant_calls else {}),
            })

            if not tool_calls:
                break

            collected_tool_calls.extend(tool_calls)
            for call in tool_calls:
                yield {
                    "type": "tool_call",
                    "callId": call["id"],
                    "name": call["name"],
                    "arguments": call.get("arguments") or {},
                }
                ok, result = tools.execute_tool(
                    call["name"], call.get("arguments") or {}, tool_context,
                    session, call_id=call["id"],
                )
                _add_message(
                    session, AgentMessage.ROLE_TOOL, content=result,
                    tool_call_id=call["id"], name=call["name"],
                )
                context.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": call["name"],
                    "content": result,
                })
                yield {
                    "type": "tool_result",
                    "callId": call["id"],
                    "name": call["name"],
                    "ok": ok,
                    "result": result[:2000],
                }
                # 工具内部产生的事件（例如 change）紧跟其后
                while events:
                    yield events.pop(0)

            if finish_reason != "tool_calls":
                finish_reason = "tool_calls"
        else:
            # 达到工具轮次上限
            finish_reason = "length"
    except ProviderError as exc:
        logger.warning("模型调用失败 session=%s: %s", session.id, exc)
        _add_usage(session, totals)
        yield {"type": "error", "code": "provider_error", "message": str(exc)}
        yield {"type": "done", "finishReason": "error"}
        return

    _add_usage(session, totals)
    while events:
        yield events.pop(0)
    yield {"type": "done", "finishReason": finish_reason}


# ---------------------------------------------------------------------------
# 教师端汇总
# ---------------------------------------------------------------------------
def exam_sessions(exam):
    """教师端：本场考试的全部 AI 会话（含用量与消息/修改计数）。"""
    from django.db.models import Count

    sessions = (
        AgentSession.objects.filter(exam=exam)
        .select_related("student", "problem")
        .annotate(
            message_count=Count("messages", distinct=True),
            change_count=Count("code_changes", distinct=True),
        )
        .order_by("-last_active_at")
    )
    from .levels import LEVEL_LABELS

    return [
        {
            "sessionId": session.id,
            "student": session.student.username,
            "nickname": session.student.nickname,
            "problemId": session.problem_id,
            "problemTitle": session.problem.title,
            "level": session.level,
            "levelLabel": LEVEL_LABELS.get(session.level, session.level),
            "provider": session.provider,
            "model": session.model,
            "status": session.status,
            "inputTokens": session.input_tokens,
            "outputTokens": session.output_tokens,
            "cacheHitTokens": session.cache_hit_tokens,
            "messageCount": session.message_count,
            "changeCount": session.change_count,
            "created": session.created.isoformat() if session.created else None,
            "lastActiveAt": session.last_active_at.isoformat() if session.last_active_at else None,
        }
        for session in sessions
    ]


def exam_summary(exam):
    sessions = AgentSession.objects.filter(exam=exam).select_related("student")
    rows = {}
    for session in sessions:
        row = rows.setdefault(session.student_id, {
            "username": session.student.username,
            "nickname": session.student.nickname,
            "sessions": 0,
            "messages": 0,
            "inputTokens": 0,
            "outputTokens": 0,
            "cacheHitTokens": 0,
            "aiChanges": 0,
        })
        row["sessions"] += 1
        row["messages"] += session.messages.count()
        row["inputTokens"] += session.input_tokens
        row["outputTokens"] += session.output_tokens
        row["cacheHitTokens"] += session.cache_hit_tokens
        row["aiChanges"] += session.code_changes.count()

    students = list(rows.values())
    total = {
        "students": len(students),
        "inputTokens": sum(item["inputTokens"] for item in students),
        "outputTokens": sum(item["outputTokens"] for item in students),
        "aiChanges": sum(item["aiChanges"] for item in students),
    }
    return {"students": students, "total": total}
