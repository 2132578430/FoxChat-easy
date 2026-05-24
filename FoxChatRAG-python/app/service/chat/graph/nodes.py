"""
Chat Graph 节点函数

每个节点 = (ChatState) -> partial dict，内部调用现有 service 层。
不包含业务逻辑，只做参数传递和状态更新。
"""

from typing import List

from loguru import logger
from app.schemas.current_state import UnfinishedItem, ItemStatus
from app.service.chat.graph.state import ChatState
from app.service.chat.state_manager import (
    increment_round_counter,
    clean_expired_unfinished_items,
    update_unfinished_items,
    get_current_state,
)
from app.service.chat.time_node_service import route_due_time_nodes
from app.service.chat.chat_redis_service import (
    fetch_all_memories,
    save_chat_to_redis,
    build_history_message,
)
from app.service.chat.memory_parser import (
    parse_character_card,
    parse_core_anchor,
    parse_user_profile,
    parse_memory_bank,
    parse_current_state,
)
from app.service.chat.intent_classifier import classify_intent
from app.service.chat.llm_invoke_service import (
    search_relevant_memories,
    invoke_llm_with_retrieval,
)
from app.service.chat.response_parser import parse_action_tags
from app.service.chat.emotion_classifier import classify_and_update_emotion
from app.service.chat.memory_summary_service import trigger_summary_with_counter
from app.service.chat.timer_scheduler import SUMMARY_MAX_TRIGGER_THRESHOLD
from app.service.chat.common import build_recent_msg_key
from app.util import strip_all_tags, strip_think_only
from app.service.chat.types import ParsedMemories


# ============================================================
# Pre-flight
# ============================================================

async def pre_flight(state: ChatState) -> dict:
    """轮数初始化 + 清理过期 + 时间节点路由（lock 由 API 层管理）"""
    user_id = state["user_id"]
    llm_id = state["llm_id"]

    current_round = increment_round_counter(user_id, llm_id) - 1
    clean_expired_unfinished_items(user_id, llm_id, current_round)

    routing = route_due_time_nodes(user_id, llm_id, current_round)
    if routing["unfinished_items"]:
        activated_items = [
            UnfinishedItem(
                content=item["content"],
                status=ItemStatus.PENDING,
                confidence=item.get("confidence", 0.9),
                expire_rounds=item.get("expire_rounds", 6),
                update_round=current_round,
                update_reason="时间节点到期激活",
                created_at=item.get("created_at"),
                due_at=item.get("due_at"),
            )
            for item in routing["unfinished_items"]
        ]
        update_unfinished_items(user_id, llm_id, activated_items, current_round)
        logger.info(f"【时间节点激活】B层: {len(activated_items)} 条事项写入 unfinished_items")

    recent_msg_key = build_recent_msg_key(user_id, llm_id)

    return {
        "current_round": current_round,
        "recent_msg_key": recent_msg_key,
    }


# ============================================================
# Memory
# ============================================================

async def fetch_memory(state: ChatState) -> dict:
    """批量拉取 Redis 记忆（7 个 key 一次 pipeline）"""
    memories = await fetch_all_memories(state["user_id"], state["llm_id"])
    return {"memories": memories}


async def parse_memory(state: ChatState) -> dict:
    """解析 5 种记忆 + 构建历史消息"""
    memories = state["memories"]

    character_card_examples, character_card_detail = parse_character_card(memories.character_card_json)
    role_declaration, core_anchor_text = parse_core_anchor(memories.core_anchor_json)
    user_profile_summary = parse_user_profile(memories.user_profile_json)
    memory_bank_summary = parse_memory_bank(memories.memory_bank_json)
    current_state_text = parse_current_state(memories.current_state_json, state["current_round"])

    parsed = ParsedMemories(
        character_card_examples=character_card_examples,
        character_card_detail=character_card_detail,
        role_declaration=role_declaration,
        core_anchor_text=core_anchor_text,
        user_profile_summary=user_profile_summary,
        memory_bank_summary=memory_bank_summary,
        current_state=current_state_text,
    )

    history_msg = build_history_message(memories.recent_msg)

    return {"parsed": parsed, "history_msg": history_msg}


