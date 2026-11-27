#!/usr/bin/env python3
"""Grade an Arch Lab submission against the supplied handout in an isolated copy."""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = {
    "PartA/sum.ys": "misc/sum.ys",
    "PartA/rsum.ys": "misc/rsum.ys",
    "PartA/copy.ys": "misc/copy.ys",
    "PartB/seq-full.hcl": "seq/seq-full.hcl",
    "PartC/ncopy.ys": "pipe/ncopy.ys",
    "PartC/pipe-full.hcl": "pipe/pipe-full.hcl",
}
BUILD_FLAGS = ["CFLAGS=-Wall -O1 -g -fcommon", "LCFLAGS=-O1 -fcommon"]
BASELINE = [49, 64, 22, 600]
WITH_IADDQ = [58, 96, 22, 756]
RUBRICS = {
    "course": {
        "A_sum": 5, "A_rsum": 5, "A_copy": 5,
        "B_baseline": 5, "B_iaddq": 15,
        "C_pipe_regression": 2, "C_yis_correctness": 4,
        "C_pipe_correctness": 4, "C_performance": 30,
    },
    "auto100": {
        "A_sum": 6, "A_rsum": 7, "A_copy": 7,
        "B_baseline": 5, "B_iaddq": 25,
        "C_pipe_regression": 2, "C_yis_correctness": 4,
        "C_pipe_correctness": 4, "C_performance": 40,
    },
}


def run(args, cwd, timeout=120):
    try:
        result = subprocess.run(
            args, cwd=cwd, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=timeout, check=False,
        )
        return result.returncode == 0, result.stdout
    except subprocess.TimeoutExpired as exc:
        return False, f"Timed out after {timeout}s: {exc}"


def checks_passed(output, expected):
    return [int(n) for n in re.findall(r"All (\d+) ISA Checks Succeed", output)] == expected


def cpe_points(cpe):
    if cpe > 10.5:
        return 0.0
    if cpe < 7.5:
        return 30.0
    return round(10 * (10.5 - cpe), 2)


def register_score(result, key, points, passed, evidence):
    result["items"][key] = {
        "earned": points if passed else 0,
        "possible": points,
        "passed": bool(passed),
        "evidence": evidence[-1000:],
    }


