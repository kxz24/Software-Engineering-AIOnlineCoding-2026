"""Create a local, repeatable problem set and limited-AI exam for manual review."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from exam.models import Exam, ExamProblem
from problem.models import Problem, TestSample
from user.models import User


PROBLEMS = (
    {
        "title": "[本地复现] A+B",
        "difficulty": Problem.DIFFICULTY_EASY,
        "description": "读入同一行的两个整数，输出它们的和。输入：两个空格分隔的整数。输出：一个整数。",
        "starter_code": "a, b = map(int, input().split())\nprint(0)\n",
        "samples": (("样例 1", "1 2\n", "3\n", True), ("隐藏 1", "-7 10\n", "3\n", False)),
    },
    {
        "title": "[本地复现] 括号匹配",
        "difficulty": Problem.DIFFICULTY_EASY,
        "description": "输入一行只包含 ()[]{} 的字符串。若每个右括号都与最近的同类左括号配对，输出 true，否则输出 false。",
        "starter_code": "s = input().strip()\nprint('false')\n",
        "samples": (("样例 1", "([]){}\n", "true\n", True), ("隐藏 1", "([)]\n", "false\n", False)),
    },
    {
        "title": "[本地复现] 最长无重复子串",
        "difficulty": Problem.DIFFICULTY_MEDIUM,
        "description": "输入一行由小写字母组成的字符串，输出其中不含重复字符的最长连续子串的长度。",
        "starter_code": "s = input().strip()\nprint(0)\n",
        "samples": (("样例 1", "abcabcbb\n", "3\n", True), ("隐藏 1", "bbbbb\n", "1\n", False)),
    },
    {
        "title": "[本地复现] 岛屿数量",
        "difficulty": Problem.DIFFICULTY_MEDIUM,
        "description": "第一行给出 n m，随后 n 行各有 m 个字符 0 或 1。上下相邻的 1 属于同一岛屿，输出岛屿数量。",
        "starter_code": "n, m = map(int, input().split())\ngrid = [input().strip() for _ in range(n)]\nprint(0)\n",
        "samples": (("样例 1", "3 3\n110\n010\n001\n", "2\n", True), ("隐藏 1", "4 5\n11000\n11000\n00100\n00011\n", "3\n", False)),
    },
    {
        "title": "[本地复现] 课程依赖",
        "difficulty": Problem.DIFFICULTY_MEDIUM,
        "description": "第一行 n m；之后 m 行为 a b，表示学习课程 a 前须先学 b。课程编号为 0 到 n-1。若能学完全部课程，输出 YES，否则输出 NO。",
        "starter_code": "n, m = map(int, input().split())\nprerequisites = [tuple(map(int, input().split())) for _ in range(m)]\nprint('NO')\n",
        "samples": (("样例 1", "2 1\n1 0\n", "YES\n", True), ("隐藏 1", "2 2\n1 0\n0 1\n", "NO\n", False)),
    },
    {
        "title": "[本地复现] 双有序数组中位数",
        "difficulty": Problem.DIFFICULTY_HARD,
        "description": "第一行 n m；第二、三行分别给出两个非降序整数数组。两数组总长度至少为 1。输出合并后的中位数，保留一位小数。请考虑对数级查找方法。",
        "starter_code": "n, m = map(int, input().split())\na = list(map(int, input().split())) if n else []\nb = list(map(int, input().split())) if m else []\nprint('0.0')\n",
        "samples": (("样例 1", "1 2\n1\n2 3\n", "2.0\n", True), ("隐藏 1", "2 2\n1 2\n3 4\n", "2.5\n", False)),
    },
    {
        "title": "[本地复现] 最小覆盖子串",
        "difficulty": Problem.DIFFICULTY_HARD,
        "description": "输入两行字符串 s 和 t。输出 s 中包含 t 所有字符及其出现次数的最短连续子串；若有并列，取起点最靠前的；不存在则输出空行。",
        "starter_code": "s = input().strip()\nt = input().strip()\nprint('')\n",
        "samples": (("样例 1", "ADOBECODEBANC\nABC\n", "BANC\n", True), ("隐藏 1", "a\na\n", "a\n", False)),
    },
)


class Command(BaseCommand):
    help = "预置 7 道本地练习题及一场正在进行的受限 AI 复现考试"

    def handle(self, *args, **options):
        teacher = User.objects.filter(username="teacher", role=User.ROLE_TEACHER).first()
        student = User.objects.filter(username="student", role=User.ROLE_STUDENT).first()
        if teacher is None or student is None:
            raise CommandError("请先运行 python manage.py init_db")

        now = timezone.now()
        exam, _ = Exam.objects.update_or_create(
            title="[本地复现] AI 受限模式练习",
            defaults={
                "course": "本地复现",
                "description": "用于检查受限模式回答是否包含过多可执行代码。",
                "start_time": now - timedelta(minutes=10),
                "end_time": now + timedelta(days=1),
                "duration_minutes": 1440,
                "submit_limit": 10,
                "ai_mode": Exam.AI_LIMITED,
                "agent_token_quota": 0,
                "status": Exam.STATUS_PUBLISHED,
                "created_by": teacher,
            },
        )
        for order, spec in enumerate(PROBLEMS):
            problem, _ = Problem.objects.update_or_create(
                title=spec["title"],
                defaults={
                    "description": spec["description"],
                    "type": Problem.TYPE_ALGORITHM,
                    "language": Problem.LANGUAGE_PYTHON,
                    "difficulty": spec["difficulty"],
                    "starter_code": spec["starter_code"],
                    "created_by": teacher,
                },
            )
            for name, input_data, expected_output, is_sample in spec["samples"]:
                TestSample.objects.update_or_create(
                    problem=problem,
                    name=name,
                    defaults={
                        "input_data": input_data,
                        "expected_output": expected_output,
                        "is_sample": is_sample,
                    },
                )
            ExamProblem.objects.update_or_create(
                exam=exam, problem=problem,
                defaults={"order": order, "score": 100},
            )

        self.stdout.write(self.style.SUCCESS(
            f"考试 #{exam.id} 已发布；预置 {len(PROBLEMS)} 道题。"
        ))
