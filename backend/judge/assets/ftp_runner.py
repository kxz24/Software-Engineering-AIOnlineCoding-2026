"""在容器内评测课程 FTP 项目。标准对端与学生程序使用独立身份。"""

import ftplib
import json
import logging
import os
import socket
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.ioloop import IOLoop
from pyftpdlib.log import config_logging
from pyftpdlib.servers import FTPServer

HOST = "127.0.0.1"
PASSWORD = "student@example.test"
SMALL_BYTES = 128 * 1024 + 17
LARGE_BYTES = 1_000_000_000


@dataclass
class CaseDirectory:
    shared: Path
    private: Path


class CheckFailed(Exception):
    pass


def check(condition, message):
    if not condition:
        raise CheckFailed(message)


def request_student(action, **arguments):
    request_id = time.monotonic_ns()
    marker = Path("/sandbox/grader") / f"response-{request_id}.json"
    print(json.dumps({"request": request_id, "action": action, **arguments}), flush=True)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            reply = json.loads(marker.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.05)
            continue
        marker.unlink()
        if reply.get("timeout"):
            raise TimeoutError
        if reply.get("error"):
            raise CheckFailed(reply["error"])
        return reply
    raise RuntimeError("学生运行入口未响应")


def run_student(argv, cwd, timeout, commands=None):
    result = request_student("run", argv=argv, cwd=str(cwd), timeout=timeout, commands=commands)
    return result["status"], result["output"]


def shared_directory(directory):
    directory.mkdir()
    directory.chmod(0o2770)
    return directory


def prepare_side(side):
    source = Path("/sandbox/student") / side
    if not source.is_dir():
        return False, f"缺少 {side}/ 目录"
    output = ""
    if any((source / name).is_file() for name in ("GNUmakefile", "makefile", "Makefile")):
        try:
            status, output = run_student(["make", "-B"], source, 15)
        except TimeoutError:
            return False, f"{side} 构建超时"
        except CheckFailed as exc:
            return False, str(exc)
        if status:
            return False, output or f"{side} 构建失败"
    elif side == "server":
        return False, "服务端缺少 Makefile"
    if request_student("prepare_executable", cwd=str(source), name=side).get("missing"):
        return False, f"未生成 {side} 启动文件"
    return True, output


def fixture(path, size):
    with path.open("wb") as stream:
        while size > 0:
            chunk_size = min(size, 1024 * 1024)
            stream.write(os.urandom(chunk_size))
            size -= chunk_size
    path.chmod(0o640)


def same_file(first, second):
    if not second.is_file() or second.is_symlink():
        return False
    with first.open("rb") as expected, open(
        second, "rb", opener=lambda name, flags: os.open(name, flags | os.O_NOFOLLOW),
    ) as actual:
        while True:
            chunk = expected.read(1024 * 1024)
            if chunk != actual.read(1024 * 1024):
                return False
            if not chunk:
                return True


def available_port():
    with socket.socket() as listener:
        listener.bind((HOST, 0))
        return listener.getsockname()[1]


@contextmanager
def student_server(source, work, timeout):
    port = available_port()
    root = shared_directory(work.shared / "files")
    process = request_student(
        "start", argv=["./server", "-port", str(port), "-root", str(root)], cwd=str(source),
    )
    with ftplib.FTP(timeout=timeout) as ftp:
        try:
            deadline = time.monotonic() + 3
            while True:
                try:
                    greeting = ftp.connect(HOST, port)
                    break
                except ConnectionRefusedError as exc:
                    if time.monotonic() >= deadline:
                        raise CheckFailed("服务端未在指定端口启动") from exc
                    time.sleep(0.05)
            check(greeting.startswith("220"), "欢迎响应应为 220")
            yield ftp, root
        finally:
            request_student("stop", pid=process["pid"])


@contextmanager
def reference_server(root):
    history = []
    authorizer = DummyAuthorizer()
    authorizer.add_user("anonymous", PASSWORD, str(root), perm="elradfmw")

    class ReferenceHandler(FTPHandler):
        def pre_process_command(self, line, cmd, arg):
            history.append(cmd)
            return super().pre_process_command(line, cmd, arg)

        def on_file_sent(self, file):
            history.append("download_complete")

        def on_file_received(self, file):
            history.append("upload_complete")

    ReferenceHandler.authorizer = authorizer
    loop = IOLoop()
    server = FTPServer((HOST, 0), ReferenceHandler, ioloop=loop)
    port = server.socket.getsockname()[1]
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"timeout": 0.05, "handle_exit": False}, daemon=True,
    )
    thread.start()
    try:
        yield port, history
    finally:
        server.close_all()
        thread.join(timeout=1)


