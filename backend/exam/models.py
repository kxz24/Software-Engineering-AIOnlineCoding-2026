from django.db import models

from problem.models import Problem
from user.models import User


class Exam(models.Model):
    """
    一场考试。创建后为草稿，发布后学生可见，结束后可归档。

    名单为空表示对本课程全体学生开放（candidate_count 返回学生总数）。
    """

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "草稿"),
        (STATUS_PUBLISHED, "已发布"),
        (STATUS_ARCHIVED, "已归档"),
    )

    AI_LIMITED = "limited"
    AI_OPEN = "open"
    AI_CLOSED = "closed"
    AI_MODE_CHOICES = (
        (AI_LIMITED, "受限"),
        (AI_OPEN, "开放"),
        (AI_CLOSED, "关闭"),
    )

    title = models.CharField(max_length=128)
    course = models.CharField(max_length=64, blank=True, default="")
    description = models.TextField(blank=True, default="")
    notice = models.TextField(blank=True, default="")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=120)
    submit_limit = models.PositiveIntegerField(default=2)
    ai_mode = models.CharField(max_length=16, choices=AI_MODE_CHOICES, default=AI_LIMITED)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    candidates = models.ManyToManyField(User, through="ExamCandidate", related_name="exams")
    problems = models.ManyToManyField(Problem, through="ExamProblem", related_name="exams")
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_exams"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]
        verbose_name = "考试"
        verbose_name_plural = "考试"

    def __str__(self):
        return self.title


class ExamProblem(models.Model):
    """组卷条目：题目在考试中的顺序与分值。"""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_problems")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="problem_exams")
    order = models.PositiveIntegerField(default=0)
    score = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("exam", "problem")
        verbose_name = "考试题目"
        verbose_name_plural = "考试题目"


class ExamCandidate(models.Model):
    """考生名单条目；名单为空表示全体学生。"""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_candidates")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="candidate_entries")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("exam", "student")
        verbose_name = "考生"
        verbose_name_plural = "考生"


class Submission(models.Model):
    """
    学生的一次代码提交。

    当前阶段只负责收卷存档（status 固定为 pending），
    判题服务接入后回填判定结果。
    """

    STATUS_PENDING = "pending"
    STATUS_JUDGED = "judged"
    STATUS_CHOICES = (
        (STATUS_PENDING, "待判分"),
        (STATUS_JUDGED, "已判分"),
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    code = models.TextField(blank=True, default="")
    language = models.CharField(max_length=16, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "提交记录"
        verbose_name_plural = "提交记录"

    def __str__(self):
        return f"{self.student.username}@{self.exam.title}#{self.problem_id}"
