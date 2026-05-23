"""
响应解析服务

职责：
- 解析 LLM 响应中的 action 标签
- 将响应分割为消息块
"""

import re
from typing import List

from app.schemas import MessageBlock


def parse_action_tags(content: str) -> List[MessageBlock]:
    """
    解析 <action> 标签，将消息分割成多个消息块

    Args:
        content: LLM 响应文本

    Returns:
        MessageBlock 列表
    """
    if not content:
        return []

    pattern = r'<action>(.*?)</action>'
    matches = list(re.finditer(pattern, content, re.DOTALL))

    if not matches:
        return [MessageBlock(type="text", text=content.strip())]

    blocks: List[MessageBlock] = []

    # 处理第一个 action 之前的文本
    first_action_start = matches[0].start()
    if first_action_start > 0:
        before_text = content[:first_action_start].strip()
        if before_text:
            blocks.append(MessageBlock(type="text", text=before_text))

    # 处理每个 action 及其后续文本
    for i, match in enumerate(matches):
        action_text = match.group(1).strip()
        match_end = match.end()

        if i < len(matches) - 1:
            next_match_start = matches[i + 1].start()
            after_text = content[match_end:next_match_start].strip()
        else:
            after_text = content[match_end:].strip()

        if after_text:
            blocks.append(MessageBlock(type="action_text", action=action_text, text=after_text))
        else:
            blocks.append(MessageBlock(type="action", action=action_text, text=None))

    return blocks