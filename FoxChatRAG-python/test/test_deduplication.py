import unittest
from dataclasses import dataclass


@dataclass
class MemoryEvent:
    """简化版 MemoryEvent 用于测试"""
    event_id: str
    content: str


DEDUP_SIMILARITY_THRESHOLD = 0.95


def _calculate_content_similarity(content1: str, content2: str) -> float:
    """计算字符级相似度"""
    if not content1 or not content2:
        return 0.0
    chars1 = set(content1)
    chars2 = set(content2)
    intersection = len(chars1 & chars2)
    union = len(chars1 | chars2)
    if union == 0:
        return 0.0
    return intersection / union


def should_deduplicate(event1: MemoryEvent, event2: MemoryEvent) -> bool:
    """去重规则：相似度 >= 0.95 或相同 event_id"""
    if event1.content == event2.content:
        return True
    if event1.event_id and event1.event_id == event2.event_id:
        return True
    similarity = _calculate_content_similarity(event1.content, event2.content)
    if similarity >= DEDUP_SIMILARITY_THRESHOLD:
        return True
    return False


class TestShouldDeduplicate(unittest.TestCase):
    """测试去重逻辑：95%相似度去重"""

    def test_identical_content_deduplicated(self):
        """相同内容应去重"""
        event1 = MemoryEvent(event_id="id1", content="测试回复")
        event2 = MemoryEvent(event_id="id2", content="测试回复")
        self.assertTrue(should_deduplicate(event1, event2))

    def test_different_content_retained(self):
        """不同内容应保留（如"测试回复1"和"测试回复2"）"""
        event1 = MemoryEvent(event_id="id1", content="测试回复1")
        event2 = MemoryEvent(event_id="id2", content="测试回复2")
        # "测试回复1" vs "测试回复2" 字符集合差异较大
        self.assertFalse(should_deduplicate(event1, event2))

    def test_same_event_id_deduplicated(self):
        """相同event_id应去重（续写合并场景）"""
        event1 = MemoryEvent(event_id="same_id", content="原始内容")
        event2 = MemoryEvent(event_id="same_id", content="续写后的内容")
        self.assertTrue(should_deduplicate(event1, event2))

    def test_empty_event_id_different_content_retained(self):
        """空event_id且内容不同应保留"""
        event1 = MemoryEvent(event_id="", content="内容A")
        event2 = MemoryEvent(event_id="", content="内容B")
        self.assertFalse(should_deduplicate(event1, event2))

    def test_high_similarity_deduplicated(self):
        """高相似度(>=95%)应去重"""
        # "测试回复内容相同" vs "测试回复内容相同" - 完全相同
        event1 = MemoryEvent(event_id="id1", content="测试回复内容相同")
        event2 = MemoryEvent(event_id="id2", content="测试回复内容相同")
        self.assertTrue(should_deduplicate(event1, event2))

    def test_medium_similarity_retained(self):
        """中等相似度(<95%)应保留"""
        # 不同内容但有些相似字符
        event1 = MemoryEvent(event_id="id1", content="用户说明天去跑步")
        event2 = MemoryEvent(event_id="id2", content="用户说后天去游泳")
        # 字符集合：{用户说明天去跑步} vs {用户说后天去游泳}
        # 差异较大，不应去重
        self.assertFalse(should_deduplicate(event1, event2))


if __name__ == "__main__":
    unittest.main()