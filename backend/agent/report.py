"""Experimental, evidence-linked description of the help a student requested."""

import json

from django.conf import settings

from .providers import DeepSeekProvider, ProviderError


class ReportError(Exception):
    pass


ACTIVITIES = {"knowledge", "algorithm", "coding", "debugging", "other"}

REPORT_RULES = """你是考试对话的过程分析员。只根据给定对话，返回 JSON，不要 Markdown。
结构：{"turns":[{"userSeq":整数,"activity":"knowledge|algorithm|coding|debugging|other",
"helpLevel":0到4的整数,"receivedLevel":0到4的整数,"evidence":"原话中的短摘录"}],
"overview":"简短中文总结",
"limitations":"证据限制"}。
每条学生提问都要有一项；userSeq 必须来自输入中的学生消息。
helpLevel 是学生请求的深度，receivedLevel 是助教实际给予的深度；
0=无帮助，1=概念或思路，2=算法设计或调试方向，
3=某个明确局部实现/修错，4=完整解法。不得把助教主动给得过多算成学生索取；
若两者不一致，在 overview 单独说明。
evidence 必须逐字摘自对应 userSeq 的学生提问，不能从助教回答中摘取。
不能据此断言学生已经学会、
存在作弊或给出最终成绩。"""


def build_help_report(messages, provider):
    """Return a validated draft report; never infer mastery or a score."""
    dialogue = [
        {"seq": int(item["seq"]), "role": item["role"],
         "content": str(item.get("content") or "")}
        for item in messages if item["role"] in ("user", "assistant")
    ]
    user_seqs = {item["seq"] for item in dialogue if item["role"] == "user"}
    if not user_seqs:
        raise ReportError("会话没有学生提问")
    payload = [
        {"role": "system", "content": REPORT_RULES},
        {"role": "user", "content": json.dumps(dialogue, ensure_ascii=False)},
    ]
    parts = []
    try:
        for event in provider.stream(payload, [], max_tokens=4096):
            if event["type"] == "delta":
                parts.append(event["text"])
    except ProviderError as exc:
        raise ReportError(str(exc)) from exc
    raw = "".join(parts).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(raw)
        turns = result["turns"]
        if not isinstance(turns, list) or len(turns) != len(user_seqs):
            raise ValueError("missing or extra turns")
        seen = set()
        user_text = {item["seq"]: item["content"] for item in dialogue
                     if item["role"] == "user"}
        for turn in turns:
            seq = turn["userSeq"]
            level = turn["helpLevel"]
            received = turn["receivedLevel"]
            evidence = turn["evidence"]
            if seq not in user_seqs or seq in seen:
                raise ValueError("fabricated user sequence")
            if (turn["activity"] not in ACTIVITIES or type(level) is not int
                    or not 0 <= level <= 4 or type(received) is not int
                    or not 0 <= received <= 4):
                raise ValueError("invalid activity or level")
            if not isinstance(evidence, str) or not evidence or evidence not in user_text[seq]:
                raise ValueError("unsupported evidence")
            seen.add(seq)
        if not isinstance(result["overview"], str) or not isinstance(result["limitations"], str):
            raise ValueError("invalid summary")
    except (ValueError, TypeError, KeyError) as exc:
        raise ReportError("汇报模型返回了无效或无依据的结果") from exc
    return result


def report_for_session(session):
    provider = DeepSeekProvider(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=getattr(settings, "AGENT_GUARD_BASE_URL", settings.DEEPSEEK_BASE_URL),
        model=getattr(settings, "AGENT_REPORT_MODEL", "Qwen3.8-Flash"),
        timeout=int(getattr(settings, "AGENT_REQUEST_TIMEOUT", 180)),
    )
    messages = list(session.messages.filter(role__in=("user", "assistant"))
                    .order_by("seq").values("seq", "role", "content"))
    return build_help_report(messages, provider)
