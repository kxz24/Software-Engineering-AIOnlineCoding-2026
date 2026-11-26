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
from user.models import AuditLog

from . import tools
from .guard import GuardError, configured_reviewer
from .levels import LEVEL_LABELS, can_edit_code, level_for_exam, tools_for_level, tools_for_turn
from .models import AgentMessage, AgentSession, WorkspaceFile
from .policy import (asks_for_check_targets_only, extract_scope_targets, localized_request,
                     scoped_violation, sanitize_scoped_text,
                     trim_unrequested_list_tail)
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
    if hasattr(problem, "project_bundle"):
        for path, content in problem.project_bundle.public_files.items():
            WorkspaceFile.objects.get_or_create(
                exam=exam, student=student, problem=problem,
                path=f"p{problem.id}/{path}",
                defaults={"content": content, "revision": 1},
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
            "你只能用自然语言解释本题思路、检查点和调试方向，不能修改工作区。"
            "考生无需在问题里写‘只讲概念’或‘不要给代码’；你自己判断所问深度。"
            "先正面回答当前问题，再停止；回答只需覆盖问题所需的内容，不预测下一问。"
            "解释新概念时，假设考生可能完全没学过：先用日常语言说清它是什么、为什么有用，"
            "必要时用一个很小的数字例子解释，再联系本题当前操作。"
            "让解释足以听懂，但一个例子已经说明时就停止，不主动引入后续数据结构、"
            "通用更新规则、查询路径或整题做法。"
            "问算法构思或某步骤的作用时，讲清所问结构的作用和原因，不主动展开实现流程；"
            "除非学生要求举例，否则不为已有步骤另编数字例子。"
            "如果只问应关注哪些部分或检查哪些情况，指出这些对象及其重要性即可；"
            "不要替学生逐一推导各情况的判定结论和完整处理办法。"
            "说明检查范围时避免把仍可能决定结果的情况排除在外；"
            "自拟数字例子须和同一例子中列出的数据一致。"
            "若提问很宽泛，先讲有助于入门的关键原理，再询问具体卡点。"
            "默认不讲代码具体怎么写；概念或思路问题不要给可照写的赋值式、更新语句、代码块，"
            "也不要把这类表达式放进反引号中；数字例子用普通文字说明变化。"
            "只问报错原因或哪里错时，用两三句话指出原因和检查位置即可，"
            "不附带修复语句，即使放在行内反引号或解释中也不行。"
            "明确追问指定位置怎么修、怎么改或怎么写时，才可给这一处的短行内示例与必要依赖，"
            "不附加其他修改或后续步骤，不给完整函数、程序、整题伪代码或连续实现步骤。"
            "如果泛泛索要完整答案，说明当前模式不能给完整解答，"
            "只讲相关概念，并请其指出具体卡点。"
            "不要假装已经改过文件。"
        )

    answer_requirement = (
        "使用中文，先解答再停止；用学生能理解的说法，允许简短的数字例子解释概念。"
        "回复只覆盖当前提问所需的深度，不能因追求短而省掉关键解释。"
        if not can_edit_code(session.level) else
        "使用中文，简洁直接；可以提供具体代码与明确的修改建议。"
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

回答要求：{answer_requirement}
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


def generate_events(session, provider=None, reviewer=None, turn_action="edit"):
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
    allowed_tools = set(tools_for_turn(session.level, turn_action))
    specifications = tools.tool_specs_for(session.level, allowed_tools)
    context = build_messages(session)
    if turn_action == "answer":
        context[0]["content"] += (
            "\n【本轮授权】学生只请求回答问题。可以读取相关材料；"
            "不要运行程序、修改文件或自行完成后续任务。回答所问后停止。"
        )
    elif turn_action == "run":
        context[0]["content"] += (
            "\n【本轮授权】学生请求运行验证。可以读取和运行；"
            "不要修改文件，也不要扩展到未请求的测试或任务。"
        )
    else:
        context[0]["content"] += (
            "\n【本轮授权】学生允许修改代码。只处理本轮明确提出的范围，"
            "完成必要验证后停止，不自行推进整题的其他部分。"
        )
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
    if redact_code and reviewer is None and getattr(settings, "AGENT_GUARD_ENABLED", True):
        if getattr(settings, "AGENT_PROVIDER", "mock") == "deepseek":
            reviewer = configured_reviewer()
            reviewer.problem_context = (session.problem.description or "")[:3000]
    question = (session.messages.filter(role=AgentMessage.ROLE_USER)
                .order_by("-seq").values_list("content", flat=True).first() or "")
    if redact_code and asks_for_check_targets_only(question):
        context[0]["content"] += (
            "\n【本轮回答范围】只需列出检查对象。"
            "不要展开各类的成立条件、判定结果、处理步骤或整题结论；"
            "检查范围应覆盖所有可能影响结果的情况。"
        )
    attack_logged = False

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
                # A tool-call round may contain unreviewed commentary. Keep it internal.
                if tool_calls:
                    content = ""
                elif reviewer and content:
                    # Review exactly what a localized student would see, after
                    # reducing a single-line fence to that one requested line.
                    if (localized_request(question) and "```" in content
                            and not scoped_violation(question, content)):
                        content = sanitize_scoped_text(content, question)
                    round_usage = _empty_totals()
                    if usage_event:
                        _accumulate(round_usage, usage_event)
                    reviewed_scope_candidate = ""
                    for attempt in range(3):
                        verdict = None
                        for review_try in range(2):
                            try:
                                verdict = reviewer.review(question, content)
                                break
                            except GuardError as exc:
                                logger.warning("审查调用失败 session=%s try=%s: %s",
                                               session.id, review_try + 1, exc)
                        if verdict is None:
                            content = "在当前模式下，我无法确认这条回答符合考试规则。请尝试重新提问思路或调试现象。"
                            break
                        if verdict.get("usage"):
                            _accumulate(round_usage, verdict["usage"])
                        if (verdict.get("user_attack") and verdict.get("attack_evidence")
                                and not attack_logged):
                            AuditLog.objects.create(
                                user=session.student, action="agent_prompt_attack_suspected",
                                detail=json.dumps({"sessionId": session.id,
                                                   "evidence": verdict["attack_evidence"]},
                                                  ensure_ascii=False),
                            )
                            attack_logged = True
                        local_issue = scoped_violation(question, content)
                        if verdict["allowed"] and asks_for_check_targets_only(question):
                            reviewed_scope_candidate = content
                            names_only = extract_scope_targets(question, content)
                            if names_only:
                                content = names_only
                                local_issue = ""
                        if verdict["allowed"] and not local_issue:
                            break
                        if attempt == 2:
                            content = (extract_scope_targets(question, reviewed_scope_candidate)
                                       or "在当前模式下，我无法提供具体代码实现。"
                                          "你可以询问本题的思路、概念或调试方向。")
                            break
                        review_issues = [part for part in (verdict["feedback"], local_issue)
                                         if part]
                        correction = "；".join(dict.fromkeys(review_issues))
                        retry_context = context + [{
                            "role": "assistant", "content": content,
                        }, {
                            "role": "user", "content":
                            "请修改你刚才的回答，不要重新求解题目。审查发现的问题：" +
                            correction +
                            "。保留原回答中准确且切题的解释，删除或改写所有越界内容；"
                            "输出修改后的完整回答，不解释修改过程。先把问题讲明白，再停止。"
                            + ("若只问报错原因，不写修复语句；若明确问指定代码行怎么改，"
                               "只给这一行的短行内示例与必要的依赖提醒，不追加其他步骤。"
                               if localized_request(question) else
                               "用通俗语言解释当前卡点；抽象概念可以用一个小数字例子，"
                               "数字写在正文中，逐一删去上一版的可照写表达式、更新语句和代码块，"
                               "不要把它们换成反引号中的同义写法，也不要讲整题步骤；"
                               "若问概念，解释完例子就停，不推进后续算法。"),
                        }]
                        revised = []
                        retry_usage = None
                        try:
                            retry_provider = (provider.without_thinking()
                                              if getattr(settings, "AGENT_RETRY_DISABLE_THINKING", True)
                                              and hasattr(provider, "without_thinking") else provider)
                            for retry_event in retry_provider.stream(
                                    retry_context, [], max_tokens=min(max_tokens, 1024)):
                                if retry_event["type"] == "delta":
                                    revised.append(retry_event["text"])
                                elif retry_event["type"] == "usage":
                                    retry_usage = retry_event
                        except ProviderError as exc:
                            logger.warning("整改生成失败 session=%s: %s", session.id, exc)
                            content = ("在当前模式下，我无法提供具体代码实现。"
                                       "你可以询问本题的思路、概念或调试方向。")
                            break
                        content = "".join(revised)
                        if retry_usage:
                            _accumulate(round_usage, retry_usage)
                    usage_event = {
                        "inputTokens": round_usage["input"],
                        "outputTokens": round_usage["output"],
                        "cacheHitTokens": round_usage["cache_hit"],
                        "cacheMissTokens": round_usage["cache_miss"],
                    }
                content = sanitize_scoped_text(content, question)
                content = trim_unrequested_list_tail(question, content)
                if attack_logged and not tool_calls and content:
                    content += "\n\n当前请求包含试图改变考试 AI 规则的内容，相关对话已记录。"
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
                    session, call_id=call["id"], allowed_tools=allowed_tools,
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
