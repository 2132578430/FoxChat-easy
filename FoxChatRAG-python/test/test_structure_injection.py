import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest
from dataclasses import dataclass
from enum import StrEnum


class EventActor(StrEnum):
    USER = "USER"
    ROLE = "ROLE"


class EventDetailType(StrEnum):
    FOLLOW_UP = "follow_up"
    BOUNDARY = "boundary"
    COMMITMENT = "commitment"
    OTHER = "other"


@dataclass
class MemoryEvent:
    event_id: str
    content: str
    actor: EventActor
    event_type: EventDetailType
    occurred_at: str = ""


EVENT_TYPE_LABELS = {
    "boundary": "边界底线",
    "follow_up": "跟进事项",
    "share_experience": "经历分享",
    "commitment": "承诺约定",
    "relation_change": "关系变化",
    "express_emotion": "情绪表达",
    "other": "其他",
}


def format_history_events(events: list) -> str:
    """简化版 format_history_events 用于测试"""
    if not events:
        return ""

    lines = ["【相关历史事件】"]

    for event in events:
        actor_prefix = "用户" if event.actor == EventActor.USER else "角色"
        event_type_str = event.event_type.value if event.event_type else "other"
        type_label = EVENT_TYPE_LABELS.get(event_type_str, "其他")
        event_line = f"- [{type_label}] {actor_prefix}{event.content}"
        lines.append(event_line)

    return "\n".join(lines)


class TestFormatHistoryEvents(unittest.TestCase):
    """测试结构注入格式"""

    def test_follow_up_format(self):
        """验证跟进事项格式"""
        event = MemoryEvent(
            event_id="id1",
            content="说三小时后吃饭",
            actor=EventActor.USER,
            event_type=EventDetailType.FOLLOW_UP,
        )
        result = format_history_events([event])
        self.assertIn("- [跟进事项] 用户说三小时后吃饭", result)

    def test_boundary_format(self):
        """验证边界声明格式"""
        event = MemoryEvent(
            event_id="id2",
            content="拒绝讨论政治话题",
            actor=EventActor.USER,
            event_type=EventDetailType.BOUNDARY,
        )
        result = format_history_events([event])
        self.assertIn("- [边界声明] 用户拒绝讨论政治话题", result)

    def test_commitment_format(self):
        """验证承诺约定格式"""
        event = MemoryEvent(
            event_id="id3",
            content="承诺明天完成报告",
            actor=EventActor.ROLE,
            event_type=EventDetailType.COMMITMENT,
        )
        result = format_history_events([event])
        self.assertIn("- [承诺约定] 角色承诺明天完成报告", result)


if __name__ == "__main__":
    unittest.main()