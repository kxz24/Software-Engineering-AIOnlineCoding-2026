# -*- coding: utf-8 -*-
"""自由练习：练习提交与题目评论。"""
from django.db import models

from judge.constants import STATUS_CHOICES as SUBMISSION_STATUS_CHOICES
from judge.constants import VERDICT_CHOICES
from problem.models import Problem
from user.models import User


class PracticeSubmission(models.Model):
    """学生在自由练习中的一次代码提交（与考试提交完全独立）。"""

    STATUS_CHOICES = SUBMISSION_STATUS_CHOICES

    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="practice_submissions"
    )
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="practice_submissions"
    )
    code = models.TextField(blank=True, default="")
    language = models.CharField(max_length=16, blank=True, default="")
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="pending"
    )
    verdict = models.CharField(
        max_length=32, choices=VERDICT_CHOICES, blank=True, default=""
    )
    passed_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)
    sample_passed = models.PositiveIntegerField(default=0)
    sample_total = models.PositiveIntegerField(default=0)
    hidden_passed = models.PositiveIntegerField(default=0)
    hidden_total = models.PositiveIntegerField(default=0)
    time_ms = models.PositiveIntegerField(default=0)
    memory_kb = models.PositiveIntegerField(default=0)
    # 逐用例结果（隐藏用例只保留判定与耗时/内存，不含输出）
    results = models.JSONField(default=list, blank=True, verbose_name="逐用例结果")
    compile_output = models.TextField(blank=True, default="")
    judge_error = models.TextField(blank=True, default="")
    needs_review = models.BooleanField(default=False)
    judge_started_at = models.DateTimeField(null=True, blank=True)
    judged_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["problem", "student"])]
        verbose_name = "练习提交"
        verbose_name_plural = "练习提交"

    def __str__(self):
        return f"{self.student.username}@practice#{self.problem_id}"


class ProblemComment(models.Model):
    """题目评论区的一条留言；可以附带一段代码。"""

    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="problem_comments"
    )
    content = models.TextField(blank=True, default="")
    code = models.TextField(blank=True, default="", verbose_name="附带的代码")
    # 回复关系：空表示顶层评论；回复的回复统一挂到顶层，保持两级展示
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE,
        related_name="replies", verbose_name="回复的评论",
    )
    language = models.CharField(
        max_length=16, choices=Problem.LANGUAGE_CHOICES, default=Problem.LANGUAGE_PYTHON
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-id"]
        indexes = [models.Index(fields=["problem", "created"])]
        verbose_name = "题目评论"
        verbose_name_plural = "题目评论"

    def __str__(self):
        return f"{self.author.username}@{self.problem_id}"
