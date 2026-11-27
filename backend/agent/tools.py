# -*- coding: utf-8 -*-
"""AI 可调用的工具：只读工具 + 三级会话的写文件工具。

工具执行结果统一返回 JSON 字符串给模型；写操作额外生成 CodeChange 并通过
SSE 的 change 事件通知前端。
"""
import difflib
import json
import logging
import time
import uuid

from .levels import can_edit_code, tools_for_level
from .models import AgentToolCall, CodeChange, WorkspaceFile

logger = logging.getLogger(__name__)

MAX_READ_CHARS = 6000
MAX_TOOL_RESULT_CHARS = 8000


def _safe_path(path):
    """工作区路径校验：相对路径、无 ..、长度受限。"""
    path = str(path or "").strip()
    if not path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("非法的文件路径")
    if len(path) > 128:
        raise ValueError("文件路径过长")
    return path


def _json(data):
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 工具 schema（OpenAI function calling 格式）
# ---------------------------------------------------------------------------
TOOL_SPECS = {
    "list_files": {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "分页列出当前工作区里的文件路径与版本号。",
            "parameters": {"type": "object", "properties": {
                "offset": {"type": "integer", "description": "从第几个文件开始，默认 0"},
                "limit": {"type": "integer", "description": "返回数量，最多 40，默认 40"},
            }, "additionalProperties": False},
        },
    },
    "read_workspace": {
        "type": "function",
        "function": {
            "name": "read_workspace",
            "description": "按路径分段读取工作区文件；多文件工作区必须指定 path。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径，如 p1_a_plus_b.py"},
                    "offset": {"type": "integer", "description": "读取起点，默认 0"},
                },
                "additionalProperties": False,
            },
        },
    },
    "get_problem": {
        "type": "function",
        "function": {
            "name": "get_problem",
            "description": "获取本题的题面、语言、时限与公开样例（隐藏用例不可见）。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    "list_submissions": {
        "type": "function",
        "function": {
            "name": "list_submissions",
            "description": "查看我在本题的提交记录与判题结果（不含隐藏用例内容）。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    "run_sample_tests": {
        "type": "function",
        "function": {
            "name": "run_sample_tests",
            "description": "在隔离沙箱中运行当前代码，只跑公开样例，返回每个样例的通过情况。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要运行的文件，缺省为工作区第一个文件"},
                },
                "additionalProperties": False,
            },
        },
    },
    "write_file": {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将完整的新内容写入工作区文件（会覆盖原内容并记录修改）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件的完整新内容"},
                    "expected_revision": {
                        "type": "integer",
                        "description": "可选：读取到的版本号，版本不符时写入失败",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
}


def tool_specs_for(level, allowed_tools=None):
    """按级别返回工具 schema 列表；无 AI 级别返回空列表。"""
    from .levels import tools_for_level

    names = tools_for_level(level)
    if allowed_tools is not None:
        names = [name for name in names if name in allowed_tools]
    return [TOOL_SPECS[name] for name in names if name in TOOL_SPECS]


# ---------------------------------------------------------------------------
# 工作区辅助
# ---------------------------------------------------------------------------
def workspace_files(session):
    return WorkspaceFile.objects.filter(
        exam=session.exam, student=session.student, problem=session.problem
    ).order_by("path")


def ensure_workspace(session, path, content, expected_revision=None):
    """把前端当前代码同步到服务端工作区（仅在没有更新写入时）。"""
    path = _safe_path(path or "main.py")
    file = WorkspaceFile.objects.filter(
        exam=session.exam, student=session.student, problem=session.problem, path=path
    ).first()
    if file is None:
        return WorkspaceFile.objects.create(
            exam=session.exam, student=session.student, problem=session.problem,
            path=path, content=content or "", revision=1,
        )
    # 三级模式下 AI 可能已写入更新的内容，避免用旧的前端内容覆盖
    if expected_revision is not None and file.revision != expected_revision:
        return file
    if can_edit_code(session.level) and expected_revision is None:
        return file
    if file.content != (content or ""):
        file.content = content or ""
        file.revision += 1
        file.save(update_fields=["content", "revision", "updated_at"])
    return file


def _diff(before, after, path):
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    ))


# ---------------------------------------------------------------------------
# 工具执行
# ---------------------------------------------------------------------------
class ToolContext:
    """一次工具调用需要的上下文与事件回调。"""

    def __init__(self, session, emit):
        self.session = session
        self.emit = emit  # emit(event_name, data) -> None


def _tool_error(message):
    return _json({"ok": False, "error": message})


