from django.db import models

from user.models import User


class Problem(models.Model):
    """
    题库中的题目。

    分工程题（初始仓库 + 修复 / 补测试等任务）与算法题两类；
    题面 description 存 Markdown 文本。测试样例见 TestSample：
    样例测试对学生可见，隐藏测试仅用于判分。
    """

    TYPE_ENGINEERING = "engineering"
    TYPE_ALGORITHM = "algorithm"
    TYPE_CHOICES = [
        (TYPE_ENGINEERING, "工程题"),
        (TYPE_ALGORITHM, "算法题"),
    ]

    LANGUAGE_PYTHON = "python"
    LANGUAGE_CPP = "cpp"
    LANGUAGE_C = "c"
    LANGUAGE_JAVA = "java"
    LANGUAGE_CHOICES = [
        (LANGUAGE_PYTHON, "Python"),
        (LANGUAGE_CPP, "C++"),
        (LANGUAGE_C, "C"),
        (LANGUAGE_JAVA, "Java"),
    ]

    DIFFICULTY_EASY = "easy"
    DIFFICULTY_MEDIUM = "medium"
    DIFFICULTY_HARD = "hard"
    DIFFICULTY_CHOICES = [
        (DIFFICULTY_EASY, "简单"),
        (DIFFICULTY_MEDIUM, "中等"),
        (DIFFICULTY_HARD, "困难"),
    ]

    title = models.CharField(max_length=128, verbose_name="题目标题")
    description = models.TextField(blank=True, default="", verbose_name="题面（Markdown）")
    type = models.CharField(
        max_length=16,
        choices=TYPE_CHOICES,
        default=TYPE_ENGINEERING,
        verbose_name="题型",
    )
    language = models.CharField(
        max_length=16,
        choices=LANGUAGE_CHOICES,
        default=LANGUAGE_PYTHON,
        verbose_name="判题语言",
    )
    difficulty = models.CharField(
        max_length=16,
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_MEDIUM,
        verbose_name="难度",
    )
    # 工程题为初始代码 / 仓库说明，算法题为函数骨架
    starter_code = models.TextField(blank=True, default="", verbose_name="初始代码")
    # 依赖镜像名（预留字段；当前判题统一使用 settings.JUDGE_IMAGE）
    image = models.CharField(max_length=128, blank=True, default="", verbose_name="依赖镜像")
    # 判题资源限制（每个测试用例）
    time_limit_ms = models.PositiveIntegerField(default=2000, verbose_name="单用例时限（毫秒）")
    memory_limit_mb = models.PositiveIntegerField(default=256, verbose_name="内存上限（MB）")
    output_limit_kb = models.PositiveIntegerField(default=1024, verbose_name="输出上限（KB）")
    # 是否开放给学生在「自由练习」中作答（部分题目开放，不要求全部）
    practice_enabled = models.BooleanField(default=True, verbose_name="开放自由练习")
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="problems",
        verbose_name="创建人",
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.title}（{self.get_type_display()}）"


class TestSample(models.Model):
    """
    题目的测试样例。

    is_sample=True 为样例测试（作答页对学生可见），False 为隐藏测试
    （仅判题沙箱可见，不会下发给前端学生端）。
    """

    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="samples",
        verbose_name="所属题目",
    )
    name = models.CharField(max_length=64, verbose_name="用例名称")
    input_data = models.TextField(blank=True, default="", verbose_name="输入")
    expected_output = models.TextField(blank=True, default="", verbose_name="期望输出")
    is_sample = models.BooleanField(default=True, verbose_name="是否样例（学生可见）")
    created = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.problem.title} · {self.name}"
