# -*- coding: utf-8 -*-
"""Docker 判题沙箱：一次判题启动一个临时容器，跑完即销毁。"""

import io
import json
import os
import tarfile
from dataclasses import dataclass

from django.conf import settings

from judge.languages import LANGUAGES, language_payload


class SandboxError(Exception):
    """沙箱不可用 / 判题容器异常。"""


@dataclass
class CaseSpec:
    index: int
    name: str
    input_data: str
    expected_output: str
    is_sample: bool


@dataclass
class SandboxResult:
    compile_output: str
    cases: list
    compile_ok: bool = True


_client = None


def _docker_client():
    global _client
    if _client is not None:
        return _client
    if os.name == "nt" and not os.environ.get("DOCKER_HOST"):
        # Docker Desktop 在 Windows 上使用命名管道
        os.environ["DOCKER_HOST"] = "npipe:////./pipe/docker_engine"
    try:
        import docker
    except ImportError as exc:  # pragma: no cover - 部署环境已装依赖
        raise SandboxError("缺少 docker Python 依赖") from exc
    try:
        _client = docker.from_env()
    except Exception as exc:
        raise SandboxError(f"无法连接 Docker: {exc}") from exc
    return _client


def _add_file(tar, name, data):
    if name.startswith("/") or ".." in name.split("/"):
        raise SandboxError(f"非法文件名: {name}")
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def _build_tar(language_key, code, cases, time_limit_ms, memory_limit_mb,
               output_limit_kb):
    config = LANGUAGES[language_key]
    manifest_cases = []
    for case in cases:
        manifest_cases.append({
            "index": case.index,
            "input": f"cases/{case.index}.in",
            "expected": f"cases/{case.index}.out",
            "is_sample": bool(case.is_sample),
        })
    manifest = {
        **language_payload(config, memory_limit_mb),
        "time_limit_ms": time_limit_ms,
        "memory_limit_mb": memory_limit_mb,
        "output_limit_kb": output_limit_kb,
        "cases": manifest_cases,
    }

    runner_path = os.path.join(os.path.dirname(__file__), "assets", "runner.py")
    with open(runner_path, "rb") as handle:
        runner_source = handle.read()

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        _add_file(tar, "manifest.json",
                  json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
        _add_file(tar, config.source, code.encode("utf-8"))
        _add_file(tar, "runner.py", runner_source)
        cases_dir = tarfile.TarInfo("cases")
        cases_dir.type = tarfile.DIRTYPE
        cases_dir.mode = 0o777
        tar.addfile(cases_dir)
        for case in cases:
            _add_file(tar, f"cases/{case.index}.in", case.input_data.encode("utf-8"))
            _add_file(tar, f"cases/{case.index}.out", case.expected_output.encode("utf-8"))
    return buffer.getvalue()


def _parse_runner_output(raw):
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    for line in reversed([line for line in text.splitlines() if line.strip()]):
        try:
            return json.loads(line)
        except ValueError:
            continue
    raise SandboxError(f"判题 runner 未返回 JSON：{text[-500:]}")


def _wall_limit(time_limit_ms, case_count, needs_compile):
    # 编译本身最多 30 秒，容器还需要时间启动和返回诊断。
    overhead = 40 if needs_compile else 20
    budget = (time_limit_ms / 1000.0) * case_count * 2 + overhead
    return min(float(settings.JUDGE_WALL_TIME_LIMIT), budget)


def run_sandbox(language_key, code, cases, time_limit_ms, memory_limit_mb,
                output_limit_kb, *, compile_only=False):
    """
    在一次性 Docker 容器中编译并逐用例运行。

    返回 SandboxResult；Docker 不可用等系统问题抛 SandboxError。
    """
    if language_key not in LANGUAGES:
        raise SandboxError(f"不支持的判题语言: {language_key}")
    if not cases and not compile_only:
        raise SandboxError("题目没有测试用例")

    config = LANGUAGES[language_key]
    archive = _build_tar(
        language_key, code, cases, time_limit_ms, memory_limit_mb, output_limit_kb
    )
    image = settings.JUDGE_IMAGE
    client = _docker_client()

    try:
        client.images.get(image)
    except Exception as exc:
        raise SandboxError(f"判题镜像 {image} 不存在，请先构建: {exc}") from exc

    # Docker 的 put_archive 不允许写入只读根文件系统，即使目标路径是 tmpfs。
    # 因此用一次性命名卷承载代码与用例（对 runner 只读），
    # 编译产物与输出写到 tmpfs /tmp（容器内可写），根文件系统保持只读。
    try:
        volume = client.volumes.create()
    except Exception as exc:
        raise SandboxError(f"创建判题数据卷失败: {exc}") from exc

    # 等待 manifest 写入后再启动 runner，避免 start/put_archive 的竞态
    command = [
        "/bin/sh", "-c",
        "while [ ! -f /sandbox/manifest.json ]; do sleep 0.05; done; "
        "exec python3 /sandbox/runner.py",
    ]
    try:
        container = client.containers.create(
            image=image,
            command=command,
            working_dir="/sandbox",
            network_disabled=True,
            mem_limit=f"{memory_limit_mb + 128}m",
            nano_cpus=1_000_000_000,
            pids_limit=64,
            read_only=True,
            volumes={volume.name: {"bind": "/sandbox", "mode": "rw"}},
            tmpfs={"/tmp": "rw,exec,size=128m,mode=1777"},
            user="65534:65534",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            init=True,
            environment={"PYTHONDONTWRITEBYTECODE": "1", "HOME": "/tmp"},
            detach=True,
        )
    except SandboxError:
        try:
            volume.remove(force=True)
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            volume.remove(force=True)
        except Exception:
            pass
        raise SandboxError(f"创建判题容器失败: {exc}") from exc

    try:
        try:
            container.start()
            container.put_archive("/sandbox", archive)
            wait_result = container.wait(
                timeout=_wall_limit(time_limit_ms, len(cases), bool(config.compile))
            )
            exit_code = int((wait_result or {}).get("StatusCode") or 0)
        except Exception as exc:
            try:
                container.kill()
            except Exception:
                pass
            raise SandboxError(f"判题容器执行失败或超时: {exc}") from exc

        stdout = container.logs(stdout=True, stderr=False)
        try:
            payload = _parse_runner_output(stdout)
        except SandboxError:
            # 容器被内核 OOM killer 杀掉时 runner 来不及输出 JSON
            if exit_code == 137 and cases:
                return SandboxResult(
                    compile_output="",
                    cases=[{
                        "index": case.index,
                        "verdict": "memory_limit_exceeded",
                        "time_ms": 0,
                        "memory_kb": 0,
                        "output_excerpt": "",
                        "error_excerpt": "进程被内存限制终止",
                    } for case in cases],
                )
            raise
        if payload.get("error"):
            raise SandboxError(str(payload["error"]))

        results = payload.get("cases") or []
        if len(results) != len(cases):
            raise SandboxError(
                f"判题结果数量不符：期望 {len(cases)}，实际 {len(results)}"
            )
        compile_info = payload.get("compile") or {}
        return SandboxResult(
            compile_output=str(compile_info.get("output") or ""),
            cases=results,
            compile_ok=bool(compile_info.get("ok")),
        )
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass
        try:
            volume.remove(force=True)
        except Exception:
            pass
