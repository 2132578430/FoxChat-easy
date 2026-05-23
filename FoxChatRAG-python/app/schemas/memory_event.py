"""
历史事件候选 Schema 定义

阶段3新增：用于表达"过去发生过、未来可能按需回忆"的事实候选。
与 memory_bank 直接追加不同，历史事件候选需先经过分流、去重、续写判断再入库。

字段说明：
- event_id: 唯一标识，用于追踪和引用
- occurred_at: 事件发生时间（ISO datetime）
- last_seen_at: 最近一次出现时间（用于续写合并）
- actor: 事件主体（USER / AI）
- type: 大类（event / state）
- event_type: 细类（share_experience, express_emotion, commitment 等）
- content: 事件本体描述
- keywords: 关键词数组，用于关键词召回
- importance: 重要程度（0-1），用于排序优先级
- source_snippet: 原文片段，防止摘要失真
- source_round: 来源轮次，用于回溯调试
- activity_score: 活性分数，后续支持事件衰减

去重依据：
- actor + type + event_type 分桶
- 时间邻近窗口内 content 相似度 + keywords 重叠率
"""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, Field


class EventActor(StrEnum):
    """事件主体"""
    USER = "USER"
    AI = "AI"
    UNKNOWN = "UNKNOWN"


class EventType(StrEnum):
    """事件大类"""
    EVENT = "event"
    STATE = "state"


class EventDetailType(StrEnum):
    """事件细类 — 与 memory_event_extractor.md event_type 完全一致"""
    # Event 类
    SHARE_EXPERIENCE = "share_experience"
    EXPRESS_EMOTION = "express_emotion"
    COMMITMENT = "commitment"
    FOLLOW_UP = "follow_up"
    RELATION_CHANGE = "relation_change"
    INTERACTION = "interaction"
    OTHER = "other"
    # State 类
    IDENTITY = "identity"
    PREFERENCE = "preference"
    BOUNDARY = "boundary"


class ChangeType(StrEnum):
    """候选变化类型（用于无变化判断）"""
    NO_CHANGE = "no_change"
    REFRESH_ONLY = "refresh_only"
    CONTENT_UPDATE = "content_update"
    NEW_ENTRY = "new_entry"


class MemoryEvent(BaseModel):
    """
    历史事件候选对象

    对应设计文档中的 C 层（历史事件检索层）：
    - 过去重要事件
    - 承诺 / 冲突 / 共同经历
    - 旧话题锚点
    """
    event_id: str = Field(default="", description="唯一标识，格式：evt_<YYYYMMDD>_<sequence>")
    occurred_at: str = Field(default="", description="事件发生时间（ISO datetime 或日期）")
    last_seen_at: str = Field(default="", description="最近一次出现时间（用于续写合并）")
    actor: EventActor = Field(default=EventActor.UNKNOWN, description="事件主体")
    type: EventType = Field(default=EventType.EVENT, description="事件大类")
    event_type: EventDetailType = Field(default=EventDetailType.OTHER, description="事件细类")
    content: str = Field(default="", description="事件本体描述，30-50字")
    keywords: List[str] = Field(default_factory=list, description="关键词数组")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要程度")
    source_snippet: str = Field(default="", description="原文片段，防止摘要失真")
    source_round: int = Field(default=0, ge=0, description="来源轮次")
    activity_score: float = Field(default=1.0, ge=0.0, le=1.0, description="活性分数")

    def is_in_short_window(self, other: "MemoryEvent", window_hours: int = 2) -> bool:
        """判断两个事件是否在短时间窗口内"""
        if not self.occurred_at or not other.occurred_at:
            return False
        try:
            t1 = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(other.occurred_at.replace("Z", "+00:00"))
            delta = abs((t1 - t2).total_seconds())
            return delta <= window_hours * 3600
        except (ValueError, TypeError):
            return False

    def keywords_overlap_ratio(self, other: "MemoryEvent") -> float:
        """计算关键词重叠率"""
        if not self.keywords or not other.keywords:
            return 0.0
        set1 = set(self.keywords)
        set2 = set(other.keywords)
        overlap = len(set1 & set2)
        return overlap / min(len(set1), len(set2))


class HistoryEventCandidate(BaseModel):
    """
    历史事件候选（带路由元数据）

    用于 summary 流程产出的候选，包含路由判断信息。
    """
    event: MemoryEvent = Field(description="事件本体")
    change_type: ChangeType = Field(default=ChangeType.NEW_ENTRY, description="变化类型")
    target_layer: str = Field(default="history_event", description="目标层")
    why_routed: str = Field(default="", description="路由原因")
    source_round: int = Field(default=0, description="来源轮次")
    is_duplicate: bool = Field(default=False, description="是否为重复事件")
    is_continuation: bool = Field(default=False, description="是否为续写事件")
    duplicate_of: Optional[str] = Field(default=None, description="重复的源事件ID")


class MemoryEventList(BaseModel):
    """历史事件列表（用于 Redis 存储）"""
    events: List[MemoryEvent] = Field(default_factory=list)

    def get_events_by_actor(self, actor: EventActor) -> List[MemoryEvent]:
        """按主体筛选事件"""
        return [e for e in self.events if e.actor == actor]

    def get_events_by_type(self, event_type: EventDetailType) -> List[MemoryEvent]:
        """按细类筛选事件"""
        return [e for e in self.events if e.event_type == event_type]

    def add_event(self, event: MemoryEvent):
        """添加事件"""
        self.events.append(event)

    def update_event(self, event_id: str, **updates):
        """更新指定事件"""
        for event in self.events:
            if event.event_id == event_id:
                for key, value in updates.items():
                    if hasattr(event, key):
                        setattr(event, key, value)
                event.last_seen_at = datetime.now().isoformat()
                break