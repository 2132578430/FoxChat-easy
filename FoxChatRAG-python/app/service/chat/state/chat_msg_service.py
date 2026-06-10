"""
对话消息服务模块

职责：
- 删除对话记忆（clear_chat_memory）
"""

from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.common.constant.LLMChatConstant import LLMChatConstant, build_chat_key
from app.core.db.redis_client import redis_client
from app.util import chroma_util


async def clear_chat_memory(user_id: str, llm_id: str) -> None:
    """删除对话相关的所有记忆"""
    keys_to_delete = [
        build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.RAW_EXPERIENCE),
        build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.CORE_ANCHOR),
        build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.USER_PROFILE),
        build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.CHARACTER_CARD),
        build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.MEMORY_BANK),
        build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.RECENT_MSG),
        build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.ROLE_CURRENT_STATE),
    ]
    round_counter_key = build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.ROUND_COUNTER)

    pip = redis_client.pipeline()
    for key in keys_to_delete:
        pip.delete(key)
    pip.delete(round_counter_key)
    pip.execute()

    await chroma_util.delete(ChromaTypeConstant.CHAT, user_id=user_id, llm_id=llm_id)
