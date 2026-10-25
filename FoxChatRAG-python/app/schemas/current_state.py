"""
当前状态容器 Schema 定义

用于表达"当前是什么局面"。T2a 起只保留 mood 字段。
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.mood import MoodState


class UpdateSource(StrEnum):
    """状态更新来源"""
    RUNTIME = "runtime"
    SUMMARY = "summary"
    USER_EXPLICIT = "user_explicit"


class CurrentState(BaseModel):
    """当前工作状态容器（T2a 起只保留 mood）"""

    mood: MoodState = Field(default_factory=MoodState, description="当前情绪状态")
    last_update: str = Field(default="", description="最后更新时间（ISO datetime）")
    update_source: UpdateSource = Field(default=UpdateSource.RUNTIME, description="更新来源")
