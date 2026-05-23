"""
请求格式

语音请求结构：
- text: 语音转出的文本
- source: 来源（voice/text）
- timestamp: 时间戳（可选）
"""

from pydantic import BaseModel, Field
from typing import Optional


class VoiceRequest(BaseModel):
    """语音请求格式"""
    text: str = Field(..., description="语音转出的文本")
    source: str = Field(default="voice", description="来源：voice/text")
    timestamp: Optional[int] = Field(default=None, description="时间戳")


class WakeupRequest(BaseModel):
    """唤醒信号请求"""
    source: str = Field(default="wakeup", description="唤醒信号标识")