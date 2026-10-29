from django.core.management.base import BaseCommand

from user.models import User
from utils.jwt import encrypt_password

# 每个角色一个初始账号。重复执行会覆盖密码与角色，幂等。
SEED_ACCOUNTS = [
    ("admin", "admin123", "系统管理员", User.ROLE_ADMIN),
    ("teacher", "teacher123", "示例教师", User.ROLE_TEACHER),
    ("student", "student123", "示例学生", User.ROLE_STUDENT),
]


class Command(BaseCommand):
    help = "初始化数据库：为管理员 / 教师 / 学生各创建一个初始账号"

    def handle(self, *args, **options):
        for username, password, nickname, role in SEED_ACCOUNTS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"nickname": nickname, "role": role},
            )
            # 无论新建还是已存在，都重设密码与角色，保证脚本可重复执行
            user.password = encrypt_password(password)
            user.nickname = nickname
            user.role = role
            user.save()

            action = "创建" if created else "更新"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action}账号 {username}（{user.get_role_display()}）"
                )
            )

        self.stdout.write(self.style.SUCCESS("初始账号初始化完成"))
