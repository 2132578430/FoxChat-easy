"""
聊天 Redis 操作服务

职责：
- 构建 Redis key
- 批量获取记忆数据
- 保存对话到 Redis
- 构建历史消息
"""

import json
from typing import List, Optional

from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.chat_models import BaseMessage

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core.db.redis_client import redis_client
from app.exception.BusinessException import BusinessException
from app.common.constant.MsgStatusConstant import MsgStatusConstant
from app.service.chat.common import build_init_memory_key, build_recent_msg_key, build_current_state_key
from app.service.chat.types import ChatMemories


def build_history_message(recent_msg: List[str]) -> List[BaseMessage]:
    """
    将 Redis 中的消息列表转换为 LangChain 的历史消息格式

    Args:
        recent_msg: Redis 中的消息 JSON 列表

    Returns:
        LangChain BaseMessage 列表
    """
    if not recent_msg:
        return []

    history_msg: List[BaseMessage] = []
    for msg_json in reversed(recent_msg):
        msg: dict = json.loads(msg_json)
        role = msg.get("role")
        content = msg.get("content")

        if role == "human":
            history_msg.append(HumanMessage(content))
        elif role == "ai":
            history_msg.append(AIMessage(content))
        else:
            raise BusinessException(MsgStatusConstant.UNKNOWN_ROLE_ERROR)

    return history_msg


async def fetch_all_memories(user_id: str, llm_id: str) -> "ChatMemories":
    """
    批量获取所有记忆数据

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        ChatMemories 对象
    """
    init_memory_key = build_init_memory_key(user_id, llm_id)
    recent_msg_key = build_recent_msg_key(user_id, llm_id)
    current_state_key = build_current_state_key(user_id, llm_id)

    pip = redis_client.pipeline()
    pip.get(init_memory_key)
    pip.lrange(recent_msg_key, 0, 29)
    pip.get(build_memory_key(LLMChatConstant.CHARACTER_CARD, user_id, llm_id))
    pip.get(build_memory_key(LLMChatConstant.CORE_ANCHOR, user_id, llm_id))
    pip.get(build_memory_key(LLMChatConstant.USER_PROFILE, user_id, llm_id))
    pip.get(build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id))
    # 此处用的是RedisJSON来保障多个状态操作之间的原子性
    pip.execute_command('JSON.GET', current_state_key)

    result = pip.execute()

    # 处理 current_state JSON
    current_state_json = ""
    if result[6]:
        if isinstance(result[6], dict):
            current_state_json = json.dumps(result[6], ensure_ascii=False)
        elif isinstance(result[6], str):
            current_state_json = result[6]
        else:
            logger.warning(f"current_state Redis 数据格式异常: type={type(result[6])}")
            current_state_json = ""

    return ChatMemories(
        init_memory=result[0] or "",
        recent_msg=result[1],
        character_card_json=result[2] or "",
        core_anchor_json=result[3] or "",
        user_profile_json=result[4] or "",
        memory_bank_json=result[5] or "",
        current_state_json=current_state_json,
    )


async def save_chat_to_redis(
    recent_msg_key: str,
    msg_content: str,
    chat_response: str
) -> int:
    """
    保存对话到 Redis

    Args:
        recent_msg_key: 最近消息 key
        msg_content: 用户消息内容
        chat_response: AI 响应内容

    Returns:
        消息总数
    """
    pip = redis_client.pipeline()

    pip.lpush(recent_msg_key, json.dumps({"role": "human", "content": msg_content}))
    pip.lpush(recent_msg_key, json.dumps({"role": "ai", "content": chat_response}))
    pip.llen(recent_msg_key)

    result = pip.execute()
    return result[0]