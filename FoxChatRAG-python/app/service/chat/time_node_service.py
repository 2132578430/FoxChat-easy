"""
未完成事项实时注入

职责：
- 从文本中检测时间表达（明天/后天/下周/今晚X点）
- 归一化时间锚点后直接写入 current_state.unfinished_items
- 不经过 pending → active 状态机
- 每轮 cleanup 清理过期事项
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List

from loguru import logger


# 时间表达匹配模式
TIME_EXPRESSIONS = {
    "明天": timedelta(days=1),
    "后天": timedelta(days=2),
    "下周": timedelta(weeks=1),
}

# 未来事项关键词
FUTURE_EVENT_KEYWORDS = ["考试", "出结果", "面试", "复查", "见面", "约会"]
FUTURE_FOLLOWUP_KEYWORDS = ["提醒", "继续聊", "再聊", "跟进"]

# 事件关键词词表（用于结构化去重）
EVENT_KEYWORDS = [
    "约会", "考试", "面试", "见面", "复查", "出差",
    "聚餐", "旅行", "搬家", "结婚", "生日", "手术",
    "汇报", "开会", "提交", "答辩", "签约", "入职",
    "离职", "挂号", "复诊", "取货", "发货",
]


def _extract_event_keywords(text: str, time_expression: str) -> List[str]:
    """
    从文本中提取事件关键词（排除时间词本身）

    Args:
        text: 输入文本
        time_expression: 已提取的时间表达（如"明天"）

    Returns:
        关键词列表，最多3个
    """
    keywords = []
    for kw in EVENT_KEYWORDS:
        if kw in text and kw != time_expression:
            keywords.append(kw)
    return keywords[:3]


def _normalize_time_expression(expression: str) -> Optional[str]:
    """
    归一化时间表达为 ISO 日期字符串

    Args:
        expression: 时间表达文本（如"明天"、"下周"、"今晚8点"）

    Returns:
        归一化后的日期字符串，无法归一化则返回 None
    """
    now = datetime.now()

    # 检查预定义的时间表达
    for keyword, delta in TIME_EXPRESSIONS.items():
        if keyword in expression:
            due_date = now + delta
            return due_date.strftime("%Y-%m-%d")

    # 检查"今晚X点"格式
    tonight_match = re.search(r"今晚(\d+)点", expression)
    if tonight_match:
        hour = int(tonight_match.group(1))
        due_datetime = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if due_datetime < now:
            due_datetime += timedelta(days=1)
        return due_datetime.isoformat()

    return None


def write_unfinished_item_from_time_expression(
    user_id: str,
    llm_id: str,
    content: str,
    time_expression: str,
    source_round: int = 0,
    keywords: List[str] = None,
) -> bool:
    """
    直接写入未完成事项（实时注入方案）

    检测到时间表达后，归一化时间并直接写入 current_state.unfinished_items，
    不经过 pending → active 状态机。

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        content: 事项内容
        time_expression: 时间表达（如"明天"、"后天"、"下周"）
        source_round: 来源轮次
        keywords: 事件关键词列表（用于结构化去重）

    Returns:
        是否成功写入
    """
    from app.service.chat.state_manager import update_unfinished_items
    from app.schemas.current_state import UnfinishedItem, ItemStatus

    due_at = _normalize_time_expression(time_expression)

    if not due_at:
        logger.warning(f"【实时注入】无法归一化时间表达: {time_expression}")
        return False

    item = UnfinishedItem(
        content=content,
        created_at=datetime.now().isoformat(),
        due_at=due_at,
        status=ItemStatus.PENDING,
        confidence=0.85,
        expire_rounds=6,
        update_round=source_round,
        update_reason=f"时间表达提取: {time_expression}"
    )

    update_unfinished_items(user_id, llm_id, [item], source_round)

    logger.info(f"【实时注入】写入 unfinished_items: {content[:30]}..., due_at={due_at}")
    return True


def extract_and_write_unfinished_item(
    user_id: str,
    llm_id: str,
    text: str,
    is_ai_reply: bool = False,
    source_round: int = 0,
) -> bool:
    """
    从文本中提取时间表达并直接写入 unfinished_items

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        text: 输入文本
        is_ai_reply: 是否为 AI 回复
        source_round: 来源轮次

    Returns:
        是否成功写入
    """
    # 检测时间表达
    time_expression = None
    for keyword in TIME_EXPRESSIONS.keys():
        if keyword in text:
            time_expression = keyword
            break

    if not time_expression:
        # 检查"今晚X点"
        if re.search(r"今晚\d+点", text):
            time_expression = re.search(r"今晚\d+点", text).group(0)

    if not time_expression:
        return False

    # 提取内容（简化版：使用整个文本的前50字）
    content = text[:50] if len(text) > 50 else text

    # 提取事件关键词（用于结构化去重）
    keywords = _extract_event_keywords(text, time_expression)

    return write_unfinished_item_from_time_expression(
        user_id=user_id,
        llm_id=llm_id,
        content=content,
        time_expression=time_expression,
        source_round=source_round,
        keywords=keywords,
    )
