"""网页工程工作区与判题快照。"""

import io
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from django.db import transaction

from agent.models import WorkspaceFile
from exam.models import ProjectWorkspace
from judge.project import MAX_ARCHIVE_BYTES, read_project

MAX_PATH = 128
MAX_EDITABLE_FILE = 256 * 1024


class WorkspaceConflict(ValueError):
    pass


def _split_template(archive):
    editable, fixed = {}, {}
    files = read_project(bytes(archive)) if archive else {}
    for name, data in files.items():
        if len(name) > MAX_PATH:
            raise ValueError("工程模板中的文件路径不能超过 128 个字符")
        try:
            if len(data) > MAX_EDITABLE_FILE or b"\x00" in data:
                raise UnicodeError
            editable[name] = data.decode("utf-8")
        except UnicodeError:
            fixed[name] = data
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("在线模板不支持只有大小写不同的文件名")
    return editable, fixed


def validate_template(archive):
    _split_template(archive)


def _valid_name(name):
    if not isinstance(name, str):
        return False
    path = PurePosixPath(name)
    return (
        0 < len(name) <= MAX_PATH and bool(path.parts) and path.as_posix() == name
        and not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name
        and all(ord(char) >= 32 for char in name)
    )


def _zip(files):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    data = buffer.getvalue()
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("工程源码包不能超过 16 MB")
    return data


def _query(workspace):
    return WorkspaceFile.objects.filter(
        exam_id=workspace.exam_id, problem_id=workspace.problem_id, student_id=workspace.student_id,
    )


@transaction.atomic
def open_workspace(exam, problem, student):
    workspace, created = ProjectWorkspace.objects.get_or_create(exam=exam, problem=problem, student=student)
    if created:
        editable, fixed = _split_template(problem.project_template)
        workspace.fixed_archive = _zip(fixed) if fixed else None
        workspace.save(update_fields=["fixed_archive"])
        WorkspaceFile.objects.bulk_create([
            WorkspaceFile(exam=exam, problem=problem, student=student, path=name, content=text)
            for name, text in editable.items()
        ], ignore_conflicts=True)
    return workspace


def workspace_payload(workspace):
    fixed = read_project(bytes(workspace.fixed_archive)) if workspace.fixed_archive else {}
    return {
        "files": list(_query(workspace).order_by("path").values("path", "content", "revision")),
        "fixedFiles": sorted(fixed),
        "version": workspace.revision,
    }


def _verify_revisions(workspace, files, expected, version):
    if (type(version) is not int or version != workspace.revision or not isinstance(expected, dict) or any(type(value) is not int for value in expected.values())
            or expected != {file.path: file.revision for file in files}):
        raise WorkspaceConflict("工作区已在其他页面修改，请保留未保存内容并刷新后重试")


def _combine(workspace, editables):
    files = read_project(bytes(workspace.fixed_archive)) if workspace.fixed_archive else {}
    if not isinstance(editables, dict) or len(editables) + len(files) > 1024:
        raise ValueError("工程最多保留 1024 个文件")
    for name, value in editables.items():
        if not _valid_name(name) or name in files:
            raise ValueError("文件路径不合法或与只读文件重名")
        if not isinstance(value, str):
            raise ValueError("网页编辑器只保存文本文件")
        raw = value.encode("utf-8")
        if len(raw) > MAX_EDITABLE_FILE:
            raise ValueError(f"{name} 超过 256 KB")
        files[name] = raw
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("在线工作区不支持只有大小写不同的文件名")
    if any(parent.as_posix() in files for name in files for parent in PurePosixPath(name).parents):
        raise ValueError("文件路径与已有目录冲突")
    return files


@transaction.atomic
def save_workspace(workspace, editables, expected, version):
    workspace = ProjectWorkspace.objects.select_for_update().get(pk=workspace.pk)
    records = list(_query(workspace).select_for_update())
    _verify_revisions(workspace, records, expected, version)
    _combine(workspace, editables)
    if {file.path: file.content for file in records} == editables:
        return workspace_payload(workspace)
    remaining = editables.copy()
    for file in records:
        if file.path not in remaining:
            file.delete()
            continue
        content = remaining.pop(file.path)
        if content != file.content:
            file.content = content
            file.revision += 1
            file.save(update_fields=["content", "revision", "updated_at"])
    WorkspaceFile.objects.bulk_create([
        WorkspaceFile(exam_id=workspace.exam_id, problem_id=workspace.problem_id,
                      student_id=workspace.student_id, path=name, content=content)
        for name, content in remaining.items()
    ])
    workspace.revision += 1
    workspace.save(update_fields=["revision"])
    return workspace_payload(workspace)


@transaction.atomic
def workspace_archive(exam, problem_id, student, expected, version):
    workspace = ProjectWorkspace.objects.select_for_update().filter(
        exam=exam, problem_id=problem_id, student=student,
    ).first()
    if workspace is None:
        raise ValueError("请先打开工程工作区")
    records = list(_query(workspace).select_for_update())
    _verify_revisions(workspace, records, expected, version)
    files = _combine(workspace, {file.path: file.content for file in records})
    if not files:
        raise ValueError("工程工作区没有可提交的文件")
    archive = _zip(files)
    read_project(archive)
    return archive
