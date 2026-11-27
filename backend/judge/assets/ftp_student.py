"""在低权限学生容器中启动、等待或停止一次构建/运行。"""

import json
import os
import resource
import signal
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def limit_file_size():
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_100_000_000, 1_100_000_000))


def main(request):
    action = request["action"]
    if action == "copy_client":
        destination = Path(request["cwd"])
        shutil.copytree("/sandbox/student/client", destination, symlinks=True)
        destination.chmod(0o2770)
        return {}
    if action == "prepare_executable":
        executable = Path(request["cwd"]) / request["name"]
        if executable.is_symlink() or not executable.is_file():
            return {"missing": True}
        executable.chmod(0o755)
        return {}
    if action == "stop":
        try:
            os.killpg(request["pid"], signal.SIGKILL)
        except ProcessLookupError:
            pass
        return {}
    options = {
        "cwd": request["cwd"],
        "stderr": subprocess.STDOUT,
        "start_new_session": True,
        "preexec_fn": limit_file_size,
    }
    if action == "start":
        process = subprocess.Popen(
            request["argv"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, **options,
        )
        return {"pid": process.pid}

    commands = request.get("commands")
    stdin = request.get("stdin")
    data = stdin.encode() if stdin is not None else ("\n".join(commands) + "\n").encode() if commands else None
    with tempfile.TemporaryFile() as output:
        with subprocess.Popen(
            request["argv"], stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
            stdout=output, **options,
        ) as process:
            try:
                process.communicate(data, timeout=request["timeout"])
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        output.seek(0)
        return {"status": process.returncode, "output": output.read(8192).decode("utf-8", errors="replace")}


if __name__ == "__main__":
    try:
        response = main(json.loads(sys.argv[1]))
    except subprocess.TimeoutExpired:
        response = {"timeout": True}
    except OSError as exc:
        response = {"error": str(exc)}
    print(json.dumps(response))
