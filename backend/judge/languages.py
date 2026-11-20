# -*- coding: utf-8 -*-
"""各判题语言的源文件名、编译命令与运行命令。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageConfig:
    key: str
    source: str
    compile: tuple
    run: tuple
    # Java 的 JVM 会预留大量虚拟地址空间，不能用 RLIMIT_AS，改用 -Xmx
    use_rlimit_as: bool = True


LANGUAGES = {
    "python": LanguageConfig(
        key="python",
        source="main.py",
        compile=(),
        run=("python3", "main.py"),
    ),
    "c": LanguageConfig(
        key="c",
        source="main.c",
        compile=("gcc", "-O2", "-std=c17", "-o", "main", "main.c", "-lm"),
        run=("./main",),
    ),
    "cpp": LanguageConfig(
        key="cpp",
        source="main.cpp",
        compile=("g++", "-O2", "-std=c++17", "-o", "main", "main.cpp"),
        run=("./main",),
    ),
    "java": LanguageConfig(
        key="java",
        source="Main.java",
        compile=("javac", "-d", ".", "Main.java"),
        run=("java", "-Xmx{memory_mb}m", "-cp", ".", "Main"),
        use_rlimit_as=False,
    ),
}


def normalize_language(submitted, problem_language):
    """把提交语言归一化到受支持的语言；不合法时回退题目语言。"""
    for value in (submitted, problem_language):
        key = str(value or "").strip().lower()
        if key in LANGUAGES:
            return key
    return None


def run_command(config, memory_limit_mb):
    """把 {memory_mb} 占位替换为题目内存上限。"""
    return [part.format(memory_mb=memory_limit_mb) for part in config.run]


def language_payload(config, memory_limit_mb):
    """写入容器 manifest 的语言配置。"""
    return {
        "key": config.key,
        "source": config.source,
        "compile": list(config.compile),
        "run": run_command(config, memory_limit_mb),
        "use_rlimit_as": config.use_rlimit_as,
    }
