# -*- coding: utf-8 -*-
"""默认输出比对：忽略行末空白与文件末尾空行，统一换行符。"""


def normalize_output(text):
    if text is None:
        return ""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def outputs_match(expected, actual):
    """标准输出比对；首版不支持 Special Judge。"""
    return normalize_output(expected) == normalize_output(actual)
