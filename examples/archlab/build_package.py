#!/usr/bin/env python3
"""Build the Arch Lab demo ZIP from teacher-supplied course files."""

import argparse
import json
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
FILES = (
    "PartA/sum.ys", "PartA/rsum.ys", "PartA/copy.ys",
    "PartB/seq-full.hcl", "PartC/ncopy.ys", "PartC/pipe-full.hcl",
)
PUBLIC_FROM_HANDOUT = {
    "seq/seq-full.hcl": "PartB/seq-full.hcl",
    "pipe/ncopy.ys": "PartC/ncopy.ys",
    "pipe/pipe-full.hcl": "PartC/pipe-full.hcl",
}
GRADE_ENTRY = """import json
import os
from pathlib import Path
from grade_archlab import grade

result = grade(
    Path(os.environ["PROJECT_SUBMISSION"]),
    Path(os.environ["PROJECT_PRIVATE"]) / "handout",
    {}, rubric="auto100",
)
items = [
    {
        "name": key,
        "score": item["earned"],
        "maxScore": item["possible"],
        "visible": key.startswith("A_"),
        "feedback": "通过" if item["passed"] else "未通过",
    }
    for key, item in result["items"].items()
]
Path(os.environ["PROJECT_RESULT"]).write_text(json.dumps({
    "score": result["automatic_earned"],
    "maxScore": 100,
    "needsReview": False,
    "items": items,
    "summary": {"averageCpe": result["cpe"]},
}, ensure_ascii=False), encoding="utf-8")
"""


def build(handout, reference, output):
    for name in ("README.md", "sim.tar"):
        if not (handout / name).is_file():
            raise SystemExit(f"handout 缺少 {name}: {handout}")
    missing = [name for name in FILES if not (reference / name).is_file()]
    if missing:
        raise SystemExit(f"参考提交缺少: {', '.join(missing)}")
    notice = (
        "# 在线工程题示例说明\n\n"
        "一次提交 Part A、B、C 六个文件，满分 100，全部由程序评分："
        "Part A 20 分、Part B 30 分、Part C 50 分；无需提交报告。\n"
        "平台已在私有题包中准备模拟器源码与测试资源；下方原讲义中的分别提交、"
        "下载 handout 和填写身份信息要求不适用于此在线示例。\n\n---\n\n"
    )
    description = notice + (handout / "README.md").read_text(encoding="utf-8")
    manifest = {
        "title": "Arch Lab：Y86-64 处理器与 ncopy 优化",
        "description": description,
        "difficulty": "hard",
        "language": "c",
        "environment": {
            "systemPackages": [
                "gcc", "g++", "make", "perl", "flex", "bison", "libfl-dev", "libc6-dev",
            ],
        },
        "graderCommand": ["python3", "private/grade.py"],
        "selfCheckMinScore": 80,
        "maxScore": 100,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(manifest, ensure_ascii=False))
        archive.writestr("public/README.md", description)
        for name in ("sum", "rsum", "copy"):
            archive.writestr(
                f"public/PartA/{name}.ys",
                f"# Implement {name} according to README.md\n",
            )
        found = set()
        with tarfile.open(handout / "sim.tar") as source:
            for member in source.getmembers():
                if not member.isfile():
                    continue
                path = PurePosixPath(member.name)
                if (not path.parts or path.parts[0] != "sim" or
                        any(part in (".", "..") for part in path.parts)):
                    raise SystemExit(f"sim.tar 中的路径无效: {member.name}")
                relative = "/".join(path.parts[1:])
                data = source.extractfile(member).read()
                info = zipfile.ZipInfo(f"private/handout/sim/{relative}")
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (member.mode & 0o777) << 16
                archive.writestr(info, data)
                if relative in PUBLIC_FROM_HANDOUT:
                    archive.writestr(f"public/{PUBLIC_FROM_HANDOUT[relative]}", data)
                    found.add(relative)
        if found != set(PUBLIC_FROM_HANDOUT):
            raise SystemExit(f"sim.tar 缺少公开初始文件: {set(PUBLIC_FROM_HANDOUT) - found}")
        archive.write(HERE / "grade_archlab.py", "private/grade_archlab.py")
        archive.writestr("private/grade.py", GRADE_ENTRY)
        for name in FILES:
            archive.write(reference / name, f"private/selfcheck/{name}")
    print(f"生成 {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handout", type=Path, required=True,
                        help="已解压的课程 handout 目录，内有 README.md 和 sim.tar")
    parser.add_argument("--reference", type=Path, required=True,
                        help="教师可用的六文件参考提交根目录")
    parser.add_argument("--output", type=Path, default=HERE / "archlab-project-demo.zip")
    arguments = parser.parse_args()
    build(arguments.handout, arguments.reference, arguments.output)
