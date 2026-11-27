# -*- coding: utf-8 -*-
"""建议模式（limited）的确定性回复守卫。

仅靠系统提示词约束模型并不可靠：考生可以直接要求「给我完整代码」。
这里在服务端做兜底——二级会话的回复会先经过 sanitize_advise_text：
  * 删除 Markdown 代码块（```...```），包括未闭合的代码块；
  * 连续 3 行以上看起来像代码的内容整体替换为提示语；
  * 过长的行内代码（>= 120 字符）替换为提示语。

实验分支另提供 scoped_violation / sanitize_scoped_text：只有精确问某处实现时，
才允许一处短行内示例。其余情况继续保留概念性说明。
"""
import re

CODE_BLOCK_PLACEHOLDER = "（建议模式不展示完整代码，请根据上面的思路自行实现。）"

_FENCED = re.compile(r"```.*?```", re.DOTALL)

# 代码行特征：只匹配常见的语句开头，避免误伤中文说明
_CODE_LINE = re.compile(
    r"^\s*(?:#include|using\s+namespace|def\s+\w+\s*\(|class\s+\w+|import\s+\w+|"
    r"from\s+\w+\s+import|for\s*(?:\(|\w+\s+in\s+)|while\s*(?:\(|\w)|"
    r"if\s*(?:\(|\w)|elif\s+|else\s*:|return\b|print\s*\(|"
    r"public\s+(?:class|static)|private\s+|protected\s+|"
    r"System\.out|console\.log|int\s+main|void\s+\w+\s*\(|"
    r"[\w\[\]\.]+\s*(?:\+=|-=|\*=|/=|//=|%=|=)\s*[^=].*;?\s*$)"
)

_LONG_INLINE = re.compile(r"`([^`]{120,})`")
_EXECUTABLE_INLINE = re.compile(
    r"`[^`\n]*(?:\b(?:if|for|while|return|print)\b|(?<![<>=!])=(?!=)|==|<=|>=|!=)[^`\n]*`"
)
_IMPORT_STATEMENT = re.compile(
    r"\b(?:import\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*|"
    r"from\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s+import\s+[A-Za-z_]\w*)\b"
)


def _looks_like_code(line):
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in ("```", "~~~"):
        return True
    return bool(_CODE_LINE.match(line))


def _strip_code_runs(text):
    """把连续 3 行以上的代码行替换为提示语；行间空行不计入但保留分组。"""
    lines = text.splitlines()
    result = []
    run = []

    def flush():
        nonlocal run
        code_lines = [line for line in run if _looks_like_code(line)]
        if len(code_lines) >= 3:
            result.append(CODE_BLOCK_PLACEHOLDER)
        else:
            result.extend(run)
        run = []

    for line in lines:
        if _looks_like_code(line):
            run.append(line)
        elif not line.strip() and run:
            # 代码块内部的空行先保留，若后续不再是代码，会随之按普通文本输出
            run.append(line)
        else:
            flush()
            result.append(line)
    flush()
    return "\n".join(result)


def sanitize_advise_text(text):
    """建议模式回复过滤：去掉完整代码块，保留解释与思路。"""
    text = str(text or "")
    if not text.strip():
        return ""

    # 未闭合的代码块：从最后一个 ``` 起全部隐藏
    if text.count("```") % 2 == 1:
        text = text[: text.rfind("```")] + "\n" + CODE_BLOCK_PLACEHOLDER

    text = _FENCED.sub(CODE_BLOCK_PLACEHOLDER, text)
    text = _LONG_INLINE.sub(CODE_BLOCK_PLACEHOLDER, text)
    text = _EXECUTABLE_INLINE.sub(CODE_BLOCK_PLACEHOLDER, text)
    text = _strip_code_runs(text)
    return text.strip()


def conservative_violation(text):
    """Cheap, deterministic backstop for obvious implementation leakage."""
    text = str(text or "")
    if _FENCED.search(text) or text.count("```") % 2:
        return "候选回答包含代码块；请只用自然语言说明概念。"
    if _EXECUTABLE_INLINE.search(text):
        return "候选回答包含可直接照写的行内语句；请删去表达式。"
    if sanitize_advise_text(text) != text.strip():
        return "候选回答包含可执行代码；请改为自然语言。"
    if len(text) > 450:
        return "回答过长，可能已经把整题实现步骤讲完；只回答当前问题，控制在 400 字左右。"
    return ""


