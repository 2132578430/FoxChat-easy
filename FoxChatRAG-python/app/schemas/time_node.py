"""
时间节点 Schema 定义

阶段2最小时间语义机制，支持"明天/下周"类未来事项的到期激活。

第一版范围：
- 只处理 day 精度（明天/后天/下周）
- 状态机简化为 pending → active → done
- 不处理复杂时间表达（如"出成绩那天"）
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class TimeNodeStatus(StrEnum):
    """时间节点状态"""
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"


class TimePrecision(StrEnum):
    """时间精度"""
    DAY = "day"
    DATETIME = "datetime"


class CreatedFrom(StrEnum):
    """时间节点来源"""
    USER_FUTURE_EVENT = "user_future_event"
    USER_FUTURE_FOLLOWUP = "user_future_followup"
    AI_COMMITMENT = "ai_commitment"


class TimeNode(BaseModel):
    """
    时间节点对象

    职责：保存"未来某个时间点应该重新浮现"的事项，到期时激活。
    不常驻注入 Prompt，而是转成 B 层 unfinished_items 或辅助触发 C 层检索。
    """
    time_node_id: str = Field(description="唯一标识，格式：tn_<YYYYMMDD>_<sequence>")
    content: str = Field(description="到期后应重新浮现的事项")
    due_at: str = Field(description="归一化时间锚点（ISO date 或 datetime）")
    precision: TimePrecision = Field(default=TimePrecision.DAY, description="时间精度")
    status: TimeNodeStatus = Field(default=TimeNodeStatus.PENDING, description="节点状态")
    created_from: CreatedFrom = Field(description="来源类型")
    source_round: int = Field(default=0, ge=0, description="来源轮次")
    created_at: str = Field(default="", description="创建时间（ISO datetime）")
    updated_at: str = Field(default="", description="更新时间（ISO datetime）")

    def is_due(self, current_time: datetime) -> bool:
        """
        判断是否已到期

        Args:
            current_time: 当前时间

        Returns:
            是否到期
        """
        if self.status != TimeNodeStatus.PENDING:
            return False

        try:
            if self.precision == TimePrecision.DAY:
                due_date = datetime.strptime(self.due_at, "%Y-%m-%d")
                return current_time.date() >= due_date.date()
            else:
                due_datetime = datetime.fromisoformat(self.due_at)
                return current_time >= due_datetime
        except (ValueError, TypeError):
            return False

    def mark_active(self):
        """标记为激活状态"""
        self.status = TimeNodeStatus.ACTIVE
        self.updated_at = datetime.now().isoformat()

    def mark_done(self):
        """标记为完成状态"""
        self.status = TimeNodeStatus.DONE
        self.updated_at = datetime.now().isoformat()


class TimeNodeList(BaseModel):
    """时间节点列表（用于 Redis 存储）"""
    nodes: list[TimeNode] = Field(default_factory=list)

    def get_pending_nodes(self) -> list[TimeNode]:
        """获取所有 pending 状态的节点"""
        return [n for n in self.nodes if n.status == TimeNodeStatus.PENDING]

    def get_active_nodes(self) -> list[TimeNode]:
        """获取所有 active 状态的节点"""
        return [n for n in self.nodes if n.status == TimeNodeStatus.ACTIVE]

    def add_node(self, node: TimeNode):
        """添加新节点"""
        self.nodes.append(node)

    def update_node(self, time_node_id: str, **updates):
        """更新指定节点"""
        for node in self.nodes:
            if node.time_node_id == time_node_id:
                for key, value in updates.items():
                    if hasattr(node, key):
                        setattr(node, key, value)
                node.updated_at = datetime.now().isoformat()
                break