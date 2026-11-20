# -*- coding: utf-8 -*-
"""把用例级结果汇总成提交级判定与分数。"""

from judge.constants import (
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    VERDICT_PRIORITY,
    VERDICT_SYSTEM_ERROR,
    VERDICT_WRONG_ANSWER,
)


def _group_stats(cases, is_sample):
    group = [case for case in cases if bool(case.get("is_sample")) is is_sample]
    passed = sum(1 for case in group if case.get("verdict") == VERDICT_ACCEPTED)
    return len(group), passed


def summarize(case_results, problem_score):
    """
    汇总用例结果。

    case_results: [{index, is_sample, verdict, time_ms, memory_kb, ...}]
    problem_score: 该题在 ExamProblem 中的分值
    返回可直接写入 Submission 的字段 dict。
    """
    total = len(case_results)
    passed = sum(1 for case in case_results if case.get("verdict") == VERDICT_ACCEPTED)
    sample_total, sample_passed = _group_stats(case_results, True)
    hidden_total, hidden_passed = _group_stats(case_results, False)

    if total == 0:
        return {
            "verdict": VERDICT_SYSTEM_ERROR,
            "score": 0,
            "passed_count": 0,
            "total_count": 0,
            "sample_passed": 0,
            "sample_total": 0,
            "hidden_passed": 0,
            "hidden_total": 0,
            "time_ms": 0,
            "memory_kb": 0,
            "needs_review": True,
        }

    if passed == total:
        verdict = VERDICT_ACCEPTED
    elif passed > 0:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_WRONG_ANSWER
        for candidate in VERDICT_PRIORITY:
            if any(case.get("verdict") == candidate for case in case_results):
                verdict = candidate
                break

    return {
        "verdict": verdict,
        "score": int(round(problem_score * passed / total)) if total else 0,
        "passed_count": passed,
        "total_count": total,
        "sample_passed": sample_passed,
        "sample_total": sample_total,
        "hidden_passed": hidden_passed,
        "hidden_total": hidden_total,
        "time_ms": max((int(case.get("time_ms") or 0) for case in case_results), default=0),
        "memory_kb": max((int(case.get("memory_kb") or 0) for case in case_results), default=0),
        "needs_review": False,
    }
