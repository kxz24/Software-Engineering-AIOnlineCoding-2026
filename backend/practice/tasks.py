# -*- coding: utf-8 -*-
"""自由练习的异步判题任务。"""
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from judge.constants import (
    STATUS_FAILED,
    STATUS_JUDGED,
    STATUS_JUDGING,
    STATUS_PENDING,
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    VERDICT_PRIORITY,
    VERDICT_SYSTEM_ERROR,
    VERDICT_WRONG_ANSWER,
)
from judge.languages import normalize_language
from judge.sandbox import CaseSpec, run_sandbox
from problem.models import Problem

from .models import PracticeSubmission

logger = logging.getLogger(__name__)

COMPILE_OUTPUT_LIMIT = 8192
EXCERPT_LIMIT = 1000


def _truncate(value, limit):
    return str(value or "")[:limit]


def _mark_failed(submission, message):
    with transaction.atomic():
        PracticeSubmission.objects.filter(id=submission.id).update(
            status=STATUS_FAILED,
            verdict=VERDICT_SYSTEM_ERROR,
            passed_count=0,
            total_count=0,
            sample_passed=0,
            sample_total=0,
            hidden_passed=0,
            hidden_total=0,
            time_ms=0,
            memory_kb=0,
            results=[],
            compile_output="",
            judge_error=_truncate(message, COMPILE_OUTPUT_LIMIT),
            needs_review=True,
            judged_at=timezone.now(),
        )


def _build_specs(samples):
    return [
        CaseSpec(
            index=index,
            name=sample.name,
            input_data=sample.input_data,
            expected_output=sample.expected_output,
            is_sample=sample.is_sample,
        )
        for index, sample in enumerate(samples, start=1)
    ]


def _summary_verdict(cases, passed):
    if passed == len(cases):
        return VERDICT_ACCEPTED
    if passed > 0:
        return VERDICT_PARTIAL
    for candidate in VERDICT_PRIORITY:
        if any(item["verdict"] == candidate for item in cases):
            return candidate
    return VERDICT_WRONG_ANSWER


def _judge(submission):
    problem = submission.problem
    if problem.type != Problem.TYPE_ALGORITHM:
        raise RuntimeError("只有算法题支持自动判题")

    samples = list(problem.samples.all().order_by("id"))
    if not samples:
        raise RuntimeError("题目没有测试用例，无法判分")

    language = normalize_language(submission.language, problem.language)
    if language is None:
        raise RuntimeError(f"不支持的判题语言: {submission.language or problem.language}")

    specs = _build_specs(samples)
    result = run_sandbox(
        language_key=language,
        code=submission.code,
        cases=specs,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        output_limit_kb=problem.output_limit_kb,
    )

    by_index = {int(item.get("index")): item for item in result.cases}
    cases = []
    for spec in specs:
        item = by_index.get(spec.index) or {
            "verdict": VERDICT_SYSTEM_ERROR,
            "time_ms": 0,
            "memory_kb": 0,
            "output_excerpt": "",
            "error_excerpt": "缺少该用例的判题结果",
        }
        cases.append({
            "index": spec.index,
            # 隐藏用例不暴露题面里的名称，避免猜出测试数据
            "name": spec.name if spec.is_sample else f"隐藏用例 #{spec.index}",
            "isSample": spec.is_sample,
            "verdict": item.get("verdict") or VERDICT_SYSTEM_ERROR,
            "timeMs": max(0, int(item.get("time_ms") or 0)),
            "memoryKb": max(0, int(item.get("memory_kb") or 0)),
            "outputExcerpt": (
                _truncate(item.get("output_excerpt"), EXCERPT_LIMIT)
                if spec.is_sample else ""
            ),
            "errorExcerpt": (
                _truncate(item.get("error_excerpt"), EXCERPT_LIMIT)
                if spec.is_sample else ""
            ),
        })

    passed = sum(1 for item in cases if item["verdict"] == VERDICT_ACCEPTED)
    sample_total = sum(1 for item in cases if item["isSample"])
    sample_passed = sum(
        1 for item in cases if item["isSample"] and item["verdict"] == VERDICT_ACCEPTED
    )
    hidden_total = len(cases) - sample_total
    hidden_passed = passed - sample_passed
    verdict = _summary_verdict(cases, passed)
    status = (
        STATUS_FAILED if any(item["verdict"] == VERDICT_SYSTEM_ERROR for item in cases)
        else STATUS_JUDGED
    )

    PracticeSubmission.objects.filter(id=submission.id).update(
        status=status,
        verdict=verdict,
        passed_count=passed,
        total_count=len(cases),
        sample_passed=sample_passed,
        sample_total=sample_total,
        hidden_passed=hidden_passed,
        hidden_total=hidden_total,
        time_ms=max((item["timeMs"] for item in cases), default=0),
        memory_kb=max((item["memoryKb"] for item in cases), default=0),
        results=cases,
        compile_output=_truncate(result.compile_output, COMPILE_OUTPUT_LIMIT),
        judge_error="",
        needs_review=status == STATUS_FAILED,
        judged_at=timezone.now(),
    )


@shared_task(bind=True, acks_late=True)
def judge_practice_submission(self, submission_id):
    """判一条练习提交；重复投递会因认领失败而跳过。"""
    claimed = PracticeSubmission.objects.filter(
        id=submission_id, status=STATUS_PENDING
    ).update(status=STATUS_JUDGING, judge_started_at=timezone.now())
    if not claimed:
        return {"submissionId": submission_id, "skipped": True}

    submission = (
        PracticeSubmission.objects.select_related("problem", "student")
        .filter(id=submission_id)
        .first()
    )
    if submission is None:
        return {"submissionId": submission_id, "skipped": True}

    try:
        _judge(submission)
    except Exception as exc:  # noqa: BLE001 —— 判题失败要落状态
        logger.exception("练习判题失败 submission=%s", submission_id)
        _mark_failed(submission, str(exc))
    return {"submissionId": submission_id}


def enqueue(submission_id):
    """投递给 Celery；队列不可用时把提交标记为失败，避免前端一直 pending。"""
    try:
        judge_practice_submission.delay(submission_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("练习判题任务入队失败 submission=%s", submission_id)
        PracticeSubmission.objects.filter(
            id=submission_id, status=STATUS_PENDING
        ).update(
            status=STATUS_FAILED,
            verdict=VERDICT_SYSTEM_ERROR,
            judge_error=f"判题队列不可用，请稍后重试（{exc}）"[:2000],
            judged_at=timezone.now(),
        )
