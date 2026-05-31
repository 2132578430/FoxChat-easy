"""
流式 LLM 调用服务

复用 invoke_llm_with_retrieval 的 prompt 构建逻辑，
将 LLM 调用改为 litellm stream=True，逐 token yield。
"""

import asyncio
from typing import AsyncGenerator, List

import litellm
from loguru import logger

from app.core.db.mysql_client import async_session_local
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.prompt_payload_builder import build_prompt_payload
from app.service.chat.memory_parser import build_static_anchors
from app.service.chat.state_manager import (
    increment_round_counter,
    clean_expired_unfinished_items,
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
from app.service.chat.history_event_retrieval_service import (
    retrieve_history_events_v2,
    format_history_events,
)
from app.service.chat.emotion_classifier import classify_and_update_emotion
from app.service.llm_config_service import get_llm_configs_batch
from app.service.chat.strategy.base_strategy import format_model_name
from app.service.chat.common import build_recent_msg_key
from app.util.template_util import escape_template


async def stream_llm_response(
    user_id: str,
    llm_id: str,
    msg_content: str,
) -> AsyncGenerator[str, None]:
    """
    流式 LLM 调用：复用 prompt 构建，litellm stream=True。

    Args:
        user_id: 用户ID
        llm_id: 模型ID
        msg_content: 用户输入文本

    Yields:
        str: 每个 LLM token
    """
    # ── 1. 轮数 & 记忆拉取（复用 pre_flight + fetch_memory + parse_memory） ──
    current_round = increment_round_counter(user_id, llm_id) - 1
    clean_expired_unfinished_items(user_id, llm_id, current_round)

    recent_msg_key = build_recent_msg_key(user_id, llm_id)
    memories = fetch_all_memories(user_id, llm_id, recent_msg_key)

    parsed = parse_character_card(memories.init_memory)
    parsed = parse_core_anchor(parsed)
    parsed = parse_user_profile(memories, parsed)
    parsed = parse_memory_bank(memories, parsed)
    parsed = parse_current_state(memories, parsed)

    # ── 2. 意图分类 ──
    intent_result = classify_intent(msg_content)

    # ── 3. 检索（非闲聊时） ──
    relevant_memories_text = ""
    if not intent_result.skip:
        events = await retrieve_history_events_v2(
            query=msg_content,
            user_id=user_id,
            llm_id=llm_id,
            recent_messages=memories.recent_msg or [],
            scope=intent_result.scope if intent_result.scope else None,
            top_k=intent_result.top_k,
        )
        relevant_memories_text = format_history_events(events)

    # ── 4. 构建 Prompt（复用 llm_invoke_service 逻辑） ──
    async with async_session_local() as db:
        config_map = await get_llm_configs_batch(llm_id, db)

    prompt_text = await PromptManager.get_prompt("chat_system")
    prompt_text = escape_template(
        prompt_text,
        ["static_anchors", "user_profile_summary", "historical_context",
         "current_state", "behavior_guide", "talkativeness_guidance"],
    )

    soul = await PromptManager.get_soul("soul")

    static_anchors = build_static_anchors(
        soul=soul or "",
        role_declaration=parsed.role_declaration,
        core_anchor=parsed.core_anchor_text,
        character_card=memories.init_memory,
        character_card_detail=parsed.character_card_detail,
        mes_example=parsed.character_card_examples,
    )

    historical_context = relevant_memories_text if relevant_memories_text else parsed.memory_bank_summary

    behavior_guide_text = ""
    if parsed.behavior_guide_text and parsed.behavior_guide_text.strip():
        behavior_guide_text = f"【行为指南】\n{parsed.behavior_guide_text.strip()}"

    talkativeness = parsed.talkativeness
    if talkativeness <= 0.3:
        talkativeness_guidance = "【输出长度指导】当前角色话少寡言，每次只回应必要内容，用最少的词表达。不要展开，不要多说一句废话。"
    elif talkativeness <= 0.5:
        talkativeness_guidance = "【输出长度指导】当前角色话量适中，像日常聊天一样自然回应，不刻意压缩也不刻意拉长。"
    elif talkativeness <= 0.75:
        talkativeness_guidance = "【输出长度指导】当前角色较为健谈，展开你的想法，用动作与对话交替表达，构建生动的互动。禁止只回一句话就结束，至少要有2-3轮对话内容的量。"
    else:
        talkativeness_guidance = "【输出长度指导】当前角色非常健谈，尽情表达，多段展开。用丰富的动作和对话交替构建沉浸式互动体验。禁止简短回应，每次回复要像真正健谈的人一样说很多。"

    payload = build_prompt_payload(
        static_anchors=static_anchors,
        user_profile_summary=parsed.user_profile_summary,
        historical_context=historical_context,
        current_state=parsed.current_state,
        behavior_guide=behavior_guide_text,
        talkativeness_guidance=talkativeness_guidance,
        history_msg=build_history_message(memories.recent_msg),
        user_message=msg_content,
        recent_messages=memories.recent_msg,
        enable_dedup=True,
        enable_conflict_priority=True,
    )

    system_prompt = prompt_text.format(
        static_anchors=payload.static_anchors,
        user_profile_summary=payload.user_profile_summary,
        historical_context=payload.historical_context,
        current_state=payload.current_state,
        behavior_guide=payload.behavior_guide,
        talkativeness_guidance=payload.talkativeness_guidance,
    )

    history_msg = build_history_message(memories.recent_msg, recent_msg_key)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history_msg:
        msg_type = msg.type if hasattr(msg, 'type') else "user"
        role = {"human": "user", "ai": "assistant"}.get(msg_type, msg_type)
        messages.append({"role": role, "content": msg.content})
    messages.append({"role": "user", "content": msg_content})

    # ── 5. 流式调用 LLM ──
    config = config_map.get("chat", {})
    if not config:
        raise ValueError("chat 场景未配置模型")

    model = format_model_name(config["model_name"])

    logger.info(f"[StreamLLM] model={model}, messages={len(messages)}条")

    full_response = ""  # 累积完整响应（用于后续保存和情感分类）

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            api_key=config["model_api_key"],
            base_url=config["model_base_url"],
            temperature=config.get("model_temperature", 0.8),
            max_tokens=config.get("model_max_tokens", 4096),
            stream=True,
            timeout=120,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token

    except Exception as e:
        logger.error(f"[StreamLLM] 调用失败: {e}")
        raise

    # ── 6. 后处理（保存消息 + 情感分类，在流结束后异步执行） ──
    if full_response:
        try:
            await save_chat_to_redis(recent_msg_key, msg_content, full_response)
        except Exception as e:
            logger.warning(f"[StreamLLM] 保存消息失败（非致命）: {e}")

        try:
            emotion = await classify_and_update_emotion(
                user_id=user_id,
                llm_id=llm_id,
                model_reply=full_response,
            )
            # 把 emotion 存起来，gRPC 层会在 is_final 包里带出去
            stream_llm_response._last_emotion = emotion
        except Exception as e:
            logger.warning(f"[StreamLLM] 情感分类失败（非致命）: {e}")
            stream_llm_response._last_emotion = "neutral"


stream_llm_response._last_emotion = "neutral"
