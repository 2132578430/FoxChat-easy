"""
聊天服务模块

职责：
- 对话主流程编排（LangGraph Graph）
- 状态管理（current_state）
- 情绪分类
- 记忆总结
"""

from app.service.chat.state.session_lock import acquire_session_lock, release_session_lock

from app.service.chat.state.chat_msg_service import clear_chat_memory
from app.service.chat.state.state_manager import increment_round_counter
from app.service.chat.mood.store import load_current_state, save_mood_state
from app.service.chat.memory.memory_summary_service import async_summary_msg_parallel
from app.service.chat.profile.user_profile_service import update_user_profile_in_summary

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
    "increment_round_counter",
    "load_current_state",
    "save_mood_state",
    # 后台任务
    "async_summary_msg_parallel",
    "update_user_profile_in_summary",
]