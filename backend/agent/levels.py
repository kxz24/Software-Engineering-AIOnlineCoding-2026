# -*- coding: utf-8 -*-
"""级别定义：考试 AI 模式 → 会话级别 → 可用工具。

权限的强制点在工具注册表：二级会话的请求里根本不存在写文件工具，
模型无法通过提示词绕过。
"""
from exam.models import Exam

from .models import AgentSession

# 考试 ai_mode → 会话级别
AI_MODE_TO_LEVEL = {
    Exam.AI_CLOSED: AgentSession.LEVEL_NONE,
    Exam.AI_LIMITED: AgentSession.LEVEL_ADVISE,
    Exam.AI_OPEN: AgentSession.LEVEL_EDIT,
}

LEVEL_LABELS = {
    AgentSession.LEVEL_NONE: "无 AI",
    AgentSession.LEVEL_ADVISE: "AI 建议",
    AgentSession.LEVEL_EDIT: "AI 协作",
}

# 只读工具：读题面 / 工作区 / 自己的提交 / 跑公开样例
READ_TOOLS = (
    "list_files",
    "read_workspace",
    "get_problem",
    "list_submissions",
    "run_sample_tests",
)

# 写工具：只有三级（open）会话可见
WRITE_TOOLS = ("write_file",)

TOOLS_BY_LEVEL = {
    AgentSession.LEVEL_NONE: (),
    AgentSession.LEVEL_ADVISE: READ_TOOLS,
    AgentSession.LEVEL_EDIT: READ_TOOLS + WRITE_TOOLS,
}


def level_for_exam(exam):
    """考试配置对应的会话级别。"""
    return AI_MODE_TO_LEVEL.get(exam.ai_mode, AgentSession.LEVEL_NONE)


def tools_for_level(level):
    """该级别可用的工具名（有序）。"""
    return TOOLS_BY_LEVEL.get(level, ())


def can_edit_code(level):
    """该级别是否允许 AI 写入工作区。"""
    return level == AgentSession.LEVEL_EDIT