def login(ftp):
    check(ftp.sendcmd("USER anonymous").startswith("331"), "USER 响应应为 331")
    check(ftp.sendcmd(f"PASS {PASSWORD}").startswith("230"), "PASS 响应应为 230")


def server_login(ftp, root, work):
    login(ftp)


def server_control(ftp, root, work):
    login(ftp)
    check(ftp.sendcmd("SYST") == "215 UNIX Type: L8", "SYST 响应与题面不符")
    check(ftp.voidcmd("TYPE I").startswith("200"), "TYPE I 响应应为 200")
    check(ftp.quit().startswith("221"), "QUIT 响应应为 221")


def server_directories(ftp, root, work):
    login(ftp)
    folder = "course-" + os.urandom(4).hex()
    ftp.mkd(folder)
    check((root / folder).is_dir(), "MKD 未创建目录")
    ftp.cwd(folder)
    check(ftp.pwd() == "/" + folder, "PWD 未返回当前工作目录")
    ftp.cwd("/")
    ftp.rmd(folder)
    check(not (root / folder).exists(), "RMD 未移除目录")


def server_invalid(ftp, root, work):
    login(ftp)
    try:
        ftp.retrbinary("RETR missing-" + os.urandom(4).hex(), lambda data: None)
    except ftplib.error_perm:
        pass
    else:
        raise CheckFailed("读取不存在的文件应返回失败")
    check(ftp.pwd() == "/", "失败请求后应仍可处理后续命令")


def server_boundary(ftp, root, work):
    login(ftp)
    try:
        ftp.cwd("..")
    except ftplib.error_perm:
        pass
    check(ftp.pwd() == "/", "根目录边界内的当前目录应保持为 /")
    outside = work.shared / ("outside-" + os.urandom(4).hex())
    fixture(outside, 32)
    try:
        ftp.retrbinary(f"RETR ../{outside.name}", lambda chunk: None)
    except ftplib.error_perm:
        return
    raise CheckFailed("请求根目录外的文件应被拒绝")


