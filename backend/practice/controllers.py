# -*- coding: utf-8 -*-
"""自由练习的业务逻辑：题目、练习提交与评论区。"""
from django.db.models import Count, Q

from judge.languages import normalize_language
from problem.models import Problem
from user.controllers import record_audit
from user.models import User

from .models import PracticeSubmission, ProblemComment

COMMENT_CONTENT_LIMIT = 2000
COMMENT_CODE_LIMIT = 20000
CODE_LIMIT = 200_000


class PracticeError(Exception):
    """可直接返回给前端的业务错误。"""


def practice_problems(keyword=None, difficulty=None, language=None):
    """开放自由练习的算法题（工程题不参与自动判题）。"""
    query = (
        Problem.objects.filter(type=Problem.TYPE_ALGORITHM, practice_enabled=True)
        .annotate(comment_count=Count("comments", distinct=True))
    )
    if keyword:
        query = query.filter(
            Q(title__icontains=keyword) | Q(description__icontains=keyword)
        )
    if difficulty:
        query = query.filter(difficulty=difficulty)
    if language:
        query = query.filter(language=language)
    return query.order_by("-updated")


def get_practice_problem(problem_id):
    return (
        Problem.objects.filter(
            id=problem_id,
            type=Problem.TYPE_ALGORITHM,
            practice_enabled=True,
        )
        .annotate(comment_count=Count("comments", distinct=True))
        .first()
    )


def problem_summary(problem):
    sample_count = problem.samples.filter(is_sample=True).count()
    hidden_count = problem.samples.filter(is_sample=False).count()
    return {
        "id": problem.id,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "language": problem.language,
        "type": problem.type,
        "sampleCount": sample_count,
        "testCount": sample_count + hidden_count,
        "commentCount": (
            problem.comment_count
            if getattr(problem, "comment_count", None) is not None
            else problem.comments.count()
        ),
        "updated": problem.updated.isoformat() if problem.updated else None,
    }


def problem_detail(problem):
    samples = problem.samples.filter(is_sample=True).order_by("id")
    return {
        **problem_summary(problem),
        "description": problem.description,
        "starterCode": problem.starter_code,
        "timeLimitMs": problem.time_limit_ms,
        "samples": [
            {
                "name": sample.name,
                "input": sample.input_data,
                "expected": sample.expected_output,
            }
            for sample in samples
        ],
    }


# ---------------------------------------------------------------------------
# 练习提交
# ---------------------------------------------------------------------------
def submission_payload(submission):
    return {
        "id": submission.id,
        "problemId": submission.problem_id,
        "status": submission.status,
        "verdict": submission.verdict,
        "passedCount": submission.passed_count,
        "totalCount": submission.total_count,
        "samplePassed": submission.sample_passed,
        "sampleTotal": submission.sample_total,
        "hiddenPassed": submission.hidden_passed,
        "hiddenTotal": submission.hidden_total,
        "timeMs": submission.time_ms,
        "memoryKb": submission.memory_kb,
        "results": submission.results or [],
        "compileOutput": submission.compile_output,
        "judgeError": submission.judge_error,
        "created": submission.created.isoformat() if submission.created else None,
        "judgedAt": submission.judged_at.isoformat() if submission.judged_at else None,
    }


def create_submission(student, problem, code, language=""):
    """创建一次练习提交并投递给判题队列。"""
    code = str(code or "")
    if not code.strip():
        raise PracticeError("代码不能为空")
    if len(code) > CODE_LIMIT:
        raise PracticeError("代码过长（上限 200 KB）")

    normalized = normalize_language(language, problem.language)
    if normalized is None:
        raise PracticeError(f"不支持的判题语言: {language or problem.language}")

    submission = PracticeSubmission.objects.create(
        problem=problem,
        student=student,
        code=code,
        language=normalized,
    )
    record_audit(student, "practice.submit", f"题目 {problem.id} 练习提交")

    from .tasks import enqueue

    enqueue(submission.id)
    submission.refresh_from_db()
    return submission


# ---------------------------------------------------------------------------
# 评论区
# ---------------------------------------------------------------------------
def comment_payload(comment):
    return {
        "id": comment.id,
        "username": comment.author.username,
        "nickname": comment.author.nickname,
        "content": comment.content,
        "code": comment.code,
        "language": comment.language,
        "parentId": comment.parent_id,
        "created": comment.created.isoformat() if comment.created else None,
    }


def list_comments(problem, limit=100):
    return (
        problem.comments.select_related("author")
        .order_by("-created", "-id")[: max(1, min(limit, 200))]
    )


def create_comment(author, problem, content, code, language, parent_id=None):
    content = str(content or "").strip()
    code = str(code or "")
    if not content and not code.strip():
        raise PracticeError("评论内容和代码不能同时为空")
    if len(content) > COMMENT_CONTENT_LIMIT:
        raise PracticeError(f"评论过长（上限 {COMMENT_CONTENT_LIMIT} 字）")
    if len(code) > COMMENT_CODE_LIMIT:
        raise PracticeError(f"附带代码过长（上限 {COMMENT_CODE_LIMIT} 字）")

    parent = None
    if parent_id not in (None, ""):
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            raise PracticeError("parentId 必须是整数")
        parent = ProblemComment.objects.filter(id=parent_id, problem=problem).first()
        if parent is None:
            raise PracticeError("回复的评论不存在")
        # 只保留两级：回复的回复挂到顶层评论下
        parent = parent.parent or parent

    choices = [key for key, _ in Problem.LANGUAGE_CHOICES]
    if language not in choices:
        language = problem.language
    return ProblemComment.objects.create(
        problem=problem,
        author=author,
        content=content,
        code=code,
        language=language,
        parent=parent,
    )


def can_delete_comment(user, comment):
    return comment.author_id == user.id or user.role in (
        User.ROLE_TEACHER, User.ROLE_ADMIN
    )
