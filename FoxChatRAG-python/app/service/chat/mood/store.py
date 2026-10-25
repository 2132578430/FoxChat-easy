"""
情绪状态 RedisJSON 存储

一个 (user_id, llm_id) 一份文档，mood 作为子对象写入。
"""

from datetime import datetime

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_chat_key
from app.core.db.redis_client import redis_client
from app.schemas.current_state import CurrentState, UpdateSource
from app.schemas.mood import MoodState
from app.util.redis_json_util import serialize_redis_json_value


def _build_state_key(user_id: str, llm_id: str) -> str:
    return build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.ROLE_CURRENT_STATE)


def _ensure_state_exists(key: str) -> None:
    try:
        if redis_client.json().get(key) is not None:
            return
    except Exception:
        logger.warning(f"【情绪存储】读取失败，重建默认状态: {key}")

    default = serialize_redis_json_value(CurrentState().model_dump())
    redis_client.execute_command("JSON.SET", key, "$", default, "NX")


def load_current_state(user_id: str, llm_id: str) -> CurrentState:
    key = _build_state_key(user_id, llm_id)
    try:
        data = redis_client.json().get(key)
        if data:
            return CurrentState.model_validate(data)
    except Exception as e:
        logger.warning(f"【情绪存储】加载失败，使用默认状态: {e}")
    return CurrentState()


def save_mood_state(user_id: str, llm_id: str, mood: MoodState) -> None:
    key = _build_state_key(user_id, llm_id)
    _ensure_state_exists(key)

    mood_json = serialize_redis_json_value(mood.model_dump())
    now_json = serialize_redis_json_value(datetime.now().isoformat())
    source_json = serialize_redis_json_value(UpdateSource.RUNTIME.value)

    pipe = redis_client.pipeline(transaction=True)
    pipe.execute_command("JSON.SET", key, "$.mood", mood_json)
    pipe.execute_command("JSON.SET", key, "$.last_update", now_json)
    pipe.execute_command("JSON.SET", key, "$.update_source", source_json)
    pipe.execute()

    logger.debug(
        f"【情绪存储】saved: label={mood.label.value}, intensity={mood.intensity}, "
        f"round={mood.update_round}"
    )
