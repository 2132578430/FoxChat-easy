"""
Redis Key 构建工具

统一聊天服务相关的 Redis key 构建。
底层使用 LLMChatConstant.build_memory_key。
"""

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key


def build_init_memory_key(user_id: str, llm_id: str) -> str:
    """构建初始化记忆 key"""
    return build_memory_key(LLMChatConstant.INIT_MEMORY, user_id, llm_id)


def build_recent_msg_key(user_id: str, llm_id: str) -> str:
    """构建最近消息 key"""
    return build_memory_key(LLMChatConstant.RECENT_MSG, user_id, llm_id)


def build_current_state_key(user_id: str, llm_id: str) -> str:
    """构建当前状态 key"""
    return build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, user_id, llm_id)


def build_time_nodes_key(user_id: str, llm_id: str) -> str:
    """构建时间节点 key"""
    return build_memory_key(LLMChatConstant.ROLE_TIME_NODES, user_id, llm_id)


def build_round_counter_key(user_id: str, llm_id: str) -> str:
    """构建轮次计数器 key"""
    return f"chat:memory:{user_id}:{llm_id}:round_counter"


def build_summary_lock_key(user_id: str, llm_id: str) -> str:
    """构建总结锁 key"""
    return f"summary_lock:{user_id}:{llm_id}"


def build_summary_counter_key(user_id: str, llm_id: str) -> str:
    """构建总结计数器 key"""
    return f"summary_counter:{user_id}:{llm_id}"