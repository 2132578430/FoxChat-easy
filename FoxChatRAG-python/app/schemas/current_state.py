"""
当前状态容器 Schema 定义（简化版 V2）

阶段2核心数据模型，用于表达"当前是什么局面"。

【V2 简化说明】2026-05-05
移除以下字段（暂时无效，保留注释供后续参考）：
- relation_state: 关系态势（暂无明确用途和提取逻辑）
- current_focus: 话题焦点（置信度不可信，暂无行为规则）
- interaction_mode: 互动方式（暂无明确用途和提取逻辑）

保留字段：
- emotion: 当前情绪（有效，有完整提取和注入逻辑）
- unfinished_items: 待跟进事项（有效，用于时间节点到期提醒）

--- 旧版字段说明（已移除，以下为历史记录）---
- relation_state: 关系态势（疏离/中性/亲近/紧张/缓和中）
- current_focus: 当前话题焦点（4-12字短语）
- interaction_mode: 当前互动方式（闲聊/安慰/陪伴等）
--- 旧版字段说明结束 ---
"""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, Field


class ItemStatus(StrEnum):
    """未完成事项状态"""
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


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


class UnfinishedItem(BaseModel):
    """未完成事项结构"""
    content: str = Field(description="事项内容")
    created_at: Optional[str] = Field(default=None, description="事项创建时间（ISO datetime）")
    due_at: Optional[str] = Field(default=None, description="预期完成时间（ISO datetime）")
    status: ItemStatus = Field(default=ItemStatus.PENDING, description="事项状态")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")
    expire_rounds: int = Field(default=6, description="相对过期轮数")
    update_round: int = Field(default=0, description="创建时的全局轮数")
    update_reason: str = Field(default="", description="更新原因")

    def is_expired(self, current_round: int) -> bool:
        """判断是否已过期"""
        if self.expire_rounds < 0:
            return False
        return (current_round - self.update_round) >= self.expire_rounds

    def is_valid_for_injection(self, current_round: int) -> bool:
        """判断是否适合注入 Prompt"""
        return self.status == ItemStatus.PENDING and not self.is_expired(current_round)


class CurrentState(BaseModel):
    """
    当前工作状态层容器（简化版 V2）

    对应 docs/layer_definition.md 中的 B 层定义：
    - 每轮常驻注入
    - 各字段独立过期
    - 注入摘要而非原始 JSON

    【V2 简化】只保留 emotion 和 unfinished_items
    """
    emotion: StateField = Field(
        default_factory=lambda: StateField(value="平静", confidence=0.5, expire_rounds=3, update_round=0),
        description="当前情绪"
    )
    unfinished_items: List[UnfinishedItem] = Field(
        default_factory=list,
        description="待跟进事项"
    )
    last_update: str = Field(default="", description="最后更新时间（ISO datetime）")
    update_source: UpdateSource = Field(default=UpdateSource.RUNTIME, description="更新来源")

    # === 旧版字段（已移除，保留注释供后续参考）===
    # relation_state: StateField = Field(
    #     default_factory=lambda: StateField(value="中性", confidence=0.5, expire_rounds=-1, update_round=0),
    #     description="关系态势"
    # )
    # current_focus: StateField = Field(
    #     default_factory=lambda: StateField(value="", confidence=0.0, expire_rounds=2, update_round=0),
    #     description="当前话题焦点"
    # )
    # interaction_mode: StateField = Field(
    #     default_factory=lambda: StateField(value="闲聊", confidence=0.5, expire_rounds=3, update_round=0),
    #     description="互动方式"
    # )
    # === 旧版字段结束 ===

    def get_valid_fields_for_injection(self, current_round: int) -> dict:
        """获取适合注入 Prompt 的有效字段（V2 简化版）"""
        result = {}

        if self.emotion.is_valid_for_injection(current_round):
            result["情绪"] = self.emotion.value

        valid_items = [
            item.content for item in self.unfinished_items
            if item.is_valid_for_injection(current_round)
        ]
        if valid_items:
            result["未完成事项"] = valid_items[:2]  # 最多注入2条

        # === 旧版字段注入（已移除）===
        # if self.relation_state.is_valid_for_injection(current_round):
        #     result["关系状态"] = self.relation_state.value
        # if self.current_focus.is_valid_for_injection(current_round) and self.current_focus.value:
        #     result["当前焦点"] = self.current_focus.value
        # if self.interaction_mode.is_valid_for_injection(current_round):
        #     result["互动方式"] = self.interaction_mode.value
        # === 旧版字段注入结束 ===

        return result