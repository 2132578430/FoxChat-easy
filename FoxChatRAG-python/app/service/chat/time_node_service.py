"""
时间节点运行时逻辑

职责：
- 创建时间节点（从用户/AI的未来事项表达中提取）
- 归一化时间表达（明天/后天/下周）
- 到期检查与激活（兼容保留）
- 直接写入未完成事项（实时注入方案）

实时注入方案（当前主路径）：
- 检测到时间表达后直接写入 unfinished_items
- 不依赖 pending → active 状态机
- 每轮 cleanup 清理过期事项

兼容保留：
- create_time_node() 仍可用于调试/兼容
- route_due_time_nodes() 保留但不在主流程调用
"""

import json
import re
from datetime import datetime, timedelta
from typing import Optional, List

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core.db.redis_client import redis_client
from app.schemas.time_node import (
    TimeNode,
    TimeNodeList,
    TimeNodeStatus,
    TimePrecision,
    CreatedFrom,
)


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


def _get_json_client():
    """获取 RedisJSON 客户端"""
    return redis_client.json()


def _build_nodes_key(user_id: str, llm_id: str) -> str:
    """构建时间节点存储 key"""
    return build_memory_key(LLMChatConstant.ROLE_TIME_NODES, user_id, llm_id)


def _ensure_nodes_key_exists(user_id: str, llm_id: str) -> None:
    """确保时间节点 key 存在，不存在则初始化空数组"""
    key = _build_nodes_key(user_id, llm_id)
    json_client = _get_json_client()

    try:
        data = json_client.get(key)
        # 检查返回值是否有效
        if data is None or not isinstance(data, dict) or 'nodes' not in data:
            # 不存在或结构不正确，初始化空数组
            json_client.set(key, '$', {'nodes': []})
            logger.debug(f"【时间节点初始化】已创建空数组: {key}")
    except Exception as e:
        # 异常情况，初始化空数组
        json_client.set(key, '$', {'nodes': []})
        logger.debug(f"【时间节点初始化】异常后重建: {key}, error: {e}")


