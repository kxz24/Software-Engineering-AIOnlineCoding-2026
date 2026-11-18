from django.db import models

from judge.constants import STATUS_CHOICES as SUBMISSION_STATUS_CHOICES
from judge.constants import VERDICT_CHOICES
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
    # 每生本场考试的 AI token 上限（输入 + 输出），0 表示不限
    agent_token_quota = models.PositiveIntegerField(default=0, verbose_name="每生 AI token 上限")
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

    提交时只落库存档（status=pending），由 Celery 判题任务异步回填
    status / verdict / score 与用例级结果（见 judge 应用）。
    """

    STATUS_PENDING = "pending"
    STATUS_JUDGING = "judging"
    STATUS_JUDGED = "judged"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = SUBMISSION_STATUS_CHOICES

    VERDICT_ACCEPTED = "accepted"
    VERDICT_PARTIAL = "partial"
    VERDICT_WRONG_ANSWER = "wrong_answer"
    VERDICT_TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    VERDICT_MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    VERDICT_OUTPUT_LIMIT_EXCEEDED = "output_limit_exceeded"
    VERDICT_RUNTIME_ERROR = "runtime_error"
    VERDICT_COMPILE_ERROR = "compile_error"
    VERDICT_SYSTEM_ERROR = "system_error"
    VERDICT_CHOICES = VERDICT_CHOICES

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    code = models.TextField(blank=True, default="")
    language = models.CharField(max_length=16, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # 判题结果（判题任务回填）
    verdict = models.CharField(
        max_length=32, choices=VERDICT_CHOICES, blank=True, default=""
    )
    score = models.PositiveIntegerField(default=0, verbose_name="本次得分")
    passed_count = models.PositiveIntegerField(default=0, verbose_name="通过用例数")
    total_count = models.PositiveIntegerField(default=0, verbose_name="用例总数")
    sample_passed = models.PositiveIntegerField(default=0, verbose_name="样例通过数")
    sample_total = models.PositiveIntegerField(default=0, verbose_name="样例总数")
    hidden_passed = models.PositiveIntegerField(default=0, verbose_name="隐藏用例通过数")
    hidden_total = models.PositiveIntegerField(default=0, verbose_name="隐藏用例总数")
    time_ms = models.PositiveIntegerField(default=0, verbose_name="最大耗时（毫秒）")
    memory_kb = models.PositiveIntegerField(default=0, verbose_name="峰值内存（KB）")
    compile_output = models.TextField(blank=True, default="", verbose_name="编译输出")
    judge_error = models.TextField(blank=True, default="", verbose_name="判题错误")
    needs_review = models.BooleanField(default=False, verbose_name="需人工复核")
    judge_started_at = models.DateTimeField(
        null=True, blank=True, verbose_name="判题开始时间"
    )
    judged_at = models.DateTimeField(null=True, blank=True, verbose_name="判题完成时间")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "提交记录"
        verbose_name_plural = "提交记录"

    def __str__(self):
        return f"{self.student.username}@{self.exam.title}#{self.problem_id}"


class SubmissionCase(models.Model):
    """
    单个测试用例的判定结果。

    隐藏用例只保留判定与耗时/内存，不保存输入、期望输出或实际输出，
    避免通过结果接口泄露题面数据。
    """

    VERDICT_CHOICES = VERDICT_CHOICES

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="cases"
    )
    case_index = models.PositiveIntegerField(verbose_name="用例序号")
    sample = models.ForeignKey(
        "problem.TestSample",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="judge_results",
    )
    is_sample = models.BooleanField(default=True, verbose_name="是否样例")
    name = models.CharField(max_length=64, verbose_name="用例名称")
    verdict = models.CharField(max_length=32, choices=VERDICT_CHOICES)
    time_ms = models.PositiveIntegerField(default=0)
    memory_kb = models.PositiveIntegerField(default=0)
    output_excerpt = models.TextField(blank=True, default="", verbose_name="输出摘要")
    error_excerpt = models.TextField(blank=True, default="", verbose_name="错误摘要")

    class Meta:
        ordering = ["case_index"]
        unique_together = ("submission", "case_index")
        verbose_name = "用例判定"
        verbose_name_plural = "用例判定"

    def __str__(self):
        return f"#{self.submission_id}-{self.case_index} {self.verdict}"
