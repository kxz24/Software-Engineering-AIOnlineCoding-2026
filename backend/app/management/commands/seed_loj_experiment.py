"""Import a paraphrased LOJ #132 exercise for the learning-process experiment."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from exam.models import Exam, ExamProblem
from problem.models import Problem, TestSample
from user.models import User


SOURCE = "https://loj.ac/problem/132"
TITLE = "[学习过程实验] LOJ #132 树状数组 3：区间修改、区间查询"
EXAM_TITLE = "[学习过程实验] LOJ 数据结构练习"


class Command(BaseCommand):
    help = "预置 LOJ #132 的本地改写题面与自制测试数据"

    def handle(self, *args, **options):
        teacher = User.objects.filter(username="teacher", role=User.ROLE_TEACHER).first()
        if teacher is None:
            raise CommandError("请先运行 python manage.py init_db")
        problem, _ = Problem.objects.update_or_create(
            title=TITLE,
            defaults={
                "type": Problem.TYPE_ALGORITHM,
                "language": Problem.LANGUAGE_PYTHON,
                "difficulty": Problem.DIFFICULTY_HARD,
                "description": (
                    "来源：LOJ #132（" + SOURCE + "）。以下为本地改写的题面；测试数据为自制。\n"
                    "给定一个长度为 n 的整数序列，处理 q 次操作：\n"
                    "1 l r x：将从 l 到 r 的每个数增加 x；\n"
                    "2 l r：输出从 l 到 r 的数之和。下标从 1 开始，区间两端均包含。\n"
                    "输入第一行为 n q，第二行为初始序列，之后 q 行为操作。每次查询输出一行。\n"
                    "原题数据规模可达 10^6，需考虑高效的数据结构。"
                ),
                "starter_code": (
                    "n, q = map(int, input().split())\n"
                    "values = list(map(int, input().split()))\n"
                    "# 继续处理 q 次操作\n"
                ),
                "time_limit_ms": 5000,
                "created_by": teacher,
            },
        )
        samples = (
            ("自制公开样例", "5 5\n1 2 3 4 5\n2 1 5\n1 2 4 3\n2 2 4\n1 1 5 -2\n2 1 3\n",
             "15\n18\n6\n", True),
            ("自制隐藏边界", "3 4\n0 0 0\n1 1 3 -2\n2 1 3\n1 2 2 5\n2 2 3\n",
             "-6\n1\n", False),
        )
        for name, input_data, expected_output, is_sample in samples:
            TestSample.objects.update_or_create(
                problem=problem, name=name,
                defaults={"input_data": input_data, "expected_output": expected_output,
                          "is_sample": is_sample},
            )
        now = timezone.now()
        exam, _ = Exam.objects.update_or_create(
            title=EXAM_TITLE,
            defaults={
                "course": "学习过程实验", "description": "观察概念、算法、实现和调试求助。",
                "start_time": now - timedelta(minutes=5),
                "end_time": now + timedelta(days=1),
                "duration_minutes": 1440, "submit_limit": 10,
                "ai_mode": Exam.AI_LIMITED, "agent_token_quota": 0,
                "status": Exam.STATUS_PUBLISHED, "created_by": teacher,
            },
        )
        ExamProblem.objects.update_or_create(
            exam=exam, problem=problem, defaults={"order": 0, "score": 100},
        )
        self.stdout.write(self.style.SUCCESS(
            f"已预置 {TITLE}；本地考试 #{exam.id}；来源 {SOURCE}"
        ))
