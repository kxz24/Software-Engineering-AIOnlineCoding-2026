#!/usr/bin/env python3
"""Run a teacher package in a disposable work directory and emit one JSON line."""

import io
import json
import math
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath


def _safe(name):
    path = PurePosixPath(name)
    if (not name or "\\" in name or path.is_absolute() or
            any(part in ("", ".", "..") for part in name.split("/"))):
        raise ValueError("invalid package path")
    return path


def run_project(package_bytes, submission, timeout=100):
    config = None
    with tempfile.TemporaryDirectory(prefix="project-grade-") as root_name:
        root = Path(root_name)
        source = root / "submission"
        source.mkdir()
        private = root / "private"
        private.mkdir()
        with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
            config = json.loads(archive.read("project.json"))
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = _safe(info.filename)
                if name.parts[0] == "public":
                    target = source.joinpath(*name.parts[1:])
                elif name.parts[0] == "private":
                    target = private.joinpath(*name.parts[1:])
                else:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
                target.chmod(0o755 if (info.external_attr >> 16) & 0o111 else 0o644)
        files = submission.get("files")
        if not isinstance(files, dict):
            raise ValueError("submission files missing")
        for name, content in files.items():
            path = _safe(name)
            if path.parts[0] == "private" or not isinstance(content, str):
                raise ValueError("invalid submitted file")
            target = source.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        command = config["graderCommand"]
        completed = subprocess.run(
            command, cwd=root, text=True, capture_output=True, timeout=timeout,
            env={**os.environ, "PROJECT_SUBMISSION": str(source),
                 "PROJECT_PRIVATE": str(private), "PROJECT_RESULT": str(root / "result.json")},
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"grader exited {completed.returncode}: {(completed.stdout + completed.stderr)[-1000:]}")
        result = json.loads((root / "result.json").read_text(encoding="utf-8"))
        max_score = config["maxScore"]
        if (not isinstance(result, dict) or
                type(result.get("score")) not in (int, float) or
                not math.isfinite(result["score"]) or
                not 0 <= result["score"] <= max_score or
                result.get("maxScore") != max_score or
                not isinstance(result.get("items"), list) or
                len(result["items"]) > 100):
            raise ValueError("grader result has invalid score or items")
        for item in result["items"]:
            if (not isinstance(item, dict) or
                    type(item.get("score")) not in (int, float) or
                    type(item.get("maxScore")) not in (int, float) or
                    not math.isfinite(item["score"]) or
                    not math.isfinite(item["maxScore"]) or
                    not 0 <= item["score"] <= item["maxScore"] or
                    not isinstance(item.get("visible"), bool)):
                raise ValueError("grader result has invalid item")
        return result


if __name__ == "__main__":
    try:
        package = Path(os.environ.get("PROJECT_PACKAGE", "/sandbox/package.zip")).read_bytes()
        submission_data = json.loads(Path(os.environ.get(
            "PROJECT_SUBMISSION_JSON", "/sandbox/submission.json"
        )).read_text(encoding="utf-8"))
        outcome = {"result": run_project(package, submission_data)}
    except Exception as exc:
        outcome = {"error": str(exc)[:1000]}
    print(json.dumps(outcome, ensure_ascii=False))
