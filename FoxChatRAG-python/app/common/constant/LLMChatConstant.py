from enum import StrEnum


class LLMChatConstant(StrEnum):
    CHAT_MEMORY = "chat:memory"
    RECENT_MSG = "recent_msg"

    RAW_EXPERIENCE = "raw_experience"
    CORE_ANCHOR = "core_anchor"
    USER_PROFILE = "user_profile"
    CHARACTER_CARD = "character_card"
    MEMORY_BANK = "memory_bank"

    # 当前状态容器
    ROLE_CURRENT_STATE = "role_current_state"

    # 计数器
    ROUND_COUNTER = "round_counter"

    # Summary 相关 key 前缀
    SUMMARY_LOCK = "summary_lock"
    SUMMARY_COUNTER = "summary_counter"

def build_chat_key(prefix: str, user_id: str, llm_id: str, suffix: str = "") -> str:
    """统一构建聊天相关 Redis key

    Args:
        prefix: key 前缀，如 LLMChatConstant.CHAT_MEMORY / SUMMARY_LOCK
        suffix: key 后缀（仅 chat:memory 前缀的 key 需要）
    """
    base = f"{prefix}:{user_id}:{llm_id}"
    return f"{base}:{suffix}" if suffix else base


# 事件类型中文标签映射（用于结构注入）
EVENT_TYPE_LABELS = {
    # State 类
    "identity": "身份信息",
    "preference": "偏好信息",
    "boundary": "边界底线",
    # Event 类
    "follow_up": "跟进事项",
    "share_experience": "经历分享",
    "commitment": "承诺约定",
    "relation_change": "关系变化",
    "express_emotion": "情绪表达",
    "interaction": "互动测试",
    "other": "其他",
}