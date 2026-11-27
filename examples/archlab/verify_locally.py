#!/usr/bin/env python3
"""Validate and grade the teacher reference using the platform's real Docker path."""

import argparse
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

import django

django.setup()

from judge.project_environment import prepare_environment
from problem.project_package import parse_package

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    arguments = parser.parse_args()
    raw = arguments.package.read_bytes()
    metadata, public = parse_package(raw)
    bundle = SimpleNamespace(
        archive=raw,
        public_files=public,
        environment=metadata["environment"],
        runtime=metadata["runtime"],
        prepared_image="",
        max_score=metadata["max_score"],
        self_check_min_score=metadata["self_check_min_score"],
    )
    started = time.perf_counter()
    image, message = prepare_environment(bundle)
    print(f"镜像：{image}")
    print(message)
    print(f"总耗时：{time.perf_counter() - started:.2f} 秒")
