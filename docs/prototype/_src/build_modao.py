# -*- coding: utf-8 -*-
"""Build the Modao import version by removing HTML href attributes.

The visual output is identical to 本地预览版; only <a href="..."> targets are
removed, so Modao preview does not report broken links. Navigation is expected
to be wired with Modao hotspots.
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "本地预览版"
OUT = BASE / "墨刀导入版"


def main():
    OUT.mkdir(exist_ok=True)
    for path in sorted(SRC.glob("*.html")):
        html = path.read_text(encoding="utf-8")
        html = re.sub(r'(<a\b[^>]*?)\s+href="[^"]*"', r"\1", html)
        (OUT / path.name).write_text(html, encoding="utf-8")
        print(f"generated 墨刀导入版/{path.name}")


if __name__ == "__main__":
    main()
