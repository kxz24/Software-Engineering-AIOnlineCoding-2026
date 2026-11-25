"""Experimental, evidence-linked description of the help a student requested."""

import json

from django.conf import settings

from .providers import DeepSeekProvider, ProviderError, thinking_off_body


class ReportError(Exception):
    pass


ACTIVITIES = {"knowledge", "algorithm", "coding", "debugging", "other"}
STUDENT_FIELDS = ("summary", "focus", "repeatedQuestions",
                  "independentWork", "limitations")

REPORT_RULES = """你是考试对话的过程分析员。只根据给定对话，返回 JSON，不要 Markdown。
结构：{"turns":[{"userSeq":整数,"activity":"knowledge|algorithm|coding|debugging|other",
"helpLevel":0到4的整数,"receivedLevel":0到4的整数,"evidence":"原话中的短摘录"}],
"studentReport":{"summary":"按提问领域概述次数、主要问题和实际获得的回答",
"focus":"主要关注点","repeatedQuestions":"反复提问的主题，若无则说明未观察到",
"independentWork":"有证据支持的自主完成部分，若无则说明无法判断",
"limitations":"证据限制"}}。
每条学生提问都要有一项；userSeq 必须来自输入中的学生消息。
helpLevel 是学生请求的深度，receivedLevel 是助教实际给予的深度；
0=无帮助，1=概念或思路，2=算法设计或调试方向，
3=某个明确局部实现/修错，4=完整解法。不得把助教主动给得过多算成学生索取；
新术语的定义、小数字例子及其与当前题目操作的联系仍属 1；
询问多个解题组件各自的职责、为何配合，属于算法设计 2。
不能仅因回答出现题目操作或数据结构名称，就把概念解释判为 2。
只问错误原因或位置而未索要改法时，helpLevel 为 2，即使提到了具体报错或变量；
只有明确请求怎么改、怎么修时，局部修错的 helpLevel 才是 3。
evidence 必须逐字摘自对应 userSeq 的学生提问，不能从助教回答中摘取。
studentReport 只写学生问了什么、得到什么回答，以及有证据的学习活动；
按知识、算法、编程、调试等领域统计提问次数，聚焦具体主题，指出有无反复追问。
不要写模型、提示词、审查、规则、系统是否合规，也不要比较 helpLevel 与 receivedLevel；
这些信息只属于内部审查。没有代码或后续验证时，不得推断哪些部分由学生独立完成。
不能据此断言学生已经学会、存在作弊或给出最终成绩。"""


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
        student_report = result["studentReport"]
        if not isinstance(student_report, dict) or any(
                not isinstance(student_report.get(key), str)
                for key in STUDENT_FIELDS):
            raise ValueError("invalid student report")
    except (ValueError, TypeError, KeyError) as exc:
        raise ReportError("汇报模型返回了无效或无依据的结果") from exc
    counts = {activity: 0 for activity in sorted(ACTIVITIES)}
    for turn in turns:
        counts[turn["activity"]] += 1
    return {
        "studentReport": {**{key: student_report[key] for key in STUDENT_FIELDS},
                          "activityCounts": counts},
        "systemReview": {
            "turns": turns,
            "overHelpUserSeqs": [turn["userSeq"] for turn in turns
                                 if turn["receivedLevel"] > turn["helpLevel"]],
            "underHelpUserSeqs": [turn["userSeq"] for turn in turns
                                  if turn["receivedLevel"] < turn["helpLevel"]],
        },
    }


def report_for_session(session):
    model = getattr(settings, "AGENT_REPORT_MODEL", "Qwen3.8-Flash")
    provider = DeepSeekProvider(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=getattr(settings, "AGENT_GUARD_BASE_URL", settings.DEEPSEEK_BASE_URL),
        model=model,
        timeout=int(getattr(settings, "AGENT_REQUEST_TIMEOUT", 180)),
        extra_body=(thinking_off_body(model)
                    if getattr(settings, "AGENT_REPORT_DISABLE_THINKING", True) else None),
    )
    messages = list(session.messages.filter(role__in=("user", "assistant"))
                    .order_by("seq").values("seq", "role", "content"))
    return build_help_report(messages, provider)