# ============================================================
# Intent & Retrieval
# ============================================================

async def classify_intent_node(state: ChatState) -> dict:
    """两层意图分类（规则 + 语义），结果用于条件路由"""
    intent_result = classify_intent(state["msg_content"])
    return {"intent_result": {
        "intent": str(intent_result.intent),
        "scope": [str(s) for s in intent_result.scope],
        "top_k": int(intent_result.top_k),
        "skip": bool(intent_result.skip),
        "confidence": float(intent_result.confidence),
    }}


async def retrieve(state: ChatState) -> dict:
    """主动检索：BM25 + ChromaDB Vector + Rerank，结果存入 state"""
    relevant_memories_text = await search_relevant_memories(
        msg_content=state["msg_content"],
        user_id=state["user_id"],
        llm_id=state["llm_id"],
        recent_messages=state["memories"].recent_msg,
    )
    return {"relevant_memories_text": relevant_memories_text}


async def skip_retrieval(state: ChatState) -> dict:
    """跳过检索（casual_chat），relevant_memories_text 为空"""
    return {"relevant_memories_text": ""}


# ============================================================
# LLM Invocation (Build Prompt + Call LLM)
# ============================================================

async def invoke_llm(state: ChatState) -> dict:
    """构建 Prompt 并调用 LLM，使用预计算的 retrieval 结果"""
    response = await invoke_llm_with_retrieval(
        parsed=state["parsed"],
        history_msg=state["history_msg"],
        init_memory=state["memories"].init_memory,
        msg_content=state["msg_content"],
        user_id=state["user_id"],
        llm_id=state["llm_id"],
        recent_messages=state["memories"].recent_msg,
        relevant_memories_text=state.get("relevant_memories_text", ""),
    )
    return {"ai_response": response}


# ============================================================
# Post-processing (4 路并行)
# ============================================================

async def save_message(state: ChatState) -> dict:
    """保存 human + AI 消息到 Redis"""
    await save_chat_to_redis(
        state["recent_msg_key"], state["msg_content"], state["ai_response"]
    )
    return {}


async def format_output(state: ChatState) -> dict:
    """解析 LLM 输出为 MessageBlock 列表"""
    clean_response = strip_think_only(state["ai_response"])
    blocks = parse_action_tags(clean_response)
    blocks_data = [block.model_dump() for block in blocks]
    return {"blocks": blocks_data}


async def classify_emotion(state: ChatState) -> dict:
    """分类 AI 回复的情绪并更新 current_state"""
    pure_text = strip_all_tags(state["ai_response"])
    current_round = increment_round_counter(state["user_id"], state["llm_id"])
    await classify_and_update_emotion(
        state["user_id"], state["llm_id"], pure_text, current_round
    )
    current_state = get_current_state(state["user_id"], state["llm_id"], current_round)
    emotion = current_state.emotion.value if current_state.emotion else "neutral"
    return {"emotion": emotion}


async def trigger_summary(state: ChatState) -> dict:
    """消息数 >= 阈值时触发后台摘要"""
    from app.core.db.redis_client import redis_client

    key = build_recent_msg_key(state["user_id"], state["llm_id"])
    try:
        msg_count = await redis_client.llen(key) or 0
    except Exception:
        msg_count = 0

    if msg_count >= SUMMARY_MAX_TRIGGER_THRESHOLD:
        await trigger_summary_with_counter(
            key, msg_count, state["user_id"], state["llm_id"], trigger_source="max_threshold"
        )
    return {}


# ============================================================
# Cleanup
# ============================================================

async def unlock(state: ChatState) -> dict:
    """汇聚节点（lock 由 API 层 try/finally 管理）"""
    return {}
