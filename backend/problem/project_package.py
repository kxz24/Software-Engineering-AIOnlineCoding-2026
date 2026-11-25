"""Portable teacher package format for multi-file engineering problems."""

import io
import json
import stat
import zipfile
from pathlib import PurePosixPath

MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_UNPACKED_BYTES = 32 * 1024 * 1024
MAX_PUBLIC_BYTES = 1024 * 1024


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
        if not isinstance(title, str) or not title.strip() or len(title) > 128:
            raise ProjectPackageError("title 必须是 1–128 字符")
        if not isinstance(description, str) or not description.strip():
            raise ProjectPackageError("description 不能为空")
        if not isinstance(runtime, str) or not runtime or len(runtime) > 64:
            raise ProjectPackageError("runtime 无效")
        if (not isinstance(command, list) or not command or len(command) > 24 or
                any(not isinstance(part, str) or not part or len(part) > 256 for part in command)):
            raise ProjectPackageError("graderCommand 必须是非空参数数组")
        if type(max_score) is not int or not 1 <= max_score <= 1000:
            raise ProjectPackageError("maxScore 需在 1–1000 之间")
        metadata = {
            "title": title.strip(), "description": description,
            "runtime": runtime, "grader_command": command,
            "max_score": max_score,
            "difficulty": config.get("difficulty", "hard"),
            "language": config.get("language", "c"),
        }
        return metadata, public
