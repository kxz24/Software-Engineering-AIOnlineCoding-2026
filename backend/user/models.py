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
