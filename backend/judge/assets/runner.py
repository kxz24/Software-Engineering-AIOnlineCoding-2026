#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
容器内判题 runner。

由 worker 随代码、测试用例一起通过 tar 写入 /sandbox，
在禁用网络、只读根文件系统、受限资源的容器中运行。

输入：/sandbox/manifest.json
输出：stdout 上一行 JSON（程序自身的 stdout 已重定向到文件，不会污染）
"""

import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import time

SANDBOX = "/sandbox"
# /sandbox 是只读的命名卷（代码与用例），编译产物与输出写到 tmpfs /tmp
WORK = "/tmp/judge-work"
MANIFEST = os.path.join(SANDBOX, "manifest.json")

COMPILE_OUTPUT_LIMIT = 8192
EXCERPT_LIMIT = 2048


def _read_text(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return ""
    return text[:limit] if limit else text


def _normalize(text):
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _set_limits(time_limit_ms, memory_limit_mb, output_limit_kb, use_rlimit_as):
    """在子进程 exec 前设置资源限制；单项失败不影响其他限制。"""
    cpu_seconds = max(1, int(time_limit_ms / 1000) + 1)
    limits = [
        (resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1)),
        # 文件大小留出 1MB 余量，便于区分「输出超限」而不是进程直接消失
        (resource.RLIMIT_FSIZE, ((output_limit_kb + 1024) * 1024,) * 2),
        (resource.RLIMIT_NPROC, (32, 32)),
        (resource.RLIMIT_CORE, (0, 0)),
    ]
    if use_rlimit_as:
        memory_bytes = (memory_limit_mb + 64) * 1024 * 1024
        limits.append((resource.RLIMIT_AS, (memory_bytes, memory_bytes)))
    for resource_id, value in limits:
        try:
            resource.setrlimit(resource_id, value)
        except (ValueError, OSError):
            pass


def _exit_code(status):
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    return 1


def _run_case(run_cmd, case, time_limit_ms, memory_limit_mb, output_limit_kb,
              use_rlimit_as):
    index = case["index"]
    input_path = os.path.join(SANDBOX, case["input"])
    expected_path = os.path.join(SANDBOX, case["expected"])
    output_path = os.path.join(WORK, "cases", f"{index}.actual")
    error_path = os.path.join(WORK, "cases", f"{index}.err")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    timed_out = False
    started = time.monotonic()
    with open(input_path, "rb") as stdin_file, \
            open(output_path, "wb") as stdout_file, \
            open(error_path, "wb") as stderr_file:
        process = subprocess.Popen(
            run_cmd,
            cwd=WORK,
            stdin=stdin_file,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
            preexec_fn=lambda: _set_limits(
                time_limit_ms, memory_limit_mb, output_limit_kb, use_rlimit_as
            ),
        )
        # 墙钟兜底：CPU 限制对阻塞/休眠的程序无效
        deadline = started + time_limit_ms / 1000.0 + 0.5
        status = 0
        usage = None
        while True:
            done_pid, status, usage = os.wait4(process.pid, os.WNOHANG)
            if done_pid == process.pid:
                break
            if time.monotonic() > deadline:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(0.005)
        elapsed_ms = int((time.monotonic() - started) * 1000)

    # wait4 已经回收子进程，手动回填 returncode，避免 Popen 再次 waitpid
    process.returncode = _exit_code(status)

    exit_code = process.returncode
    signal_number = -exit_code if exit_code < 0 else 0
    memory_kb = int(usage.ru_maxrss) if usage else 0

    output_size = os.path.getsize(output_path)
    output_limit_bytes = output_limit_kb * 1024
    actual = _read_text(output_path, output_limit_bytes + 1)
    expected = _read_text(expected_path)
    error_text = _read_text(error_path, EXCERPT_LIMIT)

    if timed_out or signal_number == signal.SIGXCPU:
        verdict = "time_limit_exceeded"
    elif signal_number == signal.SIGXFSZ or output_size > output_limit_bytes:
        verdict = "output_limit_exceeded"
    elif exit_code != 0:
        verdict = "runtime_error"
    elif _normalize(actual) != _normalize(expected):
        verdict = "wrong_answer"
    else:
        verdict = "accepted"

    output_excerpt = actual[:EXCERPT_LIMIT] if case.get("is_sample") else ""
    return {
        "index": index,
        "verdict": verdict,
        "time_ms": elapsed_ms,
        "memory_kb": max(0, memory_kb),
        "output_excerpt": output_excerpt,
        "error_excerpt": error_text,
    }


def main():
    try:
        with open(MANIFEST, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": f"manifest 读取失败: {exc}"}, ensure_ascii=False))
        return

    try:
        os.makedirs(WORK, exist_ok=True)
        os.makedirs(os.path.join(WORK, "cases"), exist_ok=True)
        source_name = manifest.get("source")
        if source_name:
            shutil.copyfile(
                os.path.join(SANDBOX, source_name),
                os.path.join(WORK, source_name),
            )
    except OSError as exc:
        print(json.dumps(
            {"error": f"准备判题工作目录失败: {exc}"}, ensure_ascii=False
        ))
        return

    compile_cmd = manifest.get("compile") or []
    compile_info = {"ok": True, "output": ""}
    if compile_cmd:
        try:
            compiled = subprocess.run(
                compile_cmd,
                cwd=WORK,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=30,
            )
            if compiled.returncode != 0:
                compile_info = {
                    "ok": False,
                    "output": (compiled.stdout + compiled.stderr)[:COMPILE_OUTPUT_LIMIT],
                }
        except subprocess.TimeoutExpired:
            compile_info = {"ok": False, "output": "编译超时（30 秒）"}
        except OSError as exc:
            compile_info = {"ok": False, "output": f"编译命令执行失败: {exc}"}

    cases = manifest.get("cases") or []
    results = []
    if not compile_info["ok"]:
        # 编译失败时每个用例都标记 compile_error，便于前端按用例展示
        for case in cases:
            results.append({
                "index": case["index"],
                "verdict": "compile_error",
                "time_ms": 0,
                "memory_kb": 0,
                "output_excerpt": "",
                "error_excerpt": compile_info["output"][:EXCERPT_LIMIT],
            })
    else:
        for case in cases:
            try:
                results.append(_run_case(
                    manifest["run"],
                    case,
                    int(manifest["time_limit_ms"]),
                    int(manifest["memory_limit_mb"]),
                    int(manifest["output_limit_kb"]),
                    bool(manifest.get("use_rlimit_as", True)),
                ))
            except Exception as exc:  # runner 内部错误也要返回结构化结果
                results.append({
                    "index": case["index"],
                    "verdict": "system_error",
                    "time_ms": 0,
                    "memory_kb": 0,
                    "output_excerpt": "",
                    "error_excerpt": f"runner 错误: {exc}"[:EXCERPT_LIMIT],
                })

    print(json.dumps(
        {"compile": compile_info, "cases": results},
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
    sys.exit(0)
