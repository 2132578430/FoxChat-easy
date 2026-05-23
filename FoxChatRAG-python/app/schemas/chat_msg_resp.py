from typing import List, Literal

from pydantic import BaseModel


class MessageBlock(BaseModel):
    """消息块结构，用于描述带 action 标签的消息分段"""
    type: Literal["action", "text", "action_text"]
    action: str | None = None
    text: str | None = None
