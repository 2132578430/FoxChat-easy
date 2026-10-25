"""
轮次计数器

情绪状态已迁移到 app.service.chat.mood.store。
"""

from app.common.constant.LLMChatConstant import LLMChatConstant, build_chat_key
from app.core.db.redis_client import redis_client


def increment_round_counter(user_id: str, llm_id: str) -> int:
    """递增轮次计数器，返回递增后的轮次数。"""
    key = build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.ROUND_COUNTER)
    return redis_client.incr(key)
