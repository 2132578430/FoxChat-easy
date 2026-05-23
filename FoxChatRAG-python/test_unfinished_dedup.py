"""
测试 unfinished_items 结构化去重逻辑（独立版本）

验证场景：
1. 同一事项不同表述 -> 去重
2. 同一时间不同事件 -> 不去重
3. 旧数据兼容 -> 回退到 content 包含
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class UnfinishedItem:
    """简化版 UnfinishedItem 用于测试"""
    content: str
    time_expression: Optional[str] = None
    keywords: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


def _is_same_event(existing: UnfinishedItem, new_item: UnfinishedItem) -> bool:
    """
    判断是否为同一事件（结构化去重）

    规则：time_expression 相同 AND keywords 有至少 1 个重叠
    兜底：当缺少结构化字段时，回退到 content 文本包含关系
    """
    # 结构化字段去重
    if existing.time_expression and new_item.time_expression:
        # 时间表达相同
        has_same_time = existing.time_expression == new_item.time_expression

        # 关键词有重叠
        if existing.keywords and new_item.keywords:
            overlap = set(existing.keywords) & set(new_item.keywords)
            has_keyword_match = len(overlap) >= 1
        else:
            # 一方无关键词，无法判断，回退到 content
            has_keyword_match = False

        if has_same_time and has_keyword_match:
            return True

    # 兜底：content 文本包含关系（兼容旧数据）
    if existing.content and new_item.content:
        # 双向包含判断
        return (new_item.content in existing.content or
                existing.content in new_item.content)

    return False


def test_same_event_different_expression():
    """场景1：同一事项不同表述"""
    existing = UnfinishedItem(
        content="明天去约会",
        time_expression="明天",
        keywords=["约会"],
    )
    new_item = UnfinishedItem(
        content="明天约会？好好准备哦",
        time_expression="明天",
        keywords=["约会"],
    )

    result = _is_same_event(existing, new_item)
    print(f"场景1: 同一事项不同表述 -> {result}")
    assert result == True, "应该判定为同一事件"
    print("  PASS")


def test_same_time_different_event():
    """场景2：同一时间不同事件"""
    existing = UnfinishedItem(
        content="明天约会",
        time_expression="明天",
        keywords=["约会"],
    )
    new_item = UnfinishedItem(
        content="明天考试",
        time_expression="明天",
        keywords=["考试"],
    )

    result = _is_same_event(existing, new_item)
    print(f"场景2: 同一时间不同事件 -> {result}")
    assert result == False, "不应该判定为同一事件"
    print("  PASS")


def test_old_data_compatibility():
    """场景3：旧数据兼容（无结构化字段）"""
    existing = UnfinishedItem(
        content="明天去约会好好准备",
        time_expression=None,  # 旧数据无此字段
        keywords=[],           # 旧数据无此字段
    )
    new_item = UnfinishedItem(
        content="明天去约会",  # existing.content 包含这个
        time_expression="明天",
        keywords=["约会"],
    )

    result = _is_same_event(existing, new_item)
    print(f"场景3: 旧数据兼容（content包含） -> {result}")
    assert result == True, "应该通过 content 包含关系判定为同一事件"
    print("  PASS")


def test_different_time_same_event():
    """场景4：不同时间同一事件"""
    existing = UnfinishedItem(
        content="明天约会",
        time_expression="明天",
        keywords=["约会"],
    )
    new_item = UnfinishedItem(
        content="后天约会",
        time_expression="后天",
        keywords=["约会"],
    )

    result = _is_same_event(existing, new_item)
    print(f"场景4: 不同时间同一事件 -> {result}")
    assert result == False, "不应该判定为同一事件（时间不同）"
    print("  PASS")


if __name__ == "__main__":
    print("=" * 50)
    print("Test: unfinished_items structured dedup")
    print("=" * 50)

    test_same_event_different_expression()
    test_same_time_different_event()
    test_old_data_compatibility()
    test_different_time_same_event()

    print("\n" + "=" * 50)
    print("All tests PASSED")
    print("=" * 50)