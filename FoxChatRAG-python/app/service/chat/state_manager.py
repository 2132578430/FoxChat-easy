"""
当前状态容器业务逻辑（简化版 V2）

职责：
- 管理 Redis 中的 current_state 存储
- 提供状态的读取、更新、覆盖、过期机制
- 支持从 legacy emotion_state 迁移

【V2 简化说明】2026-05-05
移除以下字段的存储和更新逻辑：
- relation_state: 关系态势（暂无明确用途）
- current_focus: 话题焦点（置信度不可信）
- interaction_mode: 互动方式（暂无明确用途）

保留字段：
- emotion: 当前情绪
- unfinished_items: 待跟进事项

阶段2改造：
- 使用 RedisJSON 实现字段级原子更新
- 避免整体覆盖导致的并发竞态问题
- 使用相对轮数过期机制：(当前轮数 - 更新轮数) >= 过期轮数

注意事项：
- RedisJSON 对中文 JSON 对象写入有问题，需显式序列化
- 使用 execute_command 直接执行命令，避免 redis-py 内部处理问题
"""

import json
from datetime import datetime
from typing import Optional

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core.db.redis_client import redis_client
from app.schemas.current_state import (
    CurrentState,
    StateField,
    UnfinishedItem,
    UpdateSource,
    ItemStatus,
)
from app.util.redis_json_util import json_set_safe
from app.service.chat.common import EMOTION_CN_MAP, safe_json_parse, build_round_counter_key


# 默认过期轮数配置（V2 简化版）
DEFAULT_EXPIRE_EMOTION = 3
DEFAULT_EXPIRE_UNFINISHED = 6

# 状态覆盖阈值
CONFIDENCE_DELTA_THRESHOLD = 0.15


def _get_json_client():
    """获取 RedisJSON 客户端"""
    return redis_client.json()


def _json_set(key: str, path: str, value) -> None:
    """
    安全的 JSON.SET 操作（处理中文序列化问题）

    RedisJSON 的 json_client.set() 对包含中文的 dict 可能处理失败，
    使用 execute_command 直接执行命令并显式序列化。

    Args:
        key: Redis key
        path: JSONPath（如 $.emotion 或 $）
        value: 要写入的值（dict/list/str/float）
    """
    json_set_safe(redis_client, key, path, value)


def _build_state_key(user_id: str, llm_id: str) -> str:
    """构建状态存储 key"""
    return build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, user_id, llm_id)


def get_current_state(user_id: str, llm_id: str, current_round: int = 0) -> CurrentState:
    """
    获取当前状态容器

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        current_round: 当前全局轮数（用于过期判断）

    Returns:
        CurrentState 对象，若不存在则返回默认状态或迁移旧数据
    """
    key = _build_state_key(user_id, llm_id)
    json_client = _get_json_client()

    try:
        # 使用 JSON.GET 获取完整状态
        state_dict = json_client.get(key)
        if state_dict:
            return CurrentState.model_validate(state_dict)
    except Exception as e:
        # key 不存在或其他错误
        logger.debug(f"JSON.GET 失败或 key 不存在: {key}, error: {e}")

    # 尝试从 legacy emotion_state 迁移
    migrated_state = _migrate_from_emotion_state(user_id, llm_id)
    if migrated_state:
        logger.info(f"【状态迁移】从 emotion_state 迁移: {migrated_state.emotion.value}")
        return migrated_state

    # 返回默认状态（不写入 Redis，等首次更新时写入）
    return _create_default_state()


def _create_default_state() -> CurrentState:
    """创建默认状态（V2 简化版）"""
    return CurrentState(
        emotion=StateField(value="平静", confidence=0.5, expire_rounds=DEFAULT_EXPIRE_EMOTION, update_round=0),
        unfinished_items=[],
        last_update=datetime.now().isoformat(),
        update_source=UpdateSource.RUNTIME,
    )


def _create_default_state_dict() -> dict:
    """创建默认状态的字典形式（用于 JSON.SET）"""
    state = _create_default_state()
    return state.model_dump()


def _ensure_state_exists(user_id: str, llm_id: str) -> None:
    """确保状态 key 存在，不存在则初始化"""
    key = _build_state_key(user_id, llm_id)
    json_client = _get_json_client()

    try:
        # 检查是否存在
        result = json_client.get(key)
        if result is not None:
            return  # key 已存在
    except Exception:
        pass

    # 不存在或出错，初始化默认状态
    default_dict = _create_default_state_dict()
    _json_set(key, '$', default_dict)
    logger.debug(f"【状态初始化】已创建默认状态: {key}")


def _migrate_from_emotion_state(user_id: str, llm_id: str) -> Optional[CurrentState]:
    """
    从 legacy emotion_state 迁移

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        迁移后的 CurrentState，若旧数据不存在则返回 None
    """
    legacy_key = build_memory_key(LLMChatConstant.ROLE_EMOTION_STATE, user_id, llm_id)
    legacy_json = redis_client.get(legacy_key)

    if not legacy_json:
        return None

    try:
        legacy_state = json.loads(legacy_json)
        emotion_value = legacy_state.get("emotion", "neutral")

        # 映射英文情绪到中文
        emotion_cn = EMOTION_CN_MAP.get(emotion_value.lower(), emotion_value)

        # 获取当前轮数作为更新轮数
        current_round = get_current_round(user_id, llm_id)

        # 创建默认状态并更新 emotion
        state_dict = _create_default_state_dict()
        state_dict["emotion"] = {
            "value": emotion_cn,
            "confidence": 0.9,
            "expire_rounds": DEFAULT_EXPIRE_EMOTION,
            "update_round": current_round,
            "update_reason": "从 legacy emotion_state 迁移",
        }
        state_dict["last_update"] = legacy_state.get("last_update", datetime.now().isoformat())

        # 使用安全写入方法
        key = _build_state_key(user_id, llm_id)
        _json_set(key, '$', state_dict)

        return CurrentState.model_validate(state_dict)
    except json.JSONDecodeError:
        logger.warning(f"legacy emotion_state JSON 解析失败: {legacy_key}")
        return None


def update_current_state_field_atomic(
    user_id: str,
    llm_id: str,
    field_name: str,
    field_dict: dict,
) -> None:
    """
    原子更新单个状态字段（使用 RedisJSON）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        field_name: 字段名（emotion, relation_state, current_focus, interaction_mode）
        field_dict: 字段完整字典（包含 value, confidence, expire_rounds, update_round, update_reason）
    """
    key = _build_state_key(user_id, llm_id)

    # 确保 key 存在
    _ensure_state_exists(user_id, llm_id)

    # 原子更新字段（使用安全写入方法）
    _json_set(key, f'$.{field_name}', field_dict)

    # 更新时间戳
    _json_set(key, '$.last_update', datetime.now().isoformat())

    logger.info(f"【状态更新】{field_name}: {field_dict['value']} (update_round={field_dict['update_round']})")


def update_current_state(
    user_id: str,
    llm_id: str,
    field_name: str,
    new_value: str,
    confidence: float,
    source: UpdateSource,
    expire_rounds: Optional[int] = None,
    reason: str = "",
    current_round: int = 0,
) -> None:
    """
    更新单个状态字段（带覆盖规则判断）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        field_name: 字段名（emotion, relation_state, current_focus, interaction_mode）
        new_value: 新值
        confidence: 置信度
        source: 更新来源
        expire_rounds: 过期轮数（可选，默认保持原值）
        reason: 更新原因
        current_round: 当前全局轮数
    """
    # 1. 读取当前状态（用于覆盖判断）
    state = get_current_state(user_id, llm_id, current_round)

    # 2. 获取目标字段
    target_field = getattr(state, field_name, None)
    if target_field is None:
        logger.warning(f"【状态更新】未知字段: {field_name}")
        return

    # 3. 构建候选（写入当前轮数作为更新轮数）
    candidate = StateField(
        value=new_value,
        confidence=confidence,
        expire_rounds=expire_rounds if expire_rounds is not None else target_field.expire_rounds,
        update_round=current_round,
        update_reason=reason,
    )

    # 4. 应用覆盖规则
    should_update = _apply_state_overwrite_rules(
        existing=target_field,
        candidate=candidate,
        existing_source=state.update_source,
        candidate_source=source,
        current_round=current_round,
    )

    if should_update:
        # 5. 原子更新字段（使用 RedisJSON）
        update_current_state_field_atomic(
            user_id=user_id,
            llm_id=llm_id,
            field_name=field_name,
            field_dict=candidate.model_dump(),
        )

        # 6. 更新来源标记
        key = _build_state_key(user_id, llm_id)
        _json_set(key, '$.update_source', source.value)

        logger.info(f"【状态更新】{field_name}: {new_value} (confidence={confidence}, update_round={current_round})")
    else:
        # 只更新时间戳
        key = _build_state_key(user_id, llm_id)
        _ensure_state_exists(user_id, llm_id)
        _json_set(key, '$.last_update', datetime.now().isoformat())

        logger.debug(f"【状态保持】{field_name}: 保持原值 {target_field.value}")


def update_unfinished_items_atomic(
    user_id: str,
    llm_id: str,
    items_list: list[dict],
) -> None:
    """
    原子更新未完成事项列表（使用 RedisJSON）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        items_list: 事项列表（字典形式）
    """
    key = _build_state_key(user_id, llm_id)

    _ensure_state_exists(user_id, llm_id)

    # 原子更新整个数组（使用安全写入方法）
    _json_set(key, '$.unfinished_items', items_list)
    _json_set(key, '$.last_update', datetime.now().isoformat())

    logger.info(f"【事项更新】unfinished_items: {len(items_list)} 条")


def _is_same_event(existing: UnfinishedItem, new_item: UnfinishedItem) -> bool:
    """
    判断是否为同一事件（基于 content 文本包含关系）

    Args:
        existing: 已存在的事项
        new_item: 新事项

    Returns:
        是否为同一事件
    """
    if existing.content and new_item.content:
        return (new_item.content in existing.content or
                existing.content in new_item.content)

    return False


def update_unfinished_items(
    user_id: str,
    llm_id: str,
    items: list[UnfinishedItem],
    current_round: int = 0,
) -> None:
    """
    更新未完成事项列表（带合并逻辑）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        items: 新事项列表（会与现有事项合并）
        current_round: 当前全局轮数
    """
    # 1. 读取现有事项
    state = get_current_state(user_id, llm_id, current_round)

    merged_items = list(state.unfinished_items)

    # 2. 合并规则：基于 content 去重
    for new_item in items:
        is_duplicate = False
        for existing in merged_items:
            if _is_same_event(existing, new_item):
                is_duplicate = True
                if len(new_item.content) > len(existing.content):
                    existing.content = new_item.content
                if new_item.due_at and not existing.due_at:
                    existing.due_at = new_item.due_at
                break

        if not is_duplicate:
            # 新事项写入当前轮数作为更新轮数
            new_item.update_round = current_round
            merged_items.append(new_item)

    # 3. 清理已完成/过期事项
    from datetime import datetime

    def _is_absolutely_expired(item: UnfinishedItem) -> bool:
        """判断是否绝对时间过期（due_at过期超过7天）"""
        if not item.due_at:
            return False
        try:
            due_date = datetime.fromisoformat(item.due_at.replace("Z", "+00:00"))
            days_passed = (datetime.now() - due_date).days
            return days_passed > 7  # 超过预期时间7天，清理掉
        except Exception:
            return False

    merged_items = [
        item for item in merged_items
        if item.status == ItemStatus.PENDING
        and not item.is_expired(current_round)
        and not _is_absolutely_expired(item)  # 阶段5：绝对时间过期清理
    ]

    # 4. 最多保留5条
    merged_items = merged_items[:5]

    # 5. 原子更新
    items_list = [item.model_dump() for item in merged_items]
    update_unfinished_items_atomic(user_id, llm_id, items_list)


def clean_expired_unfinished_items(user_id: str, llm_id: str, current_round: int = 0) -> int:
    """
    清理过期未完成事项（阶段5新增）

    在每次对话开始时调用，清理：
    1. 轮数过期的事项（expire_rounds机制）
    2. 绝对时间过期的事项（due_at过期超过7天）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        current_round: 当前全局轮数

    Returns:
        清理的事项数量
    """
    from datetime import datetime

    state = get_current_state(user_id, llm_id, current_round)

    def _is_absolutely_expired(item: UnfinishedItem) -> bool:
        """判断是否绝对时间过期"""
        if not item.due_at:
            return False
        try:
            due_date = datetime.fromisoformat(item.due_at.replace("Z", "+00:00"))
            days_passed = (datetime.now() - due_date).days
            return days_passed > 7
        except Exception:
            return False

    original_count = len(state.unfinished_items)

    # 清理过期事项
    valid_items = [
        item for item in state.unfinished_items
        if item.status == ItemStatus.PENDING
        and not item.is_expired(current_round)
        and not _is_absolutely_expired(item)
    ]

    cleaned_count = original_count - len(valid_items)

    if cleaned_count > 0:
        # 原子更新清理后的列表
        items_list = [item.model_dump() for item in valid_items[:5]]
        update_unfinished_items_atomic(user_id, llm_id, items_list)
        logger.info(f"【过期清理】清理 {cleaned_count} 条过期未完成事项")

    return cleaned_count


def _apply_state_overwrite_rules(
    existing: StateField,
    candidate: StateField,
    existing_source: UpdateSource,
    candidate_source: UpdateSource,
    current_round: int,
) -> bool:
    """
    判断是否应该用候选覆盖现有状态

    规则优先级：过期 > 来源等级 > 置信度差值 > 值变化

    Args:
        existing: 现有字段
        candidate: 候选字段
        existing_source: 现有来源
        candidate_source: 候选来源
        current_round: 当前全局轮数

    Returns:
        是否应该覆盖
    """
    # 1. 过期状态直接覆盖
    if existing.is_expired(current_round):
        return True

    # 2. 空值状态直接覆盖（除非候选也是空）
    if not existing.value and candidate.value:
        return True
    if not candidate.value:
        return False

    # 3. 来源等级判断
    source_level = {
        UpdateSource.USER_EXPLICIT: 3,
        UpdateSource.RUNTIME: 2,
        UpdateSource.SUMMARY: 1,
    }
    existing_level = source_level.get(existing_source, 1)
    candidate_level = source_level.get(candidate_source, 1)

    if candidate_level > existing_level:
        return True

    # 4. 置信度差值判断
    confidence_delta = candidate.confidence - existing.confidence
    if confidence_delta >= CONFIDENCE_DELTA_THRESHOLD:
        return True

    # 5. 值变化就覆盖（情绪变化应该更新）
    if existing.value != candidate.value:
        return True

    # 6. 同值同置信度不覆盖
    if existing.value == candidate.value and confidence_delta < 0.05:
        return False

    # 默认：不覆盖，保持现有
    return False


def check_and_expire_fields(user_id: str, llm_id: str, current_round: int) -> CurrentState:
    """
    检查并处理过期字段（V2 简化版）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        current_round: 当前全局轮数

    Returns:
        更新后的 CurrentState
    """
    state = get_current_state(user_id, llm_id, current_round)
    key = _build_state_key(user_id, llm_id)

    expired_fields = []

    # 检查 emotion 是否过期
    if state.emotion.is_expired(current_round):
        expired_fields.append("emotion")
        # 原子更新：置信度置零（标记为失效，等待重新检测）
        _json_set(key, '$.emotion.confidence', 0.0)

    # 检查 unfinished_items
    state.unfinished_items = [
        item for item in state.unfinished_items
        if not item.is_expired(current_round) and item.status == ItemStatus.PENDING
    ]
    items_list = [item.model_dump() for item in state.unfinished_items]
    _json_set(key, '$.unfinished_items', items_list)

    if expired_fields:
        logger.info(f"【状态过期】字段已过期: {expired_fields}")
        _json_set(key, '$.last_update', datetime.now().isoformat())

    # 重新读取返回
    return get_current_state(user_id, llm_id, current_round)


# ==================== 轮次计数器 ====================

def _round_counter_key(user_id: str, llm_id: str) -> str:
    """构建轮次计数器 key（使用公共模块）"""
    return build_round_counter_key(user_id, llm_id)


def increment_round_counter(user_id: str, llm_id: str) -> int:
    """
    递增轮次计数器

    Returns:
        递增后的轮次数
    """
    key = _round_counter_key(user_id, llm_id)

    count = redis_client.incr(key)
    return count


def get_current_round(user_id: str, llm_id: str) -> int:
    """
    获取当前全局轮数

    Returns:
        当前轮次数
    """
    key = _round_counter_key(user_id, llm_id)

    count = redis_client.get(key)
    return int(count or 0)