def _execute_list_files(ctx, arguments):
    try:
        offset = int(arguments.get("offset", 0))
        limit = int(arguments.get("limit", 40))
    except (TypeError, ValueError):
        return _tool_error("offset 和 limit 必须是整数")
    if offset < 0 or not 1 <= limit <= 40:
        return _tool_error("offset 必须非负，limit 必须在 1–40 之间")
    files = workspace_files(ctx.session)
    total = files.count()
    page = list(files[offset:offset + limit])
    return _json({
        "ok": True,
        "files": [{"path": f.path, "revision": f.revision} for f in page],
        "total": total,
        "nextOffset": offset + len(page) if offset + len(page) < total else None,
    })


def _execute_read_workspace(ctx, arguments):
    files = workspace_files(ctx.session)
    path = arguments.get("path")
    if not path and hasattr(ctx.session.problem, "project_bundle"):
        return _tool_error("工程题请先列出文件，再指定文件路径读取")
    if path:
        files = [f for f in files if f.path == path]
        if not files:
            return _tool_error(f"工作区没有文件 {path}")
    elif files.count() > 1:
        return _tool_error("多文件工作区请指定文件路径读取")
    try:
        offset = int(arguments.get("offset", 0))
    except (TypeError, ValueError):
        return _tool_error("offset 必须是非负整数")
    if offset < 0:
        return _tool_error("offset 必须是非负整数")
    payload = []
    for file in files:
        content = file.content or ""
        end = min(len(content), offset + MAX_READ_CHARS)
        payload.append({
            "path": file.path,
            "revision": file.revision,
            "content": content[offset:end],
            "offset": offset,
            "totalLength": len(content),
            "nextOffset": end if end < len(content) else None,
            "truncated": end < len(content),
        })
    return _json({"ok": True, "files": payload})


def _execute_get_problem(ctx, _arguments):
    problem = ctx.session.problem
    samples = problem.samples.filter(is_sample=True).order_by("id")
    return _json({
        "ok": True,
        "title": problem.title,
        "description": problem.description,
        "type": problem.type,
        "language": problem.language,
        "difficulty": problem.difficulty,
        "timeLimitMs": problem.time_limit_ms,
        "totalTestCount": problem.samples.count(),
        "samples": [
            {"name": s.name, "input": s.input_data, "expected": s.expected_output}
            for s in samples
        ],
    })


def _execute_list_submissions(ctx, _arguments):
    from exam.models import Submission

    submissions = (
        Submission.objects.filter(
            exam=ctx.session.exam, student=ctx.session.student,
            problem=ctx.session.problem,
        )
        .order_by("-id")[:10]
    )
    return _json({
        "ok": True,
        "submissions": [
            {
                "id": item.id,
                "status": item.status,
                "verdict": item.verdict,
                "score": item.score,
                "passedCount": item.passed_count,
                "totalCount": item.total_count,
                "created": item.created.isoformat(),
            }
            for item in submissions
        ],
    })


def _execute_run_sample_tests(ctx, arguments):
    """只跑公开样例；沙箱不可用时把原因返回给模型，而不是抛异常。"""
    from judge.languages import normalize_language
    from judge.sandbox import CaseSpec, SandboxError, run_sandbox

    problem = ctx.session.problem
    files = workspace_files(ctx.session)
    path = arguments.get("path")
    if path:
        files = [f for f in files if f.path == path]
    if not files:
        return _tool_error("工作区没有可运行的文件")

    samples = list(problem.samples.filter(is_sample=True).order_by("id"))
    if not samples:
        return _tool_error("本题没有公开样例")

    language = normalize_language(problem.language, problem.language)
    if language is None:
        return _tool_error(f"不支持的判题语言: {problem.language}")

    cases = [
        CaseSpec(
            index=index,
            name=sample.name,
            input_data=sample.input_data,
            expected_output=sample.expected_output,
            is_sample=True,
        )
        for index, sample in enumerate(samples, start=1)
    ]
    try:
        result = run_sandbox(
            language_key=language,
            code=files[0].content,
            cases=cases,
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
            output_limit_kb=problem.output_limit_kb,
        )
    except SandboxError as exc:
        return _tool_error(f"判题沙箱不可用: {exc}")
    except Exception as exc:  # noqa: BLE001 —— 工具错误要回给模型继续对话
        logger.exception("run_sample_tests 失败 session=%s", ctx.session.id)
        return _tool_error(f"运行样例失败: {exc}")

    cases_payload = [
        {
            "name": samples[int(case.get("index")) - 1].name
            if 0 < int(case.get("index") or 0) <= len(samples) else f"样例 {case.get('index')}",
            "verdict": case.get("verdict"),
            "timeMs": case.get("time_ms"),
            "outputExcerpt": case.get("output_excerpt", "")[:1000],
        }
        for case in result.cases
    ]
    passed = sum(1 for case in result.cases if case.get("verdict") == "accepted")
    return _json({
        "ok": True,
        "passed": passed,
        "total": len(result.cases),
        "compileOutput": (result.compile_output or "")[:2000],
        "cases": cases_payload,
    })


