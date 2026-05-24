"""
ChatState — LangGraph 主对话流程的状态定义

每个字段对应 graph 中一个或多个节点的输入/输出。
"""

from typing import TypedDict, List, Any, Dict

from app.service.chat.types import ChatMemories, ParsedMemories


class ChatState(TypedDict, total=False):
    """主对话流程的共享状态"""

    # === 入口参数 ===
    user_id: str
    llm_id: str
    msg_content: str

    # === Pre-flight ===
    current_round: int
    recent_msg_key: str

    # === 记忆层 ===
    memories: ChatMemories
    parsed: ParsedMemories
    history_msg: List[Any]  # List[BaseMessage]

    # === Intent & Retrieval ===
    intent_result: Dict[str, Any]
    relevant_memories_text: str

    # === LLM ===
    ai_response: str

    # === Output ===
    blocks: List[dict]
    emotion: str
