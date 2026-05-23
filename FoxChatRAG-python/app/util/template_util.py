"""LangChain 模板工具模块。

提供 Prompt 模板与外部数据（如 JSON）的语法冲突解决方案。
"""

import re


def escape_template(template: str, var_names: list[str]) -> str:
    """模板转义方法，防止JSON和LangChain模板语法冲突。

    当JSON数据中的大括号与Prompt模板变量冲突时，
    先保护变量占位符，转义其他大括号，再恢复变量。

    Args:
        template: Prompt模板字符串
        var_names: 变量名列表，如 ["current_profile", "chat_history"]

    Returns:
        转义后的模板字符串

    Example:
        >>> template = "用户信息: {current_profile}\\n对话: {chat_history}"
        >>> escaped = escape_template(template, ["current_profile", "chat_history"])
        >>> # 现在 JSON 中的 {"name": "test"} 会被正确转义
    """
    for name in var_names:
        template = template.replace(f"{{{name}}}", f"__VAR_{name}__")

    template = template.replace("{", "{{").replace("}", "}}")

    for name in var_names:
        template = template.replace(f"__VAR_{name}__", f"{{{name}}}")

    return template


# ============================================================
# 内部工具函数
# ============================================================

def _strip_markdown_code_block(text: str) -> str:
    """去除 markdown 代码块包裹。"""
    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "")
    return text.strip()


def _strip_think_tags(content: str) -> str:
    """去除思考标签（think 和 CDATA）。"""
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    content = re.sub(r'<!\[CDATA\[.*?\]\]>', '', content, flags=re.DOTALL)
    return content


# ============================================================
# 公开 API
# ============================================================

def strip_all_tags(content: str) -> str:
    """去除 LLM 返回的所有 XML 标签及其内容（如 think、<action> 等）

    Args:
        content: 原始内容

    Returns:
        清理后的纯文本内容
    """
    if not content:
        return ""

    content = _strip_think_tags(content)

    # 去除所有 XML 标签（如 <action>...</action>）
    content = re.sub(r'<[a-zA-Z]+>.*?</[a-zA-Z]+>', '', content, flags=re.DOTALL)

    # 去除单独的 XML 标签（如 <end_turn>）
    content = re.sub(r'<[a-zA-Z]+>', '', content)

    return content.strip()


def strip_think_only(content: str) -> str:
    """仅去除 LLM 返回的思考标签，保留其他标签（如 <action>）

    Args:
        content: 原始内容

    Returns:
        清理后的内容（保留 action 等标签）
    """
    if not content:
        return ""

    content = _strip_think_tags(content)
    return content.strip()


def extract_json_text(raw_text: str, json_type: str = "auto") -> str:
    """从模型输出中提取 JSON 文本。

    Args:
        raw_text: LLM 返回的原始文本（可能包含 markdown 代码块等）
        json_type: JSON 类型，"object" 提取 {...}，"array" 提取 [...]，"auto" 自动判断

    Returns:
        提取出的 JSON 字符串
    """
    if not raw_text:
        return ""

    text = _strip_markdown_code_block(raw_text)

    # 自动判断类型
    if json_type == "auto":
        if text.lstrip().startswith("{"):
            json_type = "object"
        elif text.lstrip().startswith("["):
            json_type = "array"

    # 提取对应片段
    if json_type == "object":
        start, end = text.find("{"), text.rfind("}")
    elif json_type == "array":
        start, end = text.find("["), text.rfind("]")
    else:
        return text

    if start == -1 or end == -1 or end < start:
        return text
    return text[start:end + 1]


def try_parse_json(raw_text: str) -> dict | list | None:
    """尝试解析 JSON，自动处理常见格式问题。

    Args:
        raw_text: LLM 返回的原始文本

    Returns:
        解析后的 dict/list，失败返回 None
    """
    import json

    if not raw_text:
        return None

    text = _strip_markdown_code_block(raw_text)

    # 先尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 片段
    text = extract_json_text(text, "auto")

    # 尝试修复常见问题：补逗号
    fixed = re.sub(r'"\s*\n\s*"', '",\n"', text)  # "xxx"\n"yyy" → "xxx",\n"yyy"
    fixed = re.sub(r'"\s*"\s*:', '":', fixed)  # "xxx" "yyy": → "xxx": (错误格式修复)
    fixed = re.sub(r':\s*"\s*"\s*', ': "', fixed)  # : "xxx" "yyy" → : "xxx" (错误格式修复)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None