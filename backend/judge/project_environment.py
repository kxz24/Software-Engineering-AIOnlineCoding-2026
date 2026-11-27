"""Build a reusable, bounded tool image from a teacher's package declaration."""

import hashlib
import io
import json
import tarfile
import zipfile

from django.conf import settings

from .project_sandbox import run_project_sandbox
from .sandbox import _docker_client


def image_for_environment(environment, archive_bytes=b""):
    base = settings.PROJECT_MANAGED_BASE_IMAGE
    source = json.dumps({"base": base, "environment": environment}, sort_keys=True).encode()
    return "aicoding-project-env:" + hashlib.sha256(source + archive_bytes).hexdigest()[:20]


def _advanced_context(package_bytes):
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as source, tarfile.open(fileobj=buffer, mode="w") as target:
        for info in source.infolist():
            if info.is_dir():
                continue
            if info.filename == "private/Dockerfile":
                name = "Dockerfile"
            elif info.filename.startswith("private/build/"):
                name = info.filename[len("private/build/"):]
            else:
                continue
            data = source.read(info)
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            entry.mode = 0o755 if (info.external_attr >> 16) & 0o111 else 0o644
            target.addfile(entry, io.BytesIO(data))
    return buffer.getvalue()


def prepare_environment(bundle):
    """Build once, then grade the teacher's private reference submission."""
    environment = bundle.environment
    if environment is None:
        raise ValueError("题目未声明自动准备环境")
    package_bytes = bytes(bundle.archive)
    advanced = bool(environment.get("dockerfile"))
    image_name = image_for_environment(environment, package_bytes if advanced else b"")
    client = _docker_client()
    try:
        client.images.get(image_name)
    except Exception:
        if advanced:
            build_content = _advanced_context(package_bytes)
        else:
            system = environment["systemPackages"]
            python = environment["pythonPackages"]
            lines = [f"FROM {settings.PROJECT_MANAGED_BASE_IMAGE}"]
            if system:
                lines.append("RUN apt-get update && apt-get install -y --no-install-recommends " +
                             " ".join(system) + " && rm -rf /var/lib/apt/lists/*")
            if python:
                lines.append("RUN python3 -m pip install --no-cache-dir " + " ".join(python))
            lines.append("WORKDIR /sandbox")
            build_content = ("\n".join(lines) + "\n").encode()
        client.images.build(
            fileobj=io.BytesIO(build_content), custom_context=advanced,
            tag=image_name, rm=True, forcerm=True, timeout=300,
            container_limits={"memory": 768 * 1024 * 1024},
        )

    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        files = dict(bundle.public_files)
        for name in archive.namelist():
            if name.startswith("private/selfcheck/") and not name.endswith("/"):
                files[name[len("private/selfcheck/"):]] = archive.read(name).decode("utf-8")
    bundle.prepared_image = image_name
    result = run_project_sandbox(bundle, files)
    if result["score"] < bundle.self_check_min_score:
        raise ValueError(
            f"参考提交仅得 {result['score']}/{bundle.max_score} 分，"
            f"低于要求的 {bundle.self_check_min_score} 分"
        )
    return image_name, f"环境与评分器自检通过；参考提交得 {result['score']}/{bundle.max_score} 分"