def _execute_write_file(ctx, arguments):
    """三级会话专用：写入工作区并记录 CodeChange。"""
    session = ctx.session
    if not can_edit_code(session.level):
        # 理论上工具列表已经过滤掉，这里是第二道防线
        return _tool_error("当前级别不允许修改代码")

    try:
        path = _safe_path(arguments.get("path"))
    except ValueError as exc:
        return _tool_error(str(exc))
    content = arguments.get("content")
    if not isinstance(content, str):
        return _tool_error("content 必须是字符串")
    expected = arguments.get("expected_revision")
    if expected is not None:
        try:
            expected = int(expected)
        except (TypeError, ValueError):
            return _tool_error("expected_revision 必须是整数")

    file = WorkspaceFile.objects.filter(
        exam=session.exam, student=session.student, problem=session.problem, path=path
    ).first()
    before = file.content if file else ""
    revision_before = file.revision if file else 0
    if expected is not None and file is not None and int(expected) != revision_before:
        return _tool_error(
            f"文件已被修改（当前版本 {revision_before}），请重新读取后再写入"
        )
    if before == content:
        return _json({"ok": True, "path": path, "changed": False,
                      "revision": revision_before})

    if file is None:
        file = WorkspaceFile.objects.create(
            exam=session.exam, student=session.student, problem=session.problem,
            path=path, content=content, revision=1,
        )
        revision_after = 1
    else:
        file.content = content
        file.revision += 1
        file.save(update_fields=["content", "revision", "updated_at"])
        revision_after = file.revision

    diff = _diff(before, content, path)
    change = CodeChange.objects.create(
        session=session,
        exam=session.exam,
        student=session.student,
        problem=session.problem,
        file_path=path,
        revision_before=revision_before,
        revision_after=revision_after,
        before_text=before,
        after_text=content,
        diff=diff,
    )
    ctx.emit("change", {
        "changeId": change.id,
        "path": path,
        "status": change.status,
        "revisionBefore": revision_before,
        "revisionAfter": revision_after,
        "additions": sum(1 for line in diff.splitlines()
                         if line.startswith("+") and not line.startswith("+++")),
        "deletions": sum(1 for line in diff.splitlines()
                         if line.startswith("-") and not line.startswith("---")),
        "diff": diff,
    })
    return _json({
        "ok": True,
        "path": path,
        "changed": True,
        "revision": revision_after,
        "changeId": change.id,
    })


_EXECUTORS = {
    "list_files": _execute_list_files,
    "read_workspace": _execute_read_workspace,
    "get_problem": _execute_get_problem,
    "list_submissions": _execute_list_submissions,
    "run_sample_tests": _execute_run_sample_tests,
    "write_file": _execute_write_file,
}


def execute_tool(name, arguments, context, session, call_id="", allowed_tools=None):
    """执行一次工具调用，返回 (ok, result_text)，并落 AgentToolCall 记录。"""
    started = time.monotonic()
    allowed = set(tools_for_level(session.level))
    if allowed_tools is not None:
        allowed.intersection_update(allowed_tools)
    if name not in allowed or name not in _EXECUTORS:
        result = _tool_error(f"当前级别不可用工具: {name}")
        ok = False
    else:
        try:
            result = _EXECUTORS[name](context, arguments or {})
            ok = bool(json.loads(result).get("ok", True))
        except Exception as exc:  # noqa: BLE001 —— 工具异常转成模型可读的错误
            logger.exception("工具执行失败 %s session=%s", name, session.id)
            result = _tool_error(f"工具执行失败: {exc}")
            ok = False
    duration_ms = int((time.monotonic() - started) * 1000)
    call_id = str(call_id or "").strip() or f"local-{uuid.uuid4().hex[:12]}"
    AgentToolCall.objects.create(
        session=session,
        call_id=call_id[:64],
        name=name,
        arguments=arguments or {},
        ok=ok,
        result_excerpt=str(result)[:2000],
        duration_ms=duration_ms,
    )
    return ok, result[:MAX_TOOL_RESULT_CHARS]
