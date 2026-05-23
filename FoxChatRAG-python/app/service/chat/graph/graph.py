"""
主 Chat Graph 构建与编译

DAG 拓扑:
  START → PRE_FLIGHT → FETCH_MEMORY → PARSE_MEMORY → CLASSIFY_INTENT
    → [RETRIEVE | SKIP] → INVOKE_LLM
    → [SAVE_MESSAGE ∥ FORMAT_OUTPUT ∥ CLASSIFY_EMOTION ∥ TRIGGER_SUMMARY]
    → UNLOCK → END

Checkpointer:
  默认使用 MemorySaver (in-memory)，适合开发环境。
  生产环境可切换到 SQLite: pip install langgraph-checkpoint-sqlite
"""

import os

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.service.chat.graph.state import ChatState
from app.service.chat.graph.nodes import (
    pre_flight,
    fetch_memory,
    parse_memory,
    classify_intent_node,
    retrieve,
    skip_retrieval,
    invoke_llm,
    save_message,
    format_output,
    classify_emotion,
    trigger_summary,
    unlock,
)
from app.service.chat.graph.router import need_retrieval


def build_main_graph() -> StateGraph:
    """构建主 Chat 流程的 StateGraph"""

    builder = StateGraph(ChatState)

    # === Nodes ===
    builder.add_node("pre_flight", pre_flight)
    builder.add_node("fetch_memory", fetch_memory)
    builder.add_node("parse_memory", parse_memory)
    builder.add_node("classify_intent", classify_intent_node)
    builder.add_node("retrieve", retrieve)
    builder.add_node("skip_retrieval", skip_retrieval)
    builder.add_node("invoke_llm", invoke_llm)
    builder.add_node("save_message", save_message)
    builder.add_node("format_output", format_output)
    builder.add_node("classify_emotion", classify_emotion)
    builder.add_node("trigger_summary", trigger_summary)
    builder.add_node("unlock", unlock)

    # === Edges ===
    builder.add_edge(START, "pre_flight")
    builder.add_edge("pre_flight", "fetch_memory")
    builder.add_edge("fetch_memory", "parse_memory")
    builder.add_edge("parse_memory", "classify_intent")

    # Conditional routing
    builder.add_conditional_edges(
        "classify_intent",
        need_retrieval,
        {
            "retrieve": "retrieve",
            "skip_retrieval": "skip_retrieval",
        },
    )

    builder.add_edge("retrieve", "invoke_llm")
    builder.add_edge("skip_retrieval", "invoke_llm")

    # 4-way parallel post-processing
    builder.add_edge("invoke_llm", "save_message")
    builder.add_edge("invoke_llm", "format_output")
    builder.add_edge("invoke_llm", "classify_emotion")
    builder.add_edge("invoke_llm", "trigger_summary")

    # All converge to unlock, then END
    builder.add_edge("save_message", "unlock")
    builder.add_edge("format_output", "unlock")
    builder.add_edge("classify_emotion", "unlock")
    builder.add_edge("trigger_summary", "unlock")
    builder.add_edge("unlock", END)

    return builder


def compile_main_graph(checkpointer=None):
    """编译主 Graph（可选传入 checkpointer）"""
    builder = build_main_graph()
    if checkpointer is None:
        checkpointer = _get_default_checkpointer()
    return builder.compile(checkpointer=checkpointer)


def _get_default_checkpointer():
    """获取默认 checkpointer：优先 SQLite，回退 MemorySaver"""
    sqlite_path = os.environ.get("CHECKPOINT_DB_PATH", "")
    if sqlite_path:
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            return AsyncSqliteSaver.from_conn_string(sqlite_path)
        except ImportError:
            pass
    return MemorySaver()


# 默认编译（MemorySaver），用于快速启动
main_graph = compile_main_graph()
main_graph_no_checkpoint = build_main_graph().compile()
