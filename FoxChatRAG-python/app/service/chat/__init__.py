"""
聊天服务模块

职责：
- 对话主流程编排（LangGraph Graph）
- 状态管理（current_state）
- 时间节点管理（time_node）
- 情绪分类
- 记忆总结
"""

from app.service.chat.session_lock import acquire_session_lock, release_session_lock

from app.service.chat.chat_msg_service import clear_chat_memory
from app.service.chat.state_manager import (
    get_current_state,
    update_current_state,
    update_unfinished_items,
    check_and_expire_fields,
    increment_round_counter,
    get_current_round,
)
from app.service.chat.time_node_service import (
    create_time_node,
    get_all_time_nodes,
    check_and_activate_due_time_nodes,
    extract_time_node_from_text,
)
from app.service.chat.memory_summary_service import async_summary_msg_parallel
from app.service.chat.user_profile_service import update_user_profile_in_summary
from app.service.chat.emotion_classifier import classify_and_update_emotion

from app.service.chat.graph.graph import main_graph, build_main_graph, compile_main_graph
__all__ = [
    # 会话锁（分布式）
    "acquire_session_lock",
    "release_session_lock",
    # 主流程
    "clear_chat_memory",
    # LangGraph
    "main_graph",
    "build_main_graph",
    "compile_main_graph",
    # 状态管理
    "get_current_state",
    "update_current_state",
    "update_unfinished_items",
    "check_and_expire_fields",
    "increment_round_counter",
    "get_current_round",
    # 时间节点
    "create_time_node",
    "get_all_time_nodes",
    "check_and_activate_due_time_nodes",
    "extract_time_node_from_text",
    # 后台任务
    "async_summary_msg_parallel",
    "update_user_profile_in_summary",
    "classify_and_update_emotion",
]