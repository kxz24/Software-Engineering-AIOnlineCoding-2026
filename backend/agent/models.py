# -*- coding: utf-8 -*-
"""AI 助教的数据模型：会话、消息、工具调用、工作区与代码修改记录。

设计要点：
  * 对话与工具调用只增不改，供考试结束后的过程报告与申诉使用；
  * token 用量以模型 API 返回的 usage 为准，会话表存累计值，消息表保留原始 usage；
  * 三级模式下 AI 的写入先落到 WorkspaceFile，并生成 CodeChange，前端据此展示 diff。
"""
from django.db import models


class AgentSession(models.Model):
    """一场考试中某学生某道题的 AI 会话；按 (考试, 学生, 题目) 唯一，可续聊。"""

    LEVEL_NONE = "none"
    LEVEL_ADVISE = "advise"
    LEVEL_EDIT = "edit"
    LEVEL_CHOICES = (
        (LEVEL_NONE, "无 AI"),
        (LEVEL_ADVISE, "AI 建议"),
        (LEVEL_EDIT, "AI 协作"),
    )

    STATUS_ACTIVE = "active"
    STATUS_ENDED = "ended"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "进行中"),
        (STATUS_ENDED, "已结束"),
        (STATUS_FAILED, "异常"),
    )

    exam = models.ForeignKey(
        "exam.Exam", on_delete=models.CASCADE, related_name="agent_sessions"
    )
    student = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, related_name="agent_sessions"
    )
    problem = models.ForeignKey(
        "problem.Problem", on_delete=models.CASCADE, related_name="agent_sessions"
    )
    # 创建时从 Exam.ai_mode 快照，考试配置之后变化不影响进行中的会话
    level = models.CharField(max_length=8, choices=LEVEL_CHOICES)
    provider = models.CharField(max_length=16, default="mock")
    model = models.CharField(max_length=32, default="")
    prompt_version = models.CharField(max_length=16, default="v1")
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    # 累计用量：每轮判题结束用 F() 原子累加
    input_tokens = models.PositiveBigIntegerField(default=0)
    output_tokens = models.PositiveBigIntegerField(default=0)
    cache_hit_tokens = models.PositiveBigIntegerField(default=0)
    cache_miss_tokens = models.PositiveBigIntegerField(default=0)

    created = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("exam", "student", "problem")
        indexes = [models.Index(fields=["exam", "student"])]
        verbose_name = "AI 会话"
        verbose_name_plural = "AI 会话"

    def __str__(self):
        return f"{self.student.username}@{self.exam_id}#{self.problem_id}"


class AgentMessage(models.Model):
    """会话里的每一条消息，按 seq 递增，只增不改。"""

    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_TOOL = "tool"
    ROLE_SYSTEM = "system"
    ROLE_CHOICES = (
        (ROLE_USER, "考生"),
        (ROLE_ASSISTANT, "AI"),
        (ROLE_TOOL, "工具结果"),
        (ROLE_SYSTEM, "系统"),
    )

    session = models.ForeignKey(
        AgentSession, on_delete=models.CASCADE, related_name="messages"
    )
    seq = models.PositiveIntegerField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(blank=True, default="")
    # 学生本轮实际授予的能力；仅 user 消息使用。
    requested_action = models.CharField(max_length=8, blank=True, default="answer")
    # assistant 消息里的 tool_calls 原样保留（OpenAI 兼容格式）
    tool_calls = models.JSONField(null=True, blank=True)
    tool_call_id = models.CharField(max_length=64, blank=True, default="")
    name = models.CharField(max_length=64, blank=True, default="")
    # 模型返回的原始 usage，便于对账；累计值写在 AgentSession 上
    usage = models.JSONField(null=True, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    finish_reason = models.CharField(max_length=24, blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["session", "seq"]
        unique_together = ("session", "seq")
        verbose_name = "AI 消息"
        verbose_name_plural = "AI 消息"

    def __str__(self):
        return f"#{self.session_id}-{self.seq} {self.role}"


class AgentToolCall(models.Model):
    """一次工具调用；与消息分开存，便于统计与排查。"""

    session = models.ForeignKey(
        AgentSession, on_delete=models.CASCADE, related_name="tool_calls"
    )
    message = models.ForeignKey(
        AgentMessage, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    call_id = models.CharField(max_length=64)
    name = models.CharField(max_length=64)
    arguments = models.JSONField(default=dict)
    ok = models.BooleanField(default=True)
    result_excerpt = models.TextField(blank=True, default="")
    duration_ms = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "call_id")
        verbose_name = "工具调用"
        verbose_name_plural = "工具调用"

    def __str__(self):
        return f"{self.session_id}:{self.name}"


class WorkspaceFile(models.Model):
    """服务端工作区文件；AI 写入与前端保存都以它为准。"""

    exam = models.ForeignKey("exam.Exam", on_delete=models.CASCADE)
    student = models.ForeignKey("user.User", on_delete=models.CASCADE)
    problem = models.ForeignKey("problem.Problem", on_delete=models.CASCADE)
    path = models.CharField(max_length=128)
    content = models.TextField(blank=True, default="")
    # 乐观锁：写入必须带 expectedRevision，避免覆盖较新的内容
    revision = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("exam", "student", "problem", "path")
        indexes = [models.Index(fields=["exam", "student", "problem"])]
        verbose_name = "工作区文件"
        verbose_name_plural = "工作区文件"

    def __str__(self):
        return f"{self.student.username}:{self.path}"


class CodeChange(models.Model):
    """AI 对工作区的一次修改，保留前后正文与 diff，可撤销。"""

    STATUS_APPLIED = "applied"
    STATUS_REVERTED = "reverted"
    STATUS_CHOICES = (
        (STATUS_APPLIED, "已应用"),
        (STATUS_REVERTED, "已撤销"),
    )

    session = models.ForeignKey(
        AgentSession, on_delete=models.CASCADE, related_name="code_changes"
    )
    exam = models.ForeignKey("exam.Exam", on_delete=models.CASCADE)
    student = models.ForeignKey("user.User", on_delete=models.CASCADE)
    problem = models.ForeignKey("problem.Problem", on_delete=models.CASCADE)
    file_path = models.CharField(max_length=128)
    revision_before = models.PositiveIntegerField()
    revision_after = models.PositiveIntegerField()
    before_text = models.TextField(blank=True, default="")
    after_text = models.TextField(blank=True, default="")
    diff = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=8, choices=STATUS_CHOICES, default=STATUS_APPLIED
    )
    created = models.DateTimeField(auto_now_add=True)
    reverted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["session", "created"])]
        verbose_name = "AI 代码修改"
        verbose_name_plural = "AI 代码修改"

    def __str__(self):
        return f"change#{self.id} {self.file_path}"
