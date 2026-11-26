"""检查工程包并读取评测所需文件，保留原包供教师复核。"""

import io
import stat
import zlib
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024


def read_project(archive):
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("工程包不能超过 16 MB")
    try:
        with ZipFile(io.BytesIO(archive)) as project:
            entries = {}
            expanded_size = 0
            for entry in project.infolist():
                name = entry.filename
                relative = PurePosixPath(name)
                if (
                    relative.is_absolute() or ".." in relative.parts
                    or not relative.parts or "\\" in name or ":" in name
                ):
                    raise ValueError("工程包包含无效文件路径")
                mode = entry.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ValueError("工程包只允许普通文件和目录")
                if entry.is_dir():
                    continue
                if relative in entries:
                    raise ValueError("工程包包含重名文件")
                expanded_size += entry.file_size
                if expanded_size > MAX_EXPANDED_BYTES or len(entries) >= 1024:
                    raise ValueError("工程包解压后不能超过 64 MB 或 1024 个文件")
                entries[relative] = entry

            roots = {relative.parts[0] for relative in entries}
            wrapped = len(roots) == 1 and not roots.intersection({"server", "client"})
            files = {}
            for relative, entry in entries.items():
                parts = relative.parts[1:] if wrapped else relative.parts
                if len(parts) >= 2 and parts[0] in {"server", "client"}:
                    files["/".join(parts)] = project.read(entry)
            if not files:
                raise ValueError("工程包须包含 server/ 或 client/ 目录")
            if any(parent.as_posix() in files for name in files for parent in PurePosixPath(name).parents):
                raise ValueError("工程包包含同名文件与目录")
            return files
    except (BadZipFile, EOFError, NotImplementedError, RuntimeError, zlib.error) as exc:
        raise ValueError("无法读取 ZIP 工程包，请检查格式和压缩方式") from exc