def grade(submission, handout, manual, rubric="course"):
    weights = RUBRICS[rubric]
    result = {"items": {}, "manual": {}, "cpe": None}
    missing = [name for name in FILES if not (submission / name).is_file()]
    if missing:
        raise ValueError(f"Missing submission files: {', '.join(missing)}")
    source = handout / "sim"
    if not source.is_dir():
        raise ValueError(f"Handout sim directory missing: {source}")

    with tempfile.TemporaryDirectory(prefix="archlab-grade-") as temp:
        sim = Path(temp) / "sim"
        shutil.copytree(source, sim, ignore=shutil.ignore_patterns(
            "*.o", "*.yo", "*.exe", "ssim", "psim", "yas", "yis", "hcl2c",
            "seq-full.c", "pipe-full.c", "sdriver.ys", "ldriver.ys",
        ))
        for submitted, destination in FILES.items():
            shutil.copy2(submission / submitted, sim / destination)

        ok, log = run(["make", "-C", "misc", "all", *BUILD_FLAGS], sim, 120)
        if not ok:
            raise RuntimeError(f"Toolchain build failed:\n{log[-2000:]}")

        for name in ("sum", "rsum", "copy"):
            assembled, assembly_log = run(["./yas", f"{name}.ys"], sim / "misc")
            ran, simulation_log = run(["./yis", f"{name}.yo"], sim / "misc") if assembled else (False, assembly_log)
            passed = assembled and ran and "Status 'HLT'" in simulation_log and bool(
                re.search(r"%rax:\s+0x[0-9a-f]+\s+0x0*cba\b", simulation_log, re.I)
            )
            if name == "copy":
                memory_values = re.findall(
                    r"^0x[0-9a-f]+:\s+0x[0-9a-f]+\s+0x([0-9a-f]+)$",
                    simulation_log, re.I | re.M,
                )
                passed = passed and all(
                    int(expected, 16) in [int(value, 16) for value in memory_values]
                    for expected in ("a", "b0", "c00")
                )
            key = f"A_{name}"
            register_score(result, key, weights[key], passed, simulation_log)

        built, build_log = run(["make", "VERSION=full", *BUILD_FLAGS, "ssim"], sim / "seq")
        for label, flags, expected in (
            ("B_baseline", [], BASELINE),
            ("B_iaddq", ["TFLAGS=-i"], WITH_IADDQ),
        ):
            ok, log = run(["make", "SIM=../seq/ssim", *flags], sim / "ptest", 180) if built else (False, build_log)
            register_score(result, label, weights[label], ok and checks_passed(log, expected), log)

        built, build_log = run(["make", "VERSION=full", *BUILD_FLAGS, "psim"], sim / "pipe")
        baseline_ok, baseline_log = run(
            ["make", "SIM=../pipe/psim"], sim / "ptest", 180
        ) if built else (False, build_log)
        regression_ok = baseline_ok and checks_passed(baseline_log, BASELINE)
        register_score(result, "C_pipe_regression", weights["C_pipe_regression"], regression_ok, baseline_log)

        yis_ok, yis_log = run(["./correctness.pl"], sim / "pipe", 180) if built else (False, build_log)
        pipe_ok, pipe_log = run(["./correctness.pl", "-p"], sim / "pipe", 180) if built else (False, build_log)
        assembled, assembly_log = run(["../misc/yas", "ncopy.ys"], sim / "pipe")
        length = None
        if assembled:
            match = re.search(r"^0x([0-9a-f]+):\s*\| End:", (sim / "pipe/ncopy.yo").read_text(), re.I | re.M)
            if match:
                length = int(match.group(1), 16)
        length_ok = length is not None and length <= 1000
        result["ncopy_bytes"] = length
        register_score(result, "C_yis_correctness", weights["C_yis_correctness"], yis_ok and "68/68 pass correctness test" in yis_log and length_ok, yis_log)
        register_score(result, "C_pipe_correctness", weights["C_pipe_correctness"], pipe_ok and "68/68 pass correctness test" in pipe_log and length_ok, pipe_log)

        eligible = all(result["items"][key]["passed"] for key in (
            "C_pipe_regression", "C_yis_correctness", "C_pipe_correctness"
        ))
        benchmark_ok, benchmark_log = run(["./benchmark.pl"], sim / "pipe", 180) if eligible else (False, "Correctness gate failed")
        match = re.search(r"Average CPE\s+([0-9]+(?:\.[0-9]+)?)", benchmark_log)
        if benchmark_ok and match:
            result["cpe"] = float(match.group(1))
            benchmark_score = re.search(r"Score\s+([0-9]+(?:\.[0-9]+)?)/60(?:\.0)?", benchmark_log)
            earned = round(float(benchmark_score.group(1)) * weights["C_performance"] / 60, 2) if benchmark_score else round(cpe_points(result["cpe"]) * weights["C_performance"] / 30, 2)
        else:
            earned = 0.0
        result["items"]["C_performance"] = {
            "earned": earned, "possible": weights["C_performance"], "passed": benchmark_ok and bool(match),
            "evidence": benchmark_log[-1000:],
        }

    manual_limits = {"A_report": 5, "B_report": 10, "C_report": 10} if rubric == "course" else {}
    for key, limit in manual_limits.items():
        value = manual.get(key)
        if value is not None and (not isinstance(value, (int, float)) or not 0 <= value <= limit):
            raise ValueError(f"{key} must be between 0 and {limit}")
        result["manual"][key] = {"earned": value, "possible": limit}
    result["automatic_earned"] = round(sum(item["earned"] for item in result["items"].values()), 2)
    result["automatic_possible"] = sum(weights.values())
    result["manual_earned"] = round(sum(item["earned"] or 0 for item in result["manual"].values()), 2)
    result["manual_pending"] = sum(
        item["possible"] for item in result["manual"].values() if item["earned"] is None
    )
    result["total_confirmed"] = round(result["automatic_earned"] + result["manual_earned"], 2)
    result["total_possible_after_review"] = round(result["total_confirmed"] + result["manual_pending"], 2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=ROOT / "archlab-submission")
    parser.add_argument("--handout", type=Path, default=ROOT / "archlab/archlab-handout")
    parser.add_argument("--manual", type=Path, help="JSON with A_report, B_report, C_report")
    parser.add_argument("--rubric", choices=RUBRICS, default="course")
    parser.add_argument("--output", type=Path, default=ROOT / "grade-result.json")
    args = parser.parse_args()
    manual = json.loads(args.manual.read_text()) if args.manual else {}
    result = grade(args.submission, args.handout, manual, rubric=args.rubric)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for key, item in result["items"].items():
        print(f"{key:22} {item['earned']:5} / {item['possible']}")
    print(f"Automatic: {result['automatic_earned']}/{result['automatic_possible']}")
    print(f"Manual pending: {result['manual_pending']}")
    print(f"Confirmed total: {result['total_confirmed']}/100")
    print(f"Average CPE: {result['cpe']}")
    print(f"JSON: {args.output}")


if __name__ == "__main__":
    main()
