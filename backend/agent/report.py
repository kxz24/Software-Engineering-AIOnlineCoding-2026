"""Experimental, evidence-linked description of the help a student requested."""

import json
import logging
import re

from django.conf import settings

from .policy import asks_for_check_targets_only
from .providers import DeepSeekProvider, ProviderError, thinking_off_body


class ReportError(Exception):
    pass


logger = logging.getLogger(__name__)


ACTIVITIES = {"knowledge", "algorithm", "coding", "debugging", "other"}
STUDENT_FIELDS = ("narrative",)


def _student_report_text(value):
    """Remove message sequence numbers that models sometimes mistake for turn counts."""
    return re.sub(
        r"第\s*\d+(?:\s*[、，,]\s*\d+)*\s*次(?:提问|请求|对话)",
        "相关提问", value,
    )

REPORT_RULES = """你是考试对话的过程分析员。输入是 dialogue 与 observedWork；只根据输入返回 JSON，不要 Markdown。
结构：{"turns":[{"userSeq":整数,"activity":"knowledge|algorithm|coding|debugging|other",
"helpLevel":0到4的整数,"receivedLevel":0到4的整数,"evidence":"原话中的短摘录"}],
"studentReport":{"narrative":"面向学生的连贯过程叙述，约两到四段"}}。
每条学生提问都要有一项；userSeq 必须来自输入中的学生消息。
dialogue 中 requestedAction 是考生该轮显式选择的“只回答/运行/修改”授权，
不等于助教实际运行或修改。实际动作只以 observedWork 的服务器记录为准。
helpLevel 是学生请求的深度，receivedLevel 是助教实际给予的深度；
0=无帮助，1=概念或思路，2=算法设计或调试方向，
3=某个明确局部实现/修错，4=完整解法。不得把助教主动给得过多算成学生索取；
新术语的定义、小数字例子及其与当前题目操作的联系仍属 1；
询问多个解题组件各自的职责、为何配合，属于算法设计 2。
只问应检查哪些对象或情况，获得相应对象列表时，也属于算法思路帮助 2；
不要仅因为回答没有进一步推导各情况的判定条件，就判为帮助不足。
不能仅因回答出现题目操作或数据结构名称，就把概念解释判为 2。
只问错误原因或位置而未索要改法时，helpLevel 为 2，即使提到了具体报错或变量；
只有明确请求怎么改、怎么修时，局部修错的 helpLevel 才是 3。
evidence 必须逐字摘自对应 userSeq 的学生提问，不能从助教回答中摘取。
studentReport.narrative 写成连贯的过程观察：学生主要问了什么、如何追问、
助教实际回答了什么或做了什么，哪些尝试没有完成。按真实主题与因果关系组织，
不要按固定栏目逐项罗列，也不要重复机械统计；必要时可自然提及提问次数。
区分“请求”“尝试”“实际写回”“验证结果”，不能把授权当成已完成工作。
只写有证据的学习活动；没有证据时简短说明无法判断学生独立完成的部分。
不使用“第几次提问”等轮次编号，
也不暴露内部消息序号 userSeq 或 seq。
不要写模型、提示词、审查、规则、系统是否合规，也不要比较 helpLevel 与 receivedLevel；
这些信息只属于内部审查。没有代码或后续验证时，不得推断哪些部分由学生独立完成。
不能据此断言学生已经学会、存在作弊或给出最终成绩。"""

