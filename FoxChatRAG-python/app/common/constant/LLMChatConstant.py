from enum import StrEnum


class LLMChatConstant(StrEnum):
    CHAT_MEMORY = "chat:memory:"
    INIT_MEMORY = "role_init_memory"
    RECENT_MSG = "recent_msg"

    RAW_EXPERIENCE = "raw_experience"
    CORE_ANCHOR = "core_anchor"
    USER_PROFILE = "user_profile"
    CHARACTER_CARD = "character_card"
    MEMORY_BANK = "memory_bank"

    ROLE_EMOTION_STATE = "role_emotion_state"
    ROLE_EMOTION_LOG = "role_emotion_log"

    # 阶段2新增：当前状态容器与时间节点
    ROLE_CURRENT_STATE = "role_current_state"
    ROLE_TIME_NODES = "role_time_nodes"


def build_memory_key(suffix: str, user_id: str, llm_id: str) -> str:
    return f"{LLMChatConstant.CHAT_MEMORY}{user_id}:{llm_id}:{suffix}"


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