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


def scoped_violation(question, text):
    """Experimental mode: allow one local line only when explicitly requested."""
    text = str(text or "")
    if len(text) > 450:
        return "回答超出当前问题的范围；请控制在 400 字左右。"
    if _FENCED.search(text) or text.count("```") % 2:
        if not localized_request(question) or not _single_fenced_line(text):
            return "不能给完整代码块；只回答学生指出的局部问题。"
        return ""
    inline = _EXECUTABLE_INLINE.findall(text)
    if len(inline) > 1:
        return "包含多处可照写的语句；一次只解释学生指定的一处。"
    if inline and not localized_request(question):
        return "学生没有指出具体实现位置；请只讲概念或调试方向。"
    if _strip_code_runs(text) != text.strip():
        return "包含连续代码语句；请缩小到局部提示。"
    return ""


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
