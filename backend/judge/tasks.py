# -*- coding: utf-8 -*-
"""异步判题任务。"""

import json
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from exam.models import ExamProblem, Submission, SubmissionCase
from judge.constants import (
    STATUS_FAILED,
    STATUS_JUDGED,
    STATUS_JUDGING,
    STATUS_PENDING,
    VERDICT_SYSTEM_ERROR,
)
from judge.languages import normalize_language
from judge.sandbox import CaseSpec, run_sandbox
from judge.scoring import summarize
from judge.project_sandbox import run_project_sandbox
from problem.models import Problem, ProjectBundle
from user.controllers import record_audit

logger = logging.getLogger(__name__)

COMPILE_OUTPUT_LIMIT = 8192
EXCERPT_LIMIT = 2048


@shared_task(bind=True, time_limit=600, soft_time_limit=570)
def prepare_project_bundle(self, bundle_id):
    """Build a teacher-declared image and verify the private reference submission."""
    bundle = ProjectBundle.objects.get(pk=bundle_id)
    bundle.preparation_status = "preparing"
    bundle.preparation_message = "正在准备工具并试跑参考提交"
    bundle.save(update_fields=["preparation_status", "preparation_message"])
    try:
        from .project_environment import prepare_environment

        image, message = prepare_environment(bundle)
    except Exception as exc:
        logger.exception("工程题环境准备失败 bundle=%s", bundle_id)
        bundle.preparation_status = "failed"
        bundle.preparation_message = str(exc)[:1000]
        bundle.prepared_image = ""
    else:
        bundle.preparation_status = "ready"
        bundle.preparation_message = message
        bundle.prepared_image = image
    bundle.save(update_fields=["preparation_status", "preparation_message", "prepared_image"])


def _truncate(value, limit):
    return str(value or "")[:limit]


def _mark_failed(submission, message):
    """系统级失败：清空旧结果并标记为需人工复核。"""
    with transaction.atomic():
        Submission.objects.filter(id=submission.id).update(
            status=STATUS_FAILED,
            verdict=VERDICT_SYSTEM_ERROR,
            score=0,
            passed_count=0,
            total_count=0,
            sample_passed=0,
            sample_total=0,
            hidden_passed=0,
            hidden_total=0,
            time_ms=0,
            memory_kb=0,
            compile_output="",
            needs_review=True,
            judge_error=_truncate(message, COMPILE_OUTPUT_LIMIT),
            judged_at=timezone.now(),
        )
        SubmissionCase.objects.filter(submission_id=submission.id).delete()
    record_audit(
        submission.student, "submission.judged",
        f"{submission.id} system_error 需人工复核",
    )


def _build_case_specs(samples):
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


def _judge(submission):
    """执行一次判题；异常由调用方转成 failed 状态。"""
    problem = submission.problem
    if problem.type == Problem.TYPE_ENGINEERING:
        if not hasattr(problem, "project_bundle"):
            raise RuntimeError("工程题没有导入评分包，请教师人工复核")
        return _judge_project(submission)

    samples = list(problem.samples.all().order_by("id"))
    if not samples:
        raise RuntimeError("题目没有测试用例，无法判分")

    language = normalize_language(submission.language, problem.language)
    if language is None:
        raise RuntimeError(f"不支持的判题语言: {submission.language or problem.language}")

    exam_problem = ExamProblem.objects.filter(
        exam=submission.exam, problem=problem
    ).first()
    problem_score = exam_problem.score if exam_problem else 0

    specs = _build_case_specs(samples)
    result = run_sandbox(
        language_key=language,
        code=submission.code,
        cases=specs,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        output_limit_kb=problem.output_limit_kb,
    )

    by_index = {int(item.get("index")): item for item in result.cases}
    merged = []
    for spec in specs:
        item = by_index.get(spec.index) or {
            "index": spec.index,
            "verdict": VERDICT_SYSTEM_ERROR,
            "time_ms": 0,
            "memory_kb": 0,
            "output_excerpt": "",
            "error_excerpt": "缺少该用例的判题结果",
        }
        merged.append({**item, "is_sample": spec.is_sample})

    summary = summarize(merged, problem_score)
    if any(item.get("verdict") == VERDICT_SYSTEM_ERROR for item in merged):
        summary["needs_review"] = True

    status = STATUS_FAILED if summary["verdict"] == VERDICT_SYSTEM_ERROR else STATUS_JUDGED
    judged_at = timezone.now()

    with transaction.atomic():
        Submission.objects.filter(id=submission.id).update(
            status=status,
            verdict=summary["verdict"],
            score=summary["score"],
            passed_count=summary["passed_count"],
            total_count=summary["total_count"],
            sample_passed=summary["sample_passed"],
            sample_total=summary["sample_total"],
            hidden_passed=summary["hidden_passed"],
            hidden_total=summary["hidden_total"],
            time_ms=summary["time_ms"],
            memory_kb=summary["memory_kb"],
            compile_output=_truncate(result.compile_output, COMPILE_OUTPUT_LIMIT),
            judge_error="",
            needs_review=summary["needs_review"],
            judged_at=judged_at,
        )
        SubmissionCase.objects.filter(submission_id=submission.id).delete()
        SubmissionCase.objects.bulk_create([
            SubmissionCase(
                submission_id=submission.id,
                case_index=spec.index,
                sample_id=samples[spec.index - 1].id,
                is_sample=spec.is_sample,
                name=(
                    spec.name if spec.is_sample else f"隐藏用例 #{spec.index}"
                )[:64],
                verdict=item.get("verdict") or VERDICT_SYSTEM_ERROR,
                time_ms=max(0, int(item.get("time_ms") or 0)),
                memory_kb=max(0, int(item.get("memory_kb") or 0)),
                # 隐藏用例不落实际输出/错误信息，避免经结果接口泄露题面数据
                output_excerpt=(
                    _truncate(item.get("output_excerpt"), EXCERPT_LIMIT)
                    if spec.is_sample else ""
                ),
                error_excerpt=(
                    _truncate(item.get("error_excerpt"), EXCERPT_LIMIT)
                    if spec.is_sample else ""
                ),
            )
            for spec, item in zip(specs, merged)
        ])

    record_audit(
        submission.student, "submission.judged",
        f"{submission.id} {summary['verdict']} {summary['score']}分 "
        f"{summary['passed_count']}/{summary['total_count']}",
    )


