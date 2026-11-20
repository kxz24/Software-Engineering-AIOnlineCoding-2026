from django.db import models


class User(models.Model):
    """
    平台用户

    角色分为管理员 / 学生 / 教师三级，权限由 role 字段区分：
      admin    —— 平台管理，可管理账号、镜像、审计
      teacher  —— 命题、监考、评分
      student  —— 参加考试
    """

    ROLE_ADMIN = "admin"
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "管理员"),
        (ROLE_STUDENT, "学生"),
        (ROLE_TEACHER, "教师"),
    ]

    username = models.CharField(max_length=32, unique=True, verbose_name="账号")
    password = models.CharField(max_length=255, verbose_name="密码")
    nickname = models.CharField(max_length=255, verbose_name="用户名称")
    email = models.CharField(max_length=255, blank=True, default="", verbose_name="邮箱")
    role = models.CharField(
        max_length=16,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        verbose_name="角色",
    )

    created = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.username}（{self.get_role_display()}）"


class AuditLog(models.Model):
    """
    关键操作审计日志。

    登录 / 注册 / 权限变更 / 账号导入 / 题库变更等关键操作各写一条，
    供管理员查询。user 使用 SET_NULL，账号被处理时仍保留操作痕迹。
    """

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name="操作人",
    )
    action = models.CharField(max_length=64, verbose_name="动作")
    detail = models.TextField(blank=True, default="", verbose_name="详情")
    created = models.DateTimeField(auto_now_add=True, verbose_name="时间")

    def __str__(self):
        return f"[{self.created:%Y-%m-%d %H:%M:%S}] {self.action}"