def server_transfer(ftp, root, work, *, passive, upload, size=SMALL_BYTES):
    ftp.set_pasv(passive)
    login(ftp)
    name = "transfer-" + os.urandom(4).hex() + ".bin"
    local = work.private / name
    remote = root / name
    if upload:
        fixture(local, size)
        local.chmod(0o600)
        with local.open("rb") as stream:
            reply = ftp.storbinary(f"STOR {name}", stream, blocksize=65536)
        check(same_file(local, remote), "服务端落盘内容与上传文件不一致")
    else:
        fixture(remote, size)
        with open(local, "wb", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            reply = ftp.retrbinary(f"RETR {name}", stream.write, blocksize=65536)
        check(same_file(remote, local), "下载内容与服务端文件不一致")
    check(reply.startswith("226"), "传输完成响应应为 226")


def client_scenario(source, work, scenario, passive=True, size=SMALL_BYTES):
    local = work.shared / "client-files"
    remote = work.private / "reference"
    remote.mkdir(mode=0o700)
    request_student("copy_client", cwd=str(local))
    suffix = os.urandom(4).hex()
    name = f"artifact-{suffix}.bin"
    folder = f"course-{suffix}"
    commands = ["USER anonymous", f"PASS {PASSWORD}"]
    mode = "PASV"
    if scenario == "control":
        actions = ["SYST", "TYPE I"]
    elif scenario == "directories":
        actions = [f"MKD {folder}", f"CWD {folder}", "PWD", "CWD /", f"RMD {folder}"]
    elif scenario == "list":
        fixture(remote / name, 0)
        actions = [mode, "LIST"]
    elif scenario == "download":
        fixture(remote / name, size)
        actions = [mode, f"RETR {name}"]
    else:
        expected_file = work.private / name
        fixture(expected_file, size)
        os.link(expected_file, local / name)
        actions = [mode, f"STOR {name}"]

    with reference_server(remote) as (port, history):
        if not passive:
            active_port = available_port()
            actions[0] = f"PORT 127,0,0,1,{active_port // 256},{active_port % 256}"
        commands.extend([*actions, "QUIT"])
        status, output = run_student(
            ["./client", "-ip", HOST, "-port", str(port)], local,
            30 if size == LARGE_BYTES else 5, commands=commands,
        )
    check(status == 0, "客户端未正常退出")
    expected = [command.split()[0] for command in commands]
    observed = iter(history)
    check(all(command in observed for command in expected), "参考服务端未收到完整命令序列")
    if scenario == "directories":
        check(f'"/{folder}"' in output and not (remote / folder).exists(), "目录操作结果不正确")
    elif scenario == "list":
        check(name in output, "列表未展示参考服务端文件")
    elif scenario == "download":
        check("download_complete" in history, "参考服务端未完成下载会话")
        check(same_file(remote / name, local / name), "客户端保存的文件内容不正确")
    elif scenario == "upload":
        check("upload_complete" in history, "参考服务端未完成上传会话")
        check(same_file(expected_file, remote / name), "参考服务端未收到完整文件")


SERVER_CASES = (
    ("服务端 · 匿名登录", 4, server_login, {}),
    ("服务端 · 系统命令与退出", 4, server_control, {}),
    ("服务端 · 目录操作", 6, server_directories, {}),
    ("服务端 · 主动下载", 4, server_transfer, {"passive": False, "upload": False}),
    ("服务端 · 主动上传", 4, server_transfer, {"passive": False, "upload": True}),
    ("服务端 · 被动下载", 4, server_transfer, {"passive": True, "upload": False}),
    ("服务端 · 被动上传", 4, server_transfer, {"passive": True, "upload": True}),
    ("服务端 · 无效请求后可继续操作", 3, server_invalid, {}),
    ("服务端 · 根目录边界", 2, server_boundary, {}),
    ("服务端 · 大文件传输", 5, server_transfer, {"passive": True, "upload": False, "size": LARGE_BYTES}),
)
CLIENT_CASES = (
    ("客户端 · 登录、系统命令与退出", 4, {"scenario": "control"}),
    ("客户端 · 目录操作", 4, {"scenario": "directories"}),
    ("客户端 · 目录列表", 4, {"scenario": "list"}),
    ("客户端 · 主动下载", 3, {"scenario": "download", "passive": False}),
    ("客户端 · 被动下载", 3, {"scenario": "download"}),
    ("客户端 · 主动上传", 3, {"scenario": "upload", "passive": False}),
    ("客户端 · 被动上传", 3, {"scenario": "upload"}),
    ("客户端 · 大文件传输", 6, {"scenario": "download", "size": LARGE_BYTES}),
)


def grade():
    config_logging(level=logging.CRITICAL)
    results = []
    logs = []
    with tempfile.TemporaryDirectory(dir="/sandbox/exchange") as temp:
        base = Path(temp)
        base.chmod(0o2750)
        for side in ("server", "client"):
            source = Path("/sandbox/student") / side
            ok, diagnostics = prepare_side(side)
            if diagnostics:
                logs.append(side + ":\n" + diagnostics)
            cases = SERVER_CASES if side == "server" else [
                (name, points, client_scenario, options) for name, points, options in CLIENT_CASES
            ]
            for name, points, test, options in cases:
                start = time.monotonic()
                verdict = "accepted" if ok else "compile_error"
                detail = "" if ok else "该端未成功构建"
                if ok:
                    with tempfile.TemporaryDirectory(dir=base) as case_dir, \
                         tempfile.TemporaryDirectory(dir="/sandbox/grader") as private_dir:
                        work = CaseDirectory(Path(case_dir), Path(private_dir))
                        work.shared.chmod(0o2770)
                        try:
                            if side == "server":
                                with student_server(source, work, 30 if options.get("size") == LARGE_BYTES else 5) as (ftp, root):
                                    test(ftp, root, work, **options)
                            else:
                                test(source, work, **options)
                        except TimeoutError:
                            verdict, detail = "time_limit_exceeded", "未在时限内完成预期操作"
                        except CheckFailed as exc:
                            verdict, detail = "wrong_answer", str(exc)
                        except ftplib.Error as exc:
                            verdict, detail = "wrong_answer", f"协议响应异常：{str(exc)[:3]}"
                        except (OSError, EOFError):
                            verdict, detail = "wrong_answer", "无法完成连接或读取传输结果"
                results.append({
                    "index": len(results) + 1, "name": name, "points": points,
                    "verdict": verdict, "time_ms": round((time.monotonic() - start) * 1000),
                    "error_excerpt": detail,
                })
    return {"compile": {"ok": True, "output": "\n".join(logs)}, "cases": results}


if __name__ == "__main__":
    print(json.dumps(grade(), ensure_ascii=False), flush=True)