def _judge_project(submission):
    """Score a multi-file submission using its teacher-owned package."""
    bundle = submission.problem.project_bundle
    try:
        files = json.loads(submission.code)["files"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("工程题提交快照无效") from exc
    result = run_project_sandbox(bundle, files)
    items = result["items"]
    maximum = bundle.max_score
    raw_score = float(result["score"])
    if not 0 <= raw_score <= maximum:
        raise RuntimeError("工程题评分超出范围")
    exam_item = ExamProblem.objects.filter(
        exam=submission.exam, problem=submission.problem
    ).first()
    possible = exam_item.score if exam_item else 0
    score = round(possible * raw_score / maximum)
    pending = bool(result.get("needsReview"))
    if raw_score >= maximum and not pending:
        verdict = "accepted"
    elif raw_score > 0:
        verdict = "partial"
    else:
        verdict = "wrong_answer"
    passed = sum(1 for item in items if item.get("score") == item.get("maxScore"))
    visible = [item for item in items if item.get("visible")]
    with transaction.atomic():
        Submission.objects.filter(id=submission.id).update(
            status=STATUS_JUDGED, verdict=verdict, score=score,
            passed_count=passed, total_count=len(items),
            sample_passed=sum(1 for item in visible if item.get("score") == item.get("maxScore")),
            sample_total=len(visible), hidden_passed=passed - sum(
                1 for item in visible if item.get("score") == item.get("maxScore")
            ), hidden_total=len(items) - len(visible),
            needs_review=pending, judge_error="", compile_output="",
            judged_at=timezone.now(),
        )
        SubmissionCase.objects.filter(submission_id=submission.id).delete()
        SubmissionCase.objects.bulk_create([
            SubmissionCase(
                submission=submission, case_index=index,
                is_sample=bool(item.get("visible")),
                name=str(item.get("name") if item.get("visible") else f"隐藏评分项 #{index}")[:64],
                verdict="accepted" if item.get("score") == item.get("maxScore") else "wrong_answer",
                output_excerpt=str(item.get("feedback") or "")[:EXCERPT_LIMIT]
                if item.get("visible") else "",
            ) for index, item in enumerate(items, 1)
        ])
    record_audit(submission.student, "submission.judged",
                 f"{submission.id} project {score}分，待复核={pending}")


@shared_task(bind=True, acks_late=True)
def judge_submission(self, submission_id):
    """
    判题任务入口。

    先以「pending → judging」原子领取任务，重复投递会直接跳过（幂等）。
    """
    claimed = Submission.objects.filter(
        id=submission_id, status=STATUS_PENDING
    ).update(status=STATUS_JUDGING, judge_started_at=timezone.now())
    if not claimed:
        return {"submissionId": submission_id, "skipped": True}

    try:
        submission = Submission.objects.select_related(
            "exam", "problem", "student"
        ).get(id=submission_id)
    except Submission.DoesNotExist:
        return {"submissionId": submission_id, "skipped": True}

    try:
        _judge(submission)
    except Exception as exc:  # noqa: BLE001 - 判题失败要落状态，不能让任务静默
        logger.exception("判题失败 submission=%s", submission_id)
        _mark_failed(submission, str(exc))

    return {"submissionId": submission_id}