_LOCAL_REQUEST = re.compile(
    r"(?:这[一]?行|第.{0,5}行|这段代码|这个变量|\b[a-zA-Z_][a-zA-Z_0-9]*\b.{0,12}"
    r"(?:边界|赋值|报错|怎么写|怎么改)|具体哪[一]?处|错误信息|报错位置)"
)


def localized_request(question):
    """A conservative signal that the student identified a specific code location."""
    return bool(_LOCAL_REQUEST.search(str(question or "")))


def diagnostic_only_request(question):
    """A located error question asking for cause, without requesting a fix."""
    question = str(question or "")
    return (bool(re.search(r"哪里出错|哪里错|什么原因|为什么报错|报错是什么意思|为何报错", question))
            and not bool(re.search(r"(?:怎么|如何)(?:修|改|解决|处理|写|调)|修复|修正|改成", question)))


def asks_for_check_targets_only(question):
    """The student requests a list of places/cases to inspect, not their verdicts."""
    question = str(question or "")
    return (bool(re.search(r"哪些|哪几(?:种|类|处)|什么(?:部分|位置|情况|因素|对象|文件)|先看哪里|重点检查什么", question))
            and bool(re.search(r"检查|关注|先看|排查|观察|考虑", question))
            and not bool(re.search(r"(?:怎么|如何)(?:判断|判定|处理|解决|实现|写|改|检查|排查|验证|计算)|"
                                   r"(?:分别|具体)(?:怎么|如何|判断|判定)|判定条件|完整做法", question)))


def _unrequested_case_verdicts(question, text):
    if not asks_for_check_targets_only(question):
        return False
    # A single condition may explain why an object matters. Multiple conditional
    # rules or an output verdict turn an inspection list into the next solution step.
    rules = re.findall(r"只要|一旦|如果|若(?=[^，。；\n]{1,24}(?:就|则|时))|取决于|"
                       r"(?<=[，。；\n])当[^，。；\n]{1,24}时|(?<=[，。；\n])[^，。；\n]{1,24}则", text)
    verdict = re.search(r"(?:答案|结果|输出|返回)[^。；\n]{0,25}"
                        r"(?:Yes|No|true|false|成立|不成立|成功|失败|定了|确定|可判|已知)",
                        text, re.IGNORECASE)
    return bool(verdict or len(rules) >= 2)


def trim_unrequested_list_tail(question, text):
    """A check-target list is complete at its last item; drop unsolicited epilogues."""
    if not asks_for_check_targets_only(question):
        return text
    lines = text.splitlines()
    item = r"^\s*(?:[-*]|\d+[.)])\s+"
    first_item = next((index for index, line in enumerate(lines)
                       if re.match(item, line)), None)
    if first_item is None:
        return text
    for index in range(first_item + 1, len(lines)):
        if not lines[index].strip():
            next_line = next((line for line in lines[index + 1:] if line.strip()), "")
            if next_line and not re.match(item, next_line):
                return "\n".join(lines[:index]).rstrip()
    return text


def extract_scope_targets(question, reviewed_text):
    """Retain only short target names from a semantically approved scope reply."""
    if not asks_for_check_targets_only(question):
        return ""
    names = []
    for line in reviewed_text.splitlines():
        item = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$", line)
        if not item:
            continue
        bold_heading = re.match(r"\*\*([^*]{1,45})\*\*", item.group(1))
        heading = (bold_heading.group(1) if bold_heading else
                   re.split(r"[:：。；—]", item.group(1), maxsplit=1)[0])
        heading = heading.strip(" *`\t")
        if (not heading or len(heading) > 45
                or re.match(r"^(?:注意|提醒|补充|总结|不要|还要|接下来)", heading)
                or re.search(r"[=<>]|答案|输出|返回|如果|只要|取决于", heading)):
            continue
        if heading not in names:
            names.append(heading)
        if len(names) == 6:
            break
    if not names:
        return ""
    result = "可以先检查这些对象：\n" + "\n".join(f"- {name}" for name in names)
    return result if not scoped_violation(question, result) else ""


