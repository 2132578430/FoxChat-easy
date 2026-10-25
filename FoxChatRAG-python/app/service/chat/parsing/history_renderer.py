"""
历史消息转写

职责：
- 把 assistant 历史回复中的 <action> 标签转成括号旁白
- 只作用于最终 LLM messages，不回写 Redis / 摘要 / 检索
"""

from app.service.chat.parsing.response_parser import parse_action_tags

HISTORY_VIEW_NOTE = (
    "【历史视图说明】以下 assistant 历史中的“（动作）”是转写标记，只用于理解发生过什么；"
    "你回复时禁止输出圆括号，动作必须使用 <action> 标签。历史只提供事实和语气，不提供排版。"
)


def render_history_content(content: str) -> str:
    """把历史 assistant 回复的动作标签转成括号旁白，避免模型逐字模仿历史排版。"""
    if not isinstance(content, str) or not content:
        return content

    blocks = parse_action_tags(content)
    if not any(block.type == "action" for block in blocks):
        return content

    parts: list[str] = []
    for block in blocks:
        segment = (block.action if block.type == "action" else block.text) or ""
        segment = segment.strip()
        if not segment:
            continue
        parts.append(f"（{segment}）" if block.type == "action" else segment)

    rendered = "".join(parts).strip()
    return rendered or content