REPORT_RULES += """
observedWork.harnessJobs 是逐轮工程任务的服务端记录。status=failed 表示该轮没有应用文件修改；
即使 commandSamples 显示沙箱里执行过编辑，failed/partial 任务的临时改动也没有写回学生工作区。
只有 observedWork.aiChanges 才能证明工作区实际持久化了 AI 修改。
commandSamples 只能证明命令被执行以及截取到的输出，不能仅凭命令文字或返回码推断测试通过。
若某轮没有助教回复，但有工程命令记录，应在 narrative 中如实区分“尝试运行”和“已完成修改”。
activity=coding 用于直接请求编写、实现或修改源码文件，即使涉及算法或处理器设计；
activity=algorithm 仅用于询问方案、原理、复杂度或设计选择而没有要求直接写入源码。
任务失败不改变学生当初请求的活动类别。
observedWork.submissions 的 verdict 是整道题或整份工程的汇总结果；visibleCases 只包含可公开的评分项。
叙述验证结果时，应优先区分各公开评分项的通过情况与总体结果。总体 partial 不能单独证明
学生当前修改的文件有缺陷，也不能证明未通过的评分项由谁编写或为何失败。
如果没有对应评分项或运行输出的证据，不要猜测某个文件可能有错误；可以如实说明原因尚不明确。
评分项未通过只说明该评分项未达到要求，不等于学生已尝试或独立完成过对应任务。
例如学生只改了模块甲，公开评分项甲通过、乙未通过：应说“甲已通过，乙未通过；对话没有
乙的实现或求助记录”，不能说“学生在乙遇到了困难”“学生的甲仍可能有问题”。
学生说“我写了文件”只能记录为学生自述；除非有可核实的人工编辑来源，不要改写成
“学生自行编写/独立完成”。
如果助教解释了工作区文件，可以说“助教解释了工作区中的文件”；不要把文件说成
学生在对话里贴出的代码，也不要推测文件的作者或来源。
"""


def _work_summary(observed_work):
    changes = observed_work.get("aiChanges") or []
    runs = int(observed_work.get("successfulRuns") or 0)
    harness_runs = int(observed_work.get("harnessRunRequests") or 0)
    harness_steps = int(observed_work.get("harnessSteps") or 0)
    failed_jobs = sum(job.get("status") in ("failed", "partial")
                      for job in observed_work.get("harnessJobs") or [])
    submissions = observed_work.get("submissions") or []
    parts = []
    if changes:
        paths = sorted({item["path"] for item in changes})
        reverted = sum(item.get("status") == "reverted" for item in changes)
        parts.append(f"记录到 AI 修改 {len(changes)} 次，涉及文件：{'、'.join(paths[:12])}"
                     + (f"；其中 {reverted} 次已撤销" if reverted else ""))
    else:
        parts.append("没有记录到 AI 文件修改")
    parts.append(f"独立运行验证 {runs} 次" if runs else "没有记录到独立的运行验证请求")
    if harness_steps:
        parts.append(f"工程助手共执行 {harness_steps} 步操作")
        parts.append("编辑任务中的构建与测试结果以逐轮命令输出为准")
    if failed_jobs:
        parts.append(f"工程任务失败或未完成 {failed_jobs} 次，这些轮次没有应用文件修改")
    if harness_runs:
        parts.append(f"工程运行请求 {harness_runs} 次；完成请求不代表构建成功")
    if submissions:
        latest = submissions[0]
        parts.append(f"正式提交 {len(submissions)} 次，最近一次结果为 {latest['verdict']}")
    else:
        parts.append("没有记录到正式提交")
    return "；".join(parts) + "。平台未记录每次人工编辑的来源，不能据此判断学生独立写了哪些代码。"


def build_help_report(messages, provider, observed_work=None):
    """Return a validated draft report; never infer mastery or a score."""
    observed_work = observed_work or {}
    dialogue = [
        {"seq": int(item["seq"]), "role": item["role"],
         "content": str(item.get("content") or ""),
         **({"requestedAction": item.get("requested_action") or "answer"}
            if item["role"] == "user" else {})}
        for item in messages if item["role"] in ("user", "assistant")
    ]
    user_seqs = {item["seq"] for item in dialogue if item["role"] == "user"}
    if not user_seqs:
        raise ReportError("会话没有学生提问")
    payload = [
        {"role": "system", "content": REPORT_RULES},
        {"role": "user", "content": json.dumps({
            "dialogue": dialogue, "observedWork": observed_work,
        }, ensure_ascii=False)},
    ]
    parts = []
    try:
        for event in provider.stream(payload, [], max_tokens=8192):
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
        logger.warning("报告校验失败: %s; raw_len=%d", exc, len(raw))
        raise ReportError("汇报模型返回了无效或无依据的结果") from exc
    counts = {activity: 0 for activity in sorted(ACTIVITIES)}
    replies = {}
    current_user = None
    for item in dialogue:
        if item["role"] == "user":
            current_user = item["seq"]
        elif current_user is not None and item["content"].strip():
            replies[current_user] = item["content"]
    for turn in turns:
        seq = turn["userSeq"]
        if (asks_for_check_targets_only(user_text[seq])
                and replies.get(seq, "").startswith("可以先检查这些对象：\n- ")):
            turn["receivedLevel"] = max(turn["receivedLevel"],
                                        min(turn["helpLevel"], 2))
        counts[turn["activity"]] += 1
    return {
        "studentReport": {"narrative": _student_report_text(
            student_report["narrative"]), "activityCounts": counts},
        "systemReview": {
            "turns": turns,
            "observedWork": observed_work,
            "overHelpUserSeqs": [turn["userSeq"] for turn in turns
                                 if turn["receivedLevel"] > turn["helpLevel"]],
            "underHelpUserSeqs": [turn["userSeq"] for turn in turns
                                  if turn["receivedLevel"] < turn["helpLevel"]],
        },
    }


def build_help_report_with_retry(messages, provider, observed_work=None):
    """Retry one invalid draft while keeping the evidence checks strict."""
    for attempt in range(2):
        try:
            return build_help_report(messages, provider,
                                     observed_work=observed_work)
        except ReportError:
            if attempt:
                raise
            logger.warning("报告首稿无效，重试一次")


def _submission_evidence(submission):
    """Give the report only the same named grading items visible to a student."""
    return {
        "verdict": submission.verdict,
        "passedCount": submission.passed_count,
        "totalCount": submission.total_count,
        "visibleCases": [
            {"name": case.name, "verdict": case.verdict}
            for case in submission.cases.all() if case.is_sample
        ][:30],
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
                    .order_by("seq").values("seq", "role", "content", "requested_action"))
    changes = list(session.code_changes.order_by("created").values("file_path", "status")[:200])
    from exam.models import Submission
    submission_records = list(Submission.objects.filter(
        exam=session.exam, student=session.student, problem=session.problem,
        created__gte=session.created,
    ).order_by("-created").prefetch_related("cases")[:20])
    submissions = [_submission_evidence(submission)
                   for submission in submission_records]
    harness_jobs = []
    for job in session.harness_jobs.order_by("created")[:30]:
        commands = list(session.tool_calls.filter(
            call_id__startswith=f"harness-{job.id}-",
            name="harness_command",
        ).order_by("-created").values("arguments", "ok", "result_excerpt")[:5])
        harness_jobs.append({
            "userSeq": job.user_message.seq, "action": job.action,
            "scope": job.scope, "targetPath": job.target_path,
            "status": job.status, "steps": job.steps,
            "result": job.result[:600],
            "commandSamples": [
                {"command": str(item["arguments"].get("command") or "")[:250],
                 "ok": item["ok"],
                 "output": item["result_excerpt"][:240]}
                for item in reversed(commands)
            ],
        })
    observed_work = {
        "aiChanges": [{"path": item["file_path"], "status": item["status"]}
                      for item in changes],
        "successfulRuns": session.tool_calls.filter(
            name="run_sample_tests", ok=True).count(),
        "harnessRunRequests": session.harness_jobs.filter(
            action="run", status="done").count(),
        "harnessSteps": sum(session.harness_jobs.values_list("steps", flat=True)),
        "harnessJobs": harness_jobs,
        "submissions": submissions,
    }
    return build_help_report_with_retry(messages, provider,
                                        observed_work=observed_work)
