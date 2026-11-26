"""Run mini-SWE-agent against public project files in an isolated container.

This module is imported only by the dedicated agent Celery worker. The model
client stays outside the execution container; no private grader files or API
credentials are copied into it.
"""

import io
import os
import subprocess
import tarfile
import tempfile
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import F

from problem.project_package import safe_name

from . import service, tools
from .harness_scope import (ScopeReviewError, configured_scope_provider,
                            review_edit_scope)
from .models import AgentHarnessJob, AgentMessage, AgentToolCall, WorkspaceFile


# The gateway model is not in LiteLLM's public price map. Avoid a remote GitHub
# fetch during worker startup; usage is recorded from the API response instead.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")


SYSTEM_TEMPLATE = """You are a coding assistant in an exam workspace.
Each response must contain exactly one bash command in a ```mswea_bash_command block.
Keep the explanation before the command brief. Do not browse the network or
inspect paths outside /workspace. Never attempt to access hidden grader files.
"""

INSTANCE_TEMPLATE = """Student request: {{task}}

The workspace contains only the student's public project files. Follow only
the current request. Do not independently complete other parts of the task.
Read relevant files before editing. For a run-only request, execute the requested
checks but do not edit files. For an edit request, change only the authorized
scope and perform only necessary verification. The platform will reject changes
outside that scope. Do not create files outside /workspace except temporary
build files in /tmp. There is no network access.

When finished, use one command that prints COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
on its first line and a concise, factual user-facing summary on later lines.
Do not claim tests passed unless you observed their output.
"""


def _base_url():
    base = settings.DEEPSEEK_BASE_URL.rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def _public_snapshot(session):
    prefix = f"p{session.problem_id}/"
    public = session.problem.project_bundle.public_files
    files = {item.path[len(prefix):]: item for item in WorkspaceFile.objects.filter(
        exam=session.exam, student=session.student, problem=session.problem,
        path__startswith=prefix,
    ) if item.path[len(prefix):] in public}
    return {name: (files[name].content, files[name].revision)
            if name in files else (content, 0)
            for name, content in public.items()}


def _stage_archive(snapshot):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, (content, _) in snapshot.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(safe_name(name))
            info.size = len(data)
            info.mode = 0o777  # files are writable by the unprivileged container user
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _changed_public_files(archive_bytes, snapshot, required_names=None):
    if len(archive_bytes) > 70 * 1024 * 1024:
        raise RuntimeError("工程工作区输出过大")
    found = {}
    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
        for member in archive:
            name = member.name.removeprefix("./")
            if name not in snapshot:
                continue
            if not member.isfile() or member.size > 1024 * 1024:
                raise RuntimeError(f"公开文件已变为无效类型：{name}")
            found[name] = archive.extractfile(member).read().decode("utf-8")
    required = set(snapshot) if required_names is None else set(required_names)
    if not required <= set(found):
        raise RuntimeError("工程工作区缺少公开文件")
    return {name: content for name, content in found.items()
            if content != snapshot[name][0]}


