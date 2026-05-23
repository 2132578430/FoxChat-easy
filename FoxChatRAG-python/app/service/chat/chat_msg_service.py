"""
对话消息服务模块

职责：
- 删除对话记忆（clear_chat_memory）
"""

from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core.db.redis_client import redis_client
from app.util import chroma_util


async def clear_chat_memory(user_id: str, llm_id: str) -> None:
    """删除对话相关的所有记忆"""
    keys_to_delete = [
        build_memory_key(LLMChatConstant.RAW_EXPERIENCE, user_id, llm_id),
        build_memory_key(LLMChatConstant.CORE_ANCHOR, user_id, llm_id),
        build_memory_key(LLMChatConstant.USER_PROFILE, user_id, llm_id),
        build_memory_key(LLMChatConstant.CHARACTER_CARD, user_id, llm_id),
        build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id),
        build_memory_key(LLMChatConstant.INIT_MEMORY, user_id, llm_id),
        build_memory_key(LLMChatConstant.RECENT_MSG, user_id, llm_id),
        build_memory_key(LLMChatConstant.ROLE_EMOTION_STATE, user_id, llm_id),
        build_memory_key(LLMChatConstant.ROLE_EMOTION_LOG, user_id, llm_id),
        build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, user_id, llm_id),
        build_memory_key(LLMChatConstant.ROLE_TIME_NODES, user_id, llm_id),
    ]

    from app.service.chat.common import build_round_counter_key
    round_counter_key = build_round_counter_key(user_id, llm_id)

    pip = redis_client.pipeline()
    for key in keys_to_delete:
        pip.delete(key)
    pip.delete(round_counter_key)
    pip.execute()

    await chroma_util.delete(ChromaTypeConstant.CHAT, user_id=user_id, llm_id=llm_id)
