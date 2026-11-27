"""通过独立容器运行教师评分脚本，学生进程由限定接口启动。"""
import contextlib
import json
from pathlib import Path
import runpy
import sys
import time

GRADER = Path("/sandbox/grader")


def request(action, **kwargs):
    request_id = time.monotonic_ns()
    marker = GRADER / f"response-{request_id}.json"
    print(json.dumps({"request": request_id, "action": action, **kwargs}), file=sys.__stdout__, flush=True)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            result = json.loads(marker.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.05)
            continue
        marker.unlink()
        if result.get("timeout"):
            return {"status": 124, "output": "学生程序运行超时"}
        if result.get("error"):
            return {"status": 1, "output": result["error"]}
        return result
    raise RuntimeError("学生容器未响应")


class Project:
    root = Path("/sandbox/student")
    shared = Path("/sandbox/exchange/work")
    private = GRADER

    def run(self, argv, *, cwd=".", stdin=None, timeout=10):
        if not 1 <= timeout <= 30:
            raise ValueError("单次运行时限须在 1–30 秒之间")
        return request("run", argv=argv, cwd=str(self.root / cwd), stdin=stdin, timeout=timeout)

    @contextlib.contextmanager
    def start(self, argv, *, cwd="."):
        result = request("start", argv=argv, cwd=str(self.root / cwd))
        if "pid" not in result:
            raise RuntimeError(result["output"])
        try:
            yield
        finally:
            request("stop", pid=result["pid"])


if __name__ == "__main__":
    with contextlib.redirect_stdout(sys.stderr):
        grade = runpy.run_path(str(GRADER / "grade.py"))["grade"]
        cases = grade(Project())
    print(json.dumps({"cases": cases}, ensure_ascii=False), flush=True)