def _model_usage(messages):
    input_tokens = output_tokens = cache_hits = 0
    for message in messages:
        if message.get("role") != "assistant":
            continue
        usage = (message.get("extra") or {}).get("response", {}).get("usage") or {}
        input_tokens += int(usage.get("prompt_tokens") or 0)
        output_tokens += int(usage.get("completion_tokens") or 0)
        cache_hits += int((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
    return input_tokens, output_tokens, cache_hits


def _final_text(outcome, changes, steps):
    summary = str(outcome.get("submission") or "").strip()
    if not summary:
        summary = ("已按本轮请求完成操作。" if outcome.get("exit_status") == "Submitted"
                   else "本轮未能自行提交完成结果；沙箱中的改动未应用到工作区。")
    if changes:
        summary += "\n\n已更新文件：" + "、".join(sorted(changes))
    return summary[:3000]


def execute_project_job(job):
    """Run one explicit student turn and commit only authorized public edits."""
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments.docker import DockerEnvironment
    from minisweagent.models.litellm_model import LitellmModel

    session = job.session
    bundle = session.problem.project_bundle
    snapshot = _public_snapshot(session)
    prefix = f"p{session.problem_id}/"
    target = job.target_path[len(prefix):] if job.target_path.startswith(prefix) else ""
    if job.action == "edit" and job.scope == "file" and target not in snapshot:
        raise RuntimeError("本轮目标文件不在公开工作区")
    image = bundle.prepared_image or settings.PROJECT_JUDGE_RUNTIMES.get(bundle.runtime)
    if not image:
        raise RuntimeError("工程题执行环境尚未准备好")
    key = settings.DEEPSEEK_API_KEY
    if not key:
        raise RuntimeError("尚未配置模型密钥")

    with tempfile.TemporaryDirectory(prefix="exam-agent-"):
        environment = DockerEnvironment(
            image=image, cwd="/workspace", timeout=120, container_timeout="20m",
            run_args=["--rm", "--network", "none", "--memory", "768m",
                      "--cpus", "1", "--pids-limit", "64", "--read-only",
                      "--tmpfs", "/workspace:rw,exec,size=64m,mode=1777",
                      "--tmpfs", "/tmp:rw,exec,size=384m,mode=1777",
                      "--user", "65534:65534", "--cap-drop", "ALL",
                      "--security-opt", "no-new-privileges"],
        )
        try:
            subprocess.run(["docker", "exec", "-i", environment.container_id,
                            "tar", "-xf", "-", "-C", "/workspace"],
                           input=_stage_archive(snapshot), check=True,
                           capture_output=True, timeout=30)
            model = LitellmModel(
                model_name="openai/" + getattr(settings, "AGENT_HARNESS_MODEL", settings.AGENT_MODEL),
                model_kwargs={"api_key": key, "api_base": _base_url(),
                              "max_tokens": 2048, "drop_params": True,
                              "extra_body": {"thinking": {"type": "disabled"}}},
                cost_tracking="ignore_errors",
            )
            agent = DefaultAgent(
                model, environment, system_template=SYSTEM_TEMPLATE,
                instance_template=INSTANCE_TEMPLATE,
                step_limit=int(getattr(settings, "AGENT_HARNESS_MAX_STEPS", 20)),
                cost_limit=0,
                wall_time_limit_seconds=int(getattr(settings, "AGENT_HARNESS_WALL_SECONDS", 600)),
            )
            original_execute = environment.execute

            def tracked_execute(action, *args, **kwargs):
                if AgentHarnessJob.objects.filter(pk=job.pk).values_list(
                        "status", flat=True).first() == AgentHarnessJob.STATUS_CANCELLED:
                    raise RuntimeError("任务已由考生停止")
                command = str(action.get("command") or "")
                try:
                    output = original_execute(action, *args, **kwargs)
                except Exception:
                    AgentHarnessJob.objects.filter(pk=job.pk).update(steps=F("steps") + 1)
                    raise
                AgentToolCall.objects.create(
                    session=session, call_id=f"harness-{job.pk}-{uuid4().hex}"[:64],
                    name="harness_command", arguments={"command": command[:2000]},
                    ok=output.get("returncode") == 0,
                    result_excerpt=str(output.get("output") or "")[:2000],
                )
                AgentHarnessJob.objects.filter(pk=job.pk).update(steps=F("steps") + 1)
                return output

            environment.execute = tracked_execute
            scope_note = (f"Only edit {target}." if job.scope == "file"
                          else "You may edit the public project files relevant to this request.")
            task = (f"{job.user_message.content}\n\nAuthorized action: {job.action}. "
                    + (scope_note if job.action == "edit" else
                       "Run only the checks the student requested; do not edit files."))
            try:
                outcome = agent.run(task)
            finally:
                input_tokens, output_tokens, cached = _model_usage(agent.messages)
                AgentHarnessJob.objects.filter(pk=job.pk).update(
                    input_tokens=input_tokens, output_tokens=output_tokens)
                service._add_usage(session, {"input": input_tokens,
                                             "output": output_tokens,
                                             "cache_hit": cached,
                                             "cache_miss": max(0, input_tokens - cached)})
            if job.action == "run":
                changes = {}
            else:
                exported = subprocess.run(
                    ["docker", "exec", environment.container_id,
                     "tar", "-cf", "-", "-C", "/workspace", "."],
                    check=True, capture_output=True, timeout=30).stdout
                required = {target} if job.scope == "file" else None
                changes = _changed_public_files(exported, snapshot,
                                                required_names=required)
        finally:
            environment.cleanup()

        if job.action == "run":
            changes = {}
        elif job.scope == "file" and set(changes) - {target}:
            raise RuntimeError("Agent 修改了本轮授权范围外的文件；改动未应用")
        if outcome.get("exit_status") != "Submitted":
            changes = {}
        if changes:
            allowed, feedback, review_usage = review_edit_scope(
                job.user_message.content, changes, snapshot,
                configured_scope_provider(),
            )
            service._add_usage(session, {
                "input": review_usage["inputTokens"],
                "output": review_usage["outputTokens"],
                "cache_hit": review_usage["cacheHitTokens"],
                "cache_miss": review_usage["cacheMissTokens"],
            })
            input_tokens += review_usage["inputTokens"]
            output_tokens += review_usage["outputTokens"]
            AgentHarnessJob.objects.filter(pk=job.pk).update(
                input_tokens=input_tokens, output_tokens=output_tokens)
            AgentToolCall.objects.create(
                session=session,
                call_id=f"harness-{job.pk}-{uuid4().hex}"[:64],
                name="harness_scope_review",
                arguments={"changedPaths": sorted(changes)},
                ok=allowed, result_excerpt=feedback[:500],
            )
            if not allowed:
                raise ScopeReviewError("改动范围审查未通过，文件未应用")

        with transaction.atomic():
            current_job = AgentHarnessJob.objects.select_for_update().get(pk=job.pk)
            if current_job.status == AgentHarnessJob.STATUS_CANCELLED:
                raise RuntimeError("任务已由考生停止")
            if changes:
                locked = {file.path: file for file in WorkspaceFile.objects.select_for_update().filter(
                    exam=session.exam, student=session.student, problem=session.problem,
                    path__in=[prefix + name for name in changes],
                )}
                for name in changes:
                    expected = snapshot[name][1]
                    current = locked.get(prefix + name)
                    if current is None or current.revision != expected:
                        raise RuntimeError("工作区在 Agent 运行期间已变化；改动未应用")
                context = tools.ToolContext(session, lambda *_: None)
                for name, new_content in changes.items():
                    ok, message = tools.execute_tool(
                        "write_file", {"path": prefix + name,
                                       "content": new_content,
                                       "expected_revision": snapshot[name][1]},
                        context, session, allowed_tools={"write_file"},
                    )
                    if not ok:
                        raise RuntimeError(f"写回失败：{message[:200]}")
            text = _final_text(outcome, changes, job.steps)
            service._add_message(
                session, AgentMessage.ROLE_ASSISTANT, content=text,
                usage={"inputTokens": input_tokens, "outputTokens": output_tokens,
                       "usage": {"prompt_tokens": input_tokens,
                                 "completion_tokens": output_tokens}},
                finish_reason=outcome.get("exit_status", "")[:24],
            )
            job.steps = AgentHarnessJob.objects.get(pk=job.pk).steps
            job.input_tokens = input_tokens
            job.output_tokens = output_tokens
            job.result = text
            job.status = (AgentHarnessJob.STATUS_DONE
                          if outcome.get("exit_status") == "Submitted"
                          else AgentHarnessJob.STATUS_PARTIAL)
            job.save(update_fields=["steps", "input_tokens", "output_tokens",
                                    "result", "status", "updated"])