def create_time_node(
    user_id: str,
    llm_id: str,
    content: str,
    time_expression: str,
    created_from: CreatedFrom,
    source_round: int = 0,
) -> Optional[TimeNode]:
    """
    创建时间节点（原子追加）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        content: 节点内容（到期后应浮现的事项）
        time_expression: 时间表达（如"明天"）
        created_from: 来源类型
        source_round: 来源轮次

    Returns:
        创建的 TimeNode，若时间表达无法归一化则返回 None
    """
    # 归一化时间
    due_at, precision = _normalize_time_expression(time_expression)

    if not due_at:
        logger.warning(f"【时间节点】无法归一化时间表达: {time_expression}")
        return None

    # 生成唯一 ID
    today_str = datetime.now().strftime("%Y%m%d")
    nodes = get_all_time_nodes(user_id, llm_id)
    sequence = len([n for n in nodes.nodes if n.time_node_id.startswith(f"tn_{today_str}")]) + 1
    time_node_id = f"tn_{today_str}_{sequence:03d}"

    node = TimeNode(
        time_node_id=time_node_id,
        content=content,
        due_at=due_at,
        precision=precision,
        status=TimeNodeStatus.PENDING,
        created_from=created_from,
        source_round=source_round,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

    # 原子追加到 Redis
    _append_time_node_atomic(user_id, llm_id, node)

    logger.info(f"【时间节点创建】id={time_node_id}, due_at={due_at}, content={content[:30]}...")
    return node


def _normalize_time_expression(expression: str) -> tuple[Optional[str], TimePrecision]:
    """
    归一化时间表达为 ISO 日期

    Args:
        expression: 时间表达文本（如"明天"、"下周"、"今晚8点"）

    Returns:
        (due_at, precision): 归一化后的日期字符串和精度
    """
    now = datetime.now()

    # 检查预定义的时间表达
    for keyword, delta in TIME_EXPRESSIONS.items():
        if keyword in expression:
            due_date = now + delta
            return due_date.strftime("%Y-%m-%d"), TimePrecision.DAY

    # 检查"今晚X点"格式
    tonight_match = re.search(r"今晚(\d+)点", expression)
    if tonight_match:
        hour = int(tonight_match.group(1))
        due_datetime = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if due_datetime < now:
            due_datetime += timedelta(days=1)
        return due_datetime.isoformat(), TimePrecision.DATETIME

    # 无法归一化
    return None, TimePrecision.DAY


def _append_time_node_atomic(user_id: str, llm_id: str, node: TimeNode) -> None:
    """
    原子追加时间节点到数组（使用 RedisJSON）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        node: TimeNode 对象
    """
    key = _build_nodes_key(user_id, llm_id)
    json_client = _get_json_client()

    # 确保 key 存在
    _ensure_nodes_key_exists(user_id, llm_id)

    # 原子追加节点到数组
    node_dict = node.model_dump()
    json_client.arrappend(key, '$.nodes', node_dict)

    logger.debug(f"【时间节点追加】原子操作: {node.time_node_id}")


def get_all_time_nodes(user_id: str, llm_id: str) -> TimeNodeList:
    """
    获取所有时间节点

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        TimeNodeList 对象
    """
    key = _build_nodes_key(user_id, llm_id)
    json_client = _get_json_client()

    try:
        data = json_client.get(key)
        if data and 'nodes' in data:
            return TimeNodeList.model_validate(data)
    except Exception as e:
        logger.debug(f"【时间节点】JSON.GET 失败或 key 不存在: {key}, error: {e}")

    return TimeNodeList()


def get_pending_time_nodes(user_id: str, llm_id: str) -> List[TimeNode]:
    """
    获取所有 pending 状态的时间节点

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        pending 状态的 TimeNode 列表
    """
    nodes = get_all_time_nodes(user_id, llm_id)
    return nodes.get_pending_nodes()


def check_due_time_nodes(user_id: str, llm_id: str) -> List[TimeNode]:
    """
    检查已到期的时间节点

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        已到期且状态为 pending 的 TimeNode 列表
    """
    pending_nodes = get_pending_time_nodes(user_id, llm_id)
    now = datetime.now()

    due_nodes = []
    for node in pending_nodes:
        if node.is_due(now):
            due_nodes.append(node)
            logger.debug(f"【时间节点到期】id={node.time_node_id}, due_at={node.due_at}")

    return due_nodes


def _find_node_index(user_id: str, llm_id: str, time_node_id: str) -> Optional[int]:
    """
    查找指定节点的数组索引

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        time_node_id: 时间节点 ID

    Returns:
        索引位置，若不存在则返回 None
    """
    nodes = get_all_time_nodes(user_id, llm_id)
    for i, node in enumerate(nodes.nodes):
        if node.time_node_id == time_node_id:
            return i
    return None


def activate_time_node(user_id: str, llm_id: str, node: TimeNode) -> None:
    """
    激活时间节点（原子更新状态）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        node: 要激活的 TimeNode
    """
    key = _build_nodes_key(user_id, llm_id)
    json_client = _get_json_client()

    # 查找节点索引
    index = _find_node_index(user_id, llm_id, node.time_node_id)
    if index is None:
        logger.warning(f"【时间节点激活】找不到节点: {node.time_node_id}")
        return

    # 原子更新状态字段
    json_client.set(key, f'$.nodes[{index}].status', TimeNodeStatus.ACTIVE.value)
    json_client.set(key, f'$.nodes[{index}].updated_at', datetime.now().isoformat())

    logger.info(f"【时间节点激活】id={node.time_node_id}, content={node.content[:30]}... (原子操作)")


def mark_time_node_done(user_id: str, llm_id: str, time_node_id: str) -> None:
    """
    标记时间节点为完成（原子更新状态）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        time_node_id: 时间节点 ID
    """
    key = _build_nodes_key(user_id, llm_id)
    json_client = _get_json_client()

    # 查找节点索引
    index = _find_node_index(user_id, llm_id, time_node_id)
    if index is None:
        logger.warning(f"【时间节点完成】找不到节点: {time_node_id}")
        return

    # 原子更新状态字段
    json_client.set(key, f'$.nodes[{index}].status', TimeNodeStatus.DONE.value)
    json_client.set(key, f'$.nodes[{index}].updated_at', datetime.now().isoformat())

    logger.info(f"【时间节点完成】id={time_node_id} (原子操作)")


def extract_time_node_from_text(
    user_id: str,
    llm_id: str,
    text: str,
    is_ai_reply: bool = False,
    source_round: int = 0,
) -> Optional[TimeNode]:
    """
    从文本中提取时间节点

    检测未来事项表达并创建时间节点。

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        text: 输入文本
        is_ai_reply: 是否为 AI 回复
        source_round: 来源轮次

    Returns:
        创建的 TimeNode，若无有效表达则返回 None
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
        return None

    # 确定来源类型
    if is_ai_reply:
        created_from = CreatedFrom.AI_COMMITMENT
    else:
        # 判断是事件还是跟进请求
        if any(kw in text for kw in FUTURE_FOLLOWUP_KEYWORDS):
            created_from = CreatedFrom.USER_FUTURE_FOLLOWUP
        else:
            created_from = CreatedFrom.USER_FUTURE_EVENT

    # 提取内容（简化版：使用整个文本的前50字）
    content = text[:50] if len(text) > 50 else text

    return create_time_node(
        user_id=user_id,
        llm_id=llm_id,
        content=content,
        time_expression=time_expression,
        created_from=created_from,
        source_round=source_round,
    )


def check_and_activate_due_time_nodes(user_id: str, llm_id: str) -> List[str]:
    """
    检查并激活所有到期的时间节点，返回激活的内容列表

    用于在 chat_msg 主流程开始时调用。

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        激活的节点内容列表（用于注入 unfinished_items）
    """
    due_nodes = check_due_time_nodes(user_id, llm_id)

    activated_contents = []
    for node in due_nodes:
        activate_time_node(user_id, llm_id, node)
        activated_contents.append(node.content)

    return activated_contents


# 阶段4新增：时间节点路由判定


def route_due_time_nodes(user_id: str, llm_id: str, current_round: int = 0) -> dict:
    """
    检查到期时间节点并判定去向，返回路由结果

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        current_round: 当前全局轮数

    Returns:
        {
            "unfinished_items": [待跟进事项列表],
            "retrieval_triggers": [检索触发节点列表],
            "activated_count": 总激活数量
        }
    """
    due_nodes = check_due_time_nodes(user_id, llm_id)

    routing_result = {
        "unfinished_items": [],
        "retrieval_triggers": [],
        "activated_count": 0,
    }

    # 关键词判定：承诺/待跟进类
    followup_keywords = ["继续", "跟进", "提醒", "明天", "下次", "之后", "回头"]
    # 关键词判定：需要背景回忆类
    background_keywords = ["结果", "成绩", "反馈", "答复", "结果出来"]

    for node in due_nodes:
        # 激活节点
        activate_time_node(user_id, llm_id, node)
        routing_result["activated_count"] += 1

        # 判定去向
        content_lower = node.content.lower()

        # 承诺/待跟进类：优先进入 B 层
        is_followup = (
            node.created_from in [CreatedFrom.AI_COMMITMENT, CreatedFrom.USER_FUTURE_FOLLOWUP]
            or any(kw in content_lower for kw in followup_keywords)
        )

        # 需要背景回忆类：触发 C 层检索
        needs_background = any(kw in content_lower for kw in background_keywords)

        # 阶段4：标记双路由节点，便于后续去重
        dual_routing = is_followup and needs_background

        if is_followup:
            # 路由到 B 层 unfinished_items
            routing_result["unfinished_items"].append({
                "content": node.content,
                "created_at": node.created_at,  # 阶段5：传递创建时间
                "due_at": node.due_at,          # 阶段5：传递预期时间
                "source_node_id": node.time_node_id,
                "confidence": 0.9,
                "expire_rounds": 6,
                "dual_routing": dual_routing,  # 阶段4：标记双路由
            })
            logger.info(f"【时间节点路由】B层: {node.content[:30]}...")

        if needs_background:
            # 路由到 C 层检索触发
            routing_result["retrieval_triggers"].append({
                "content": node.content,
                "source_node_id": node.time_node_id,
                "dual_routing": dual_routing,  # 阶段4：标记双路由
            })
            logger.info(f"【时间节点路由】C层触发: {node.content[:30]}...")

        # 如果同时满足两种条件，允许双路由（后续去重由格式化层负责）

    return routing_result


# ============================================================
# 实时注入方案：直接写入 unfinished_items
# ============================================================


def write_unfinished_item_from_time_expression(
    user_id: str,
    llm_id: str,
    content: str,
    time_expression: str,
    source_round: int = 0,
    keywords: List[str] = None,  # 新增：事件关键词
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

    # 复用现有归一化逻辑
    due_at, precision = _normalize_time_expression(time_expression)

    if not due_at:
        logger.warning(f"【实时注入】无法归一化时间表达: {time_expression}")
        return False

    # 构建 UnfinishedItem（包含结构化去重字段）
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

    # 直接写入 unfinished_items
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

    复用 extract_time_node_from_text 的检测逻辑，但写入目标改为 unfinished_items。

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
        keywords=keywords,  # 新增
    )