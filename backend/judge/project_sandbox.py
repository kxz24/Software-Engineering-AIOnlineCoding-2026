"""Docker wrapper for teacher-defined multi-file project graders."""

import io
import json
import os
import tarfile
import zipfile

from django.conf import settings

from .sandbox import SandboxError, _add_file, _docker_client, _parse_runner_output


def _runtime_package(raw):
    """Keep build inputs and the reference solution out of grading containers."""
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(output, "w") as target:
        for info in source.infolist():
            if (info.filename.startswith("private/selfcheck/") or
                    info.filename.startswith("private/build/") or
                    info.filename == "private/Dockerfile"):
                continue
            target.writestr(info, source.read(info))
    return output.getvalue()


def run_project_sandbox(bundle, files):
    image = getattr(bundle, "prepared_image", "") or settings.PROJECT_JUDGE_RUNTIMES.get(bundle.runtime)
    if not image:
        raise SandboxError("工程题运行环境未配置")
    with open(os.path.join(os.path.dirname(__file__), "assets", "project_runner.py"), "rb") as handle:
        runner = handle.read()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        _add_file(archive, "package.zip", _runtime_package(bytes(bundle.archive)))
        _add_file(archive, "submission.json", json.dumps({"files": files}, ensure_ascii=False).encode())
        _add_file(archive, "project_runner.py", runner)

    client = _docker_client()
    try:
        client.images.get(image)
    except Exception as exc:
        raise SandboxError(f"工程题镜像 {image} 不存在，请先构建") from exc
    volume = client.volumes.create()
    container = None
    try:
        container = client.containers.create(
            image=image,
            command=["/bin/sh", "-c",
                     "while [ ! -f /sandbox/project_runner.py ]; do sleep 0.05; done; "
                     "exec python3 /sandbox/project_runner.py"],
            working_dir="/sandbox", network_disabled=True,
            mem_limit="768m", nano_cpus=1_000_000_000, pids_limit=64,
            read_only=True, volumes={volume.name: {"bind": "/sandbox", "mode": "rw"}},
            tmpfs={"/tmp": "rw,exec,size=384m,mode=1777"},
            user="65534:65534", cap_drop=["ALL"],
            security_opt=["no-new-privileges"], init=True,
            environment={"HOME": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"},
            detach=True,
        )
        container.start()
        container.put_archive("/sandbox", buffer.getvalue())
        container.wait(timeout=settings.JUDGE_WALL_TIME_LIMIT)
        payload = _parse_runner_output(container.logs(stdout=True, stderr=False))
        if payload.get("error"):
            raise SandboxError(str(payload["error"]))
        return payload["result"]
    except SandboxError:
        raise
    except Exception as exc:
        raise SandboxError(f"工程题容器执行失败: {exc}") from exc
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass
        try:
            volume.remove(force=True)
        except Exception:
            pass