def _single_fenced_line(text):
    matches = list(_FENCED.finditer(text))
    if len(matches) != 1:
        return ""
    lines = matches[0].group(0).splitlines()
    body = [line.strip() for line in lines[1:-1] if line.strip()]
    if len(body) != 1 or len(body[0]) > 120 or ";" in body[0]:
        return ""
    outside = text[:matches[0].start()] + text[matches[0].end():]
    if _EXECUTABLE_INLINE.search(outside):
        return ""
    return body[0]


def single_file_status_request(question):
    """Recognize a concise question about one existing file's current behavior."""
    if re.search(r"详细|逐行|展开|完整分析", question):
        return False
    return bool(re.search(
        r"(?:目前|当前|现在).{0,24}(?:文件|代码|程序|模块|实现|做了什么|作用|状态)|"
        r"(?:文件|代码|程序|模块|[A-Za-z_][\w.-]*\.[A-Za-z0-9]+).{0,24}"
        r"(?:目前|当前|现在|作用)", question))


def unverified_file_status_claim(question, text):
    """A file-status question does not establish a build or execution result."""
    status_question = single_file_status_request(question)
    execution_claim = re.search(
        r"(?:不能|无法|不可能|可能|可以|能够|会|将|不会).{0,30}"
        r"(?:汇编|编译|构建|运行|通过测试)|"
        r"(?:汇编|编译|构建|运行|测试).{0,70}"
        r"(?:不可能|可能|会|将|得到|失败|成功|通过|产物)", text)
    return bool(status_question and execution_claim)


def scoped_violation(question, text):
    """Experimental mode: allow one local line only when explicitly requested."""
    text = str(text or "")
    issues = []
    if unverified_file_status_claim(question, text):
        issues.append("学生询问当前内容；删除未经实际执行的编译、运行或测试结果推断。")
    if len(text) > 750:
        issues.append("回答过长；只解释当前问题，概念题最多用一个小例子。")
    if _unrequested_case_verdicts(question, text):
        issues.append("学生只问应检查的对象；请列出对象及其重要性，删除各情况的判定条件、结果和后续处理。")
    if (asks_for_check_targets_only(question)
            and re.search(r"只能发生在|只可能发生在|无需(?:再)?检查(?:其他|其余)|其他(?:位置|情况)都(?:不用|不必)看", text)):
        issues.append("列检查范围时不要擅自排除其他可能决定结果的对象；请保留完整检查范围。")
    if diagnostic_only_request(question):
        inline_code = re.findall(r"`([^`\n]+)`", text)
        if (_EXECUTABLE_INLINE.search(text)
                or _IMPORT_STATEMENT.search(text)
                or any(_looks_like_code(line) for line in text.splitlines())
                or any(_looks_like_code(span) for span in inline_code)):
            issues.append("学生只问报错原因；请定位原因，不主动给可照写的修复语句。")
    if _FENCED.search(text) or text.count("```") % 2:
        if not localized_request(question) or not _single_fenced_line(text):
            issues.append("不能给完整代码块；只回答学生指出的局部问题。")
        return "；".join(issues)
    inline = _EXECUTABLE_INLINE.findall(text)
    if len(inline) > 1:
        issues.append("包含多处可照写的语句；请删去可照写的表达式。")
    if inline and not localized_request(question):
        issues.append("学生没有指出具体实现位置；请只讲概念或调试方向。")
    if _strip_code_runs(text) != text.strip():
        issues.append("包含连续代码语句；请缩小到局部提示。")
    return "；".join(issues)


def sanitize_scoped_text(text, question=""):
    """Keep approved local inline hints while removing full code blocks."""
    text = str(text or "")
    if localized_request(question):
        line = _single_fenced_line(text)
        if line:
            return f"`{line}`"
    if text.count("```") % 2:
        text = text[:text.rfind("```")] + "\n" + CODE_BLOCK_PLACEHOLDER
    text = _FENCED.sub(CODE_BLOCK_PLACEHOLDER, text)
    text = _LONG_INLINE.sub(CODE_BLOCK_PLACEHOLDER, text)
    return _strip_code_runs(text).strip()
