"""
当前状态容器 Schema 定义

核心数据模型，用于表达"当前是什么局面"。
当前仅保留 emotion 字段（有完整提取和注入逻辑）。
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class UpdateSource(StrEnum):
    """状态更新来源"""
    RUNTIME = "runtime"
    SUMMARY = "summary"
    USER_EXPLICIT = "user_explicit"


class StateField(BaseModel):
    """单个状态字段的通用结构"""
    value: str = Field(default="", description="状态值")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度")
    expire_rounds: int = Field(default=-1, description="相对过期轮数，-1表示永不过期")
    update_round: int = Field(default=0, description="上次更新时的全局轮数")
    update_reason: str = Field(default="", description="更新原因（调试用）")

    def is_expired(self, current_round: int) -> bool:
        """
        判断是否已过期

        Args:
            current_round: 当前全局轮数

        Returns:
            是否过期
        """
        if self.expire_rounds < 0:
            return False  # 永不过期
        return (current_round - self.update_round) >= self.expire_rounds

    def is_valid_for_injection(self, current_round: int) -> bool:
        """判断是否适合注入 Prompt"""
        return self.confidence >= 0.6 and not self.is_expired(current_round)


class CurrentState(BaseModel):
    """
    当前工作状态层容器（简化版 V2）

    对应 docs/layer_definition.md 中的 B 层定义：
    - 每轮常驻注入
    - 各字段独立过期
    - 注入摘要而非原始 JSON

    【V2 简化】只保留 emotion
    """
    emotion: StateField = Field(
        default_factory=lambda: StateField(value="平静", confidence=0.5, expire_rounds=3, update_round=0),
        description="当前情绪"
    )
    last_update: str = Field(default="", description="最后更新时间（ISO datetime）")
    update_source: UpdateSource = Field(default=UpdateSource.RUNTIME, description="更新来源")

    def get_valid_fields_for_injection(self, current_round: int) -> dict:
        """获取适合注入 Prompt 的有效字段（V2 简化版）"""
        result = {}

        if self.emotion.is_valid_for_injection(current_round):
            result["情绪"] = self.emotion.value

        return result