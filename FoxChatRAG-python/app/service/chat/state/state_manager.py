"""
当前状态容器业务逻辑

职责：
- 管理 Redis 中的 current_state 存储
- 提供状态的读取、更新、覆盖、过期机制
"""

from datetime import datetime
from typing import Optional

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_chat_key
from app.core.db.redis_client import redis_client
from app.schemas.current_state import (
    CurrentState,
    StateField,
    UpdateSource,
)
from app.util.redis_json_util import json_set_safe



# 默认过期轮数配置（V2 简化版）
DEFAULT_EXPIRE_EMOTION = 3

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
    return build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.ROLE_CURRENT_STATE)


def get_current_state(user_id: str, llm_id: str, current_round: int = 0) -> CurrentState:
    """
    获取当前状态容器

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        current_round: 当前全局轮数（用于过期判断）

    Returns:
        CurrentState 对象，若不存在则返回默认状态
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

    # 返回默认状态（不写入 Redis，等首次更新时写入）
    return _create_default_state()


def _create_default_state() -> CurrentState:
    """创建默认状态（V2 简化版）"""
    return CurrentState(
        emotion=StateField(value="平静", confidence=0.5, expire_rounds=DEFAULT_EXPIRE_EMOTION, update_round=0),
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
        field_name: 字段名（当前支持 emotion）
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
        field_name: 字段名（当前支持 emotion）
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


def increment_round_counter(user_id: str, llm_id: str) -> int:
    """
    递增轮次计数器

    Returns:
        递增后的轮次数
    """
    key = build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.ROUND_COUNTER)

    count = redis_client.incr(key)
    return count