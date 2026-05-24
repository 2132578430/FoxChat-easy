"""
聊天服务类型定义

定义聊天相关的数据结构，避免循环导入。
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ChatMemories:
    """聊天所需的记忆数据容器"""
    init_memory: str
    recent_msg: List[str]
    character_card_json: str
    core_anchor_json: str
    user_profile_json: str
    memory_bank_json: str
    current_state_json: str


@dataclass
class ParsedMemories:
    """解析后的记忆数据容器"""
    character_card_examples: str
    character_card_detail: str
    behavior_guide_text: str
    talkativeness: float
    role_declaration: str
    core_anchor_text: str
    user_profile_summary: str
    memory_bank_summary: str
    current_state: str