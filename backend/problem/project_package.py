"""Portable teacher package format for multi-file engineering problems."""

import io
import json
import re
import stat
import zipfile
from pathlib import PurePosixPath

MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_UNPACKED_BYTES = 32 * 1024 * 1024
MAX_PUBLIC_BYTES = 1024 * 1024
SYSTEM_PACKAGE = re.compile(r"^[a-z0-9][a-z0-9+.-]{0,79}$")
PYTHON_PACKAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}(?:==[A-Za-z0-9._+-]{1,40})?$")


class ProjectPackageError(ValueError):
    pass


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or "\\" in name or path.is_absolute() or
            any(part in ("", ".", "..") for part in name.split("/")) or
            len(name) > 256):
        raise ProjectPackageError(f"非法文件路径: {name}")
    return str(path)


def parse_package(raw):
    """Validate ZIP and return (metadata, public text files)."""
    if not raw or len(raw) > MAX_ARCHIVE_BYTES:
        raise ProjectPackageError("工程题 ZIP 必须非空且不超过 8 MB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ProjectPackageError("工程题 ZIP 无法读取") from exc
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > 512:
            raise ProjectPackageError("工程题文件过多（上限 512）")
        names = set()
        public = {}
        total = 0
        public_total = 0
        for info in infos:
            name = safe_name(info.filename)
            if name in names:
                raise ProjectPackageError(f"重复文件: {name}")
            names.add(name)
            if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
                raise ProjectPackageError("不允许符号链接")
            total += info.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ProjectPackageError("解压后文件过大（上限 32 MB）")
            if name.startswith("public/"):
                public_total += info.file_size
                if public_total > MAX_PUBLIC_BYTES:
                    raise ProjectPackageError("公开代码过大（上限 1 MB）")
                relative = name[len("public/"):]
                if not relative or len(relative) > 110:
                    raise ProjectPackageError("公开文件路径无效或过长")
                try:
                    public[relative] = archive.read(info).decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ProjectPackageError("公开文件必须是 UTF-8 文本") from exc
            elif not name.startswith("private/") and name != "project.json":
                raise ProjectPackageError(f"文件需放在 public/ 或 private/: {name}")
        if "project.json" not in names or not public or not any(
            name.startswith("private/") for name in names
        ):
            raise ProjectPackageError("需要 project.json、public/ 和 private/ 文件")
        selfcheck_names = [name for name in names if name.startswith("private/selfcheck/")]
        if selfcheck_names:
            if len(selfcheck_names) > 100 or sum(
                archive.getinfo(name).file_size for name in selfcheck_names
            ) > 200_000:
                raise ProjectPackageError("参考提交最多 100 个文件、200 KB")
            for name in selfcheck_names:
                if name[len("private/selfcheck/"):] not in public:
                    raise ProjectPackageError("参考提交文件必须对应公开初始文件")
                try:
                    archive.read(name).decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ProjectPackageError("参考提交必须是 UTF-8 文本") from exc
        try:
            config = json.loads(archive.read("project.json"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProjectPackageError("project.json 不是有效 JSON") from exc
        if not isinstance(config, dict):
            raise ProjectPackageError("project.json 必须是对象")
        title = config.get("title")
        description = config.get("description")
        runtime = config.get("runtime")
        command = config.get("graderCommand")
        max_score = config.get("maxScore", 100)
        environment = config.get("environment")
        has_dockerfile = "private/Dockerfile" in names
        if has_dockerfile:
            if environment is not None:
                raise ProjectPackageError("已有 private/Dockerfile，不必再填写 environment")
            if archive.getinfo("private/Dockerfile").file_size > 64 * 1024:
                raise ProjectPackageError("Dockerfile 不能超过 64 KB")
            environment = {"dockerfile": True}
        if environment is not None:
            if not isinstance(environment, dict) or set(environment) - {"systemPackages", "pythonPackages", "dockerfile"}:
                raise ProjectPackageError("environment 只能包含 systemPackages 和 pythonPackages")
            if has_dockerfile:
                environment = {"dockerfile": True}
            else:
                if "dockerfile" in environment:
                    raise ProjectPackageError("Dockerfile 模式需提供 private/Dockerfile")
                for key, pattern in (("systemPackages", SYSTEM_PACKAGE), ("pythonPackages", PYTHON_PACKAGE)):
                    packages = environment.get(key, [])
                    if (not isinstance(packages, list) or len(packages) > 30 or
                            any(not isinstance(value, str) or not pattern.fullmatch(value)
                                for value in packages)):
                        raise ProjectPackageError(f"{key} 必须是最多 30 个安全包名的数组")
                environment = {
                    "systemPackages": sorted(set(environment.get("systemPackages", []))),
                    "pythonPackages": sorted(set(environment.get("pythonPackages", []))),
                }
        if not isinstance(title, str) or not title.strip() or len(title) > 128:
            raise ProjectPackageError("title 必须是 1–128 字符")
        if not isinstance(description, str) or not description.strip():
            raise ProjectPackageError("description 不能为空")
        if environment is None and (not isinstance(runtime, str) or not runtime or len(runtime) > 64):
            raise ProjectPackageError("runtime 无效")
        if environment is not None and runtime not in (None, ""):
            raise ProjectPackageError("environment 和 runtime 只能选择一种")
        if environment is not None and not selfcheck_names:
            raise ProjectPackageError("自动准备环境的题包需有 private/selfcheck/ 参考提交")
        if has_dockerfile and "private/build/Dockerfile" in names:
            raise ProjectPackageError("private/build/ 中不能再放 Dockerfile")
        if (not isinstance(command, list) or not command or len(command) > 24 or
                any(not isinstance(part, str) or not part or len(part) > 256 for part in command)):
            raise ProjectPackageError("graderCommand 必须是非空参数数组")
        if type(max_score) is not int or not 1 <= max_score <= 1000:
            raise ProjectPackageError("maxScore 需在 1–1000 之间")
        minimum = config.get("selfCheckMinScore", 1)
        if type(minimum) not in (int, float) or not 0 < minimum <= max_score:
            raise ProjectPackageError("selfCheckMinScore 需大于 0 且不超过满分")
        metadata = {
            "title": title.strip(), "description": description,
            "runtime": runtime or "managed", "environment": environment,
            "grader_command": command,
            "max_score": max_score,
            "self_check_min_score": minimum,
            "difficulty": config.get("difficulty", "hard"),
            "language": config.get("language", "c"),
        }
        return metadata, public
