"""两端共享本地网络；评测进程和学生进程各自在无特权容器中运行。"""

import io
import json
import logging
import os
import tarfile
import time

from django.conf import settings

from judge.sandbox import SandboxError, SandboxResult, _docker_client, _parse_runner_output

GRADER = 65533
STUDENT = 65534
ASSETS = os.path.join(os.path.dirname(__file__), "assets")
logger = logging.getLogger(__name__)


def _put(container, entries):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        for name, data, uid, mode in entries:
            info = tarfile.TarInfo(name)
            info.mode = mode
            info.uid = uid
            info.gid = STUDENT
            if data is None:
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    if not container.put_archive("/sandbox", archive.getvalue()):
        raise SandboxError("无法写入工程评测目录")


def _asset(name):
    with open(os.path.join(ASSETS, name), "rb") as handle:
        return handle.read()


def _stage(student, files, runner, script):
    entries = [
        ("grader", None, GRADER, 0o700),
        ("exchange", None, GRADER, 0o2750),
        ("student", None, STUDENT, 0o755),
    ]
    directories = {"student"}
    for name, data in sorted(files.items()):
        parts = name.split("/")
        for size in range(1, len(parts)):
            folder = "student/" + "/".join(parts[:size])
            if folder not in directories:
                entries.append((folder, None, STUDENT, 0o755))
                directories.add(folder)
        entries.append(("student/" + name, data, STUDENT, 0o644))
    entries.extend([
        ("ftp_student.py", _asset("ftp_student.py"), 0, 0o644),
        (f"grader/{runner}", _asset(runner), GRADER, 0o600),
    ])
    if script is not None:
        entries.extend([
            ("exchange/work", None, GRADER, 0o2770),
            ("grader/grade.py", script.encode("utf-8"), GRADER, 0o600),
        ])
    _put(student, entries)


def _execute(student, command):
    status, output = student.exec_run(
        ["python3", "/sandbox/ftp_student.py", json.dumps(command)], user=f"{STUDENT}:{STUDENT}",
    )
    if status != 0:
        raise SandboxError("学生程序运行入口异常")
    return _parse_runner_output(output)


def run_ftp_sandbox(files, memory_limit_mb):
    return _run_project(files, memory_limit_mb, runner="ftp_runner.py", script=None, timeout=150)


def run_script_sandbox(files, script, memory_limit_mb):
    return _run_project(files, memory_limit_mb, runner="project_runner.py", script=script, timeout=65)


def _run_project(files, memory_limit_mb, *, runner, script, timeout):
    client = _docker_client()
    volume = client.volumes.create()
    containers = []
    options = {
        "image": settings.JUDGE_IMAGE,
        "working_dir": "/sandbox",
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges"],
        "init": True,
        "detach": True,
        "pids_limit": 64,
        "volumes": {volume.name: {"bind": "/sandbox", "mode": "rw"}},
        "tmpfs": {"/tmp": "rw,exec,size=64m,mode=1777"},
        "environment": {"PYTHONDONTWRITEBYTECODE": "1", "HOME": "/tmp"},
    }
    try:
        student = client.containers.create(
            command=["sleep", "infinity"], network_mode="none",
            user=f"{STUDENT}:{STUDENT}", nano_cpus=1_000_000_000,
            mem_limit=f"{memory_limit_mb + 128}m", **options,
        )
        containers.append(student)
        student.start()
        _stage(student, files, runner, script)
        grader = client.containers.create(
            command=["python3", f"/sandbox/grader/{runner}"],
            network_mode=f"container:{student.id}", user=f"{GRADER}:{STUDENT}",
            nano_cpus=1_000_000_000, mem_limit="192m", **options,
        )
        containers.append(grader)
        grader.start()
        handled = 0
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            lines = grader.logs(stdout=True, stderr=False).splitlines()
            for line in lines[handled:]:
                message = json.loads(line)
                if "cases" in message:
                    return SandboxResult(
                        compile_output=message.get("compile", {}).get("output", ""), cases=message["cases"],
                    )
                request_id = message.pop("request")
                reply = _execute(student, message)
                _put(grader, [(f"grader/response-{request_id}.json", json.dumps(reply).encode(), GRADER, 0o600)])
                handled += 1
            grader.reload()
            if grader.status in {"exited", "dead"}:
                if len(grader.logs(stdout=True, stderr=False).splitlines()) == handled:
                    raise SandboxError("工程评测进程提前退出")
            time.sleep(0.1)
        raise SandboxError("工程评测超过总时限")
    finally:
        for container in reversed(containers):
            try:
                container.remove(force=True)
            except Exception:
                logger.exception("清理工程评测容器失败")
        try:
            volume.remove(force=True)
        except Exception:
            logger.exception("清理工程评测数据卷失败")
