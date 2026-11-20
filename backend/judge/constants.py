# -*- coding: utf-8 -*-
"""
判题状态与判定结果的共享常量。

放在独立模块里，避免 exam.models 与 judge 应用之间循环导入。
"""

# ---------------------------------------------------------------------------
# 提交状态
# ---------------------------------------------------------------------------
STATUS_PENDING = "pending"
STATUS_JUDGING = "judging"
STATUS_JUDGED = "judged"
STATUS_FAILED = "failed"

STATUS_CHOICES = [
    (STATUS_PENDING, "待判分"),
    (STATUS_JUDGING, "判题中"),
    (STATUS_JUDGED, "已判分"),
    (STATUS_FAILED, "判题失败"),
]

# ---------------------------------------------------------------------------
# 判定结果（提交级与用例级共用）
# ---------------------------------------------------------------------------
VERDICT_ACCEPTED = "accepted"
VERDICT_PARTIAL = "partial"
VERDICT_WRONG_ANSWER = "wrong_answer"
VERDICT_TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
VERDICT_MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
VERDICT_OUTPUT_LIMIT_EXCEEDED = "output_limit_exceeded"
VERDICT_RUNTIME_ERROR = "runtime_error"
VERDICT_COMPILE_ERROR = "compile_error"
VERDICT_SYSTEM_ERROR = "system_error"

VERDICT_CHOICES = [
    (VERDICT_ACCEPTED, "通过"),
    (VERDICT_PARTIAL, "部分通过"),
    (VERDICT_WRONG_ANSWER, "答案错误"),
    (VERDICT_TIME_LIMIT_EXCEEDED, "超时"),
    (VERDICT_MEMORY_LIMIT_EXCEEDED, "内存超限"),
    (VERDICT_OUTPUT_LIMIT_EXCEEDED, "输出超限"),
    (VERDICT_RUNTIME_ERROR, "运行错误"),
    (VERDICT_COMPILE_ERROR, "编译错误"),
    (VERDICT_SYSTEM_ERROR, "系统错误"),
]

VERDICT_LABELS = dict(VERDICT_CHOICES)

# 提交级 verdict 的展示优先级：越靠前越优先
VERDICT_PRIORITY = [
    VERDICT_COMPILE_ERROR,
    VERDICT_SYSTEM_ERROR,
    VERDICT_TIME_LIMIT_EXCEEDED,
    VERDICT_MEMORY_LIMIT_EXCEEDED,
    VERDICT_OUTPUT_LIMIT_EXCEEDED,
    VERDICT_RUNTIME_ERROR,
    VERDICT_WRONG_ANSWER,
]
