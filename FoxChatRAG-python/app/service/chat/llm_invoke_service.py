"""
LLM 调用服务

职责：
- 构建 Prompt 并调用 LLM
- 检索相关记忆
- 记录 Token 消耗

重构说明：
- 使用策略层替代硬编码的 get_chat_model()
- 需要传入 llm_id 参数以查询用户配置
"""

import json
from typing import List, Optional

from loguru import logger
from langchain_core.language_models.chat_models import BaseMessage

from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.core.db.mysql_client import async_session_local
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.prompt_payload_builder import build_prompt_payload
from app.service.chat.history_event_retrieval_service import (
    retrieve_history_events_v2,
    format_history_events,
)
from app.service.chat.strategy.base_strategy import ChatInvokeStrategy
from app.service.llm_config_service import get_llm_configs_batch
from app.util import chroma_util
from app.util.template_util import escape_template


async def invoke_llm_with_retrieval(
    parsed: "ParsedMemories",
    history_msg: List[BaseMessage],
    init_memory: str,
    msg_content: str,
    user_id: str,
    llm_id: str,
    recent_messages: List[str] = None,
    relevant_memories_text: str = "",
    db = None,
) -> str:
    """
    使用预计算的检索结果调用 LLM（跳过 search_relevant_memories）

    Args:
        parsed: 解析后的记忆数据
        history_msg: 历史消息列表
        init_memory: 初始化记忆
        msg_content: 用户消息内容
        user_id: 用户 ID
        llm_id: 模型 ID（必需，用于查询用户配置）
        recent_messages: 最近消息列表
        relevant_memories_text: 预计算的检索结果文本（空字符串表示无检索结果）
        db: 数据库会话（可选，如果没有传入则自动创建）

    Returns:
        LLM 响应文本
    """
    from app.service.chat.memory_parser import build_static_anchors

    # 获取用户配置（批量查询）
    # 如果没有传入 db，则自动创建 session
    if db:
        config_map = await get_llm_configs_batch(llm_id, db)
    else:
        async with async_session_local() as session:
            config_map = await get_llm_configs_batch(llm_id, session)

    prompt_text = await PromptManager.get_prompt("chat_system")
    prompt_text = escape_template(
        prompt_text,
        ["static_anchors", "user_profile_summary", "historical_context", "current_state", "behavior_guide", "talkativeness_guidance"],
    )

    soul = await PromptManager.get_soul("soul")

    historical_context = relevant_memories_text if relevant_memories_text else parsed.memory_bank_summary

    static_anchors = build_static_anchors(
        soul=soul or "",
        role_declaration=parsed.role_declaration,
        core_anchor=parsed.core_anchor_text,
        character_card=init_memory,
        character_card_detail=parsed.character_card_detail,
        mes_example=parsed.character_card_examples,
    )

    # 构建行为指南注入文本
    behavior_guide_text = ""
    if parsed.behavior_guide_text and parsed.behavior_guide_text.strip():
        behavior_guide_text = f"【行为指南】\n{parsed.behavior_guide_text.strip()}"

    # 根据健谈程度构建长度指导
    talkativeness = parsed.talkativeness
    if talkativeness <= 0.3:
        talkativeness_guidance = "【输出长度指导】当前角色话少寡言，每次只回应必要内容，用最少的词表达。不要展开，不要多说一句废话。"
    elif talkativeness <= 0.6:
        talkativeness_guidance = "【输出长度指导】当前角色话量适中，像日常聊天一样自然回应，不刻意压缩也不刻意拉长。"
    elif talkativeness <= 0.8:
        talkativeness_guidance = "【输出长度指导】当前角色较为健谈，展开你的想法，用动作与对话交替表达，构建生动的互动。禁止只回一句话就结束，至少要有2-3轮对话内容的量。"
    else:
        talkativeness_guidance = "【输出长度指导】当前角色非常健谈，尽情表达，多段展开。用丰富的动作和对话交替构建沉浸式互动体验。禁止简短回应，每次回复要像真正健谈的人一样说很多。"
    logger.debug(f"【健谈程度】talkativeness={talkativeness}, guidance={talkativeness_guidance}")

    payload = build_prompt_payload(
        static_anchors=static_anchors,
        user_profile_summary=parsed.user_profile_summary,
        historical_context=historical_context,
        current_state=parsed.current_state,
        behavior_guide=behavior_guide_text,
        talkativeness_guidance=talkativeness_guidance,
        history_msg=history_msg,
        user_message=msg_content,
        recent_messages=recent_messages,
        enable_dedup=True,
        enable_conflict_priority=True,
    )

    logger.info(f"【Payload】注入: {payload.blocks_injected}, 空块省略: {payload.blocks_omitted}")
    if payload.duplicates_removed:
        logger.info(f"【Payload去重】移除: {payload.duplicates_removed}")

    # 使用策略层调用 LLM
    strategy = ChatInvokeStrategy()

    # 构建消息列表（用于 LiteLLM）
    messages = []
    for msg in history_msg:
        msg_type = msg.type if hasattr(msg, 'type') else "user"
        role = {"human": "user", "ai": "assistant"}.get(msg_type, msg_type)
        messages.append({
            "role": role,
            "content": msg.content
        })
    messages.append({
        "role": "user",
        "content": msg_content
    })

    # 添加 system prompt 到消息开头
    system_prompt = prompt_text.format(
        static_anchors=payload.static_anchors,
        user_profile_summary=payload.user_profile_summary,
        historical_context=payload.historical_context,
        current_state=payload.current_state,
        behavior_guide=payload.behavior_guide,
        talkativeness_guidance=payload.talkativeness_guidance,
    )
    messages.insert(0, {"role": "system", "content": system_prompt})

    # 调试日志：打印完整 messages
    logger.debug(f"【完整Messages】共 {len(messages)} 条消息")
    for i, msg in enumerate(messages):
        content_preview = msg["content"][:3000] if len(msg["content"]) > 3000 else msg["content"]
        logger.debug(f"  [{i}] role={msg['role']}, content={content_preview}...")

    response_text = await strategy.invoke(messages, config_map)
    return response_text


async def search_relevant_memories(
    msg_content: str,
    user_id: str,
    llm_id: str,
    recent_messages: Optional[List[str]] = None,
) -> str:
    """
    检索相关记忆（主动检索：每轮都检索，不依赖触发词）

    Args:
        msg_content: 用户输入
        user_id: 用户 ID
        llm_id: 模型 ID
        recent_messages: 最近窗口消息列表

    Returns:
        格式化后的 relevant_memories 文本块
    """
    try:
        from app.service.chat.intent_classifier import classify_intent
        from app.common.constant.intent_config import IntentType

        # 意图判断
        intent_result = classify_intent(msg_content)
        logger.info(f"【意图判断】intent={intent_result.intent}, scope={intent_result.scope}, top_k={intent_result.top_k}, skip={intent_result.skip}")

        if intent_result.skip:
            logger.info("【意图判断】casual_chat，跳过检索")
            return ""

        # 检索 membank
        events = await retrieve_history_events_v2(
            query=msg_content,
            user_id=user_id,
            llm_id=llm_id,
            max_results=4,
            recent_messages=recent_messages,
            enable_rerank=True,
            scope=intent_result.scope,
            top_k=intent_result.top_k,
        )

        # 检索 summary
        documents = await chroma_util.search(
            ChromaTypeConstant.CHAT,
            msg_content,
            {"user_id": user_id, "llm_id": llm_id, "is_event": False}
        )

        # 合并结果
        result_parts = []

        if events:
            if intent_result.intent == IntentType.INTERACTION_Q:
                events.sort(key=lambda e: e.source_round)
                logger.info(f"【测试类查询】按 source_round 升序排序，共 {len(events)} 条事件")

            result_parts.append(format_history_events(events))
            logger.info(f"【主动检索】membank 返回 {len(events)} 条结构化事件")

        if documents:
            summary_lines = []
            for doc in documents[:3]:
                content = doc.page_content.strip()
                if content:
                    summary_lines.append(f"- {content}")
            if summary_lines:
                result_parts.append("【相关对话总结】\n" + "\n".join(summary_lines))
                logger.info(f"【主动检索】summary 返回 {len(summary_lines)} 条")

        if not result_parts:
            logger.info("【主动检索】无相关记忆")
            return ""

        return "\n\n".join(result_parts)

    except Exception as e:
        logger.warning(f"检索相关记忆失败: {e}")
        return ""


def _print_template(template_value):
    """打印最终注入的完整提示词"""
    if hasattr(template_value, 'to_string'):
        logger.info(f"【最终提示词】\n{template_value.to_string()}")
    elif hasattr(template_value, 'messages'):
        full_text = "\n".join([
            f"[{m.type if hasattr(m, 'type') else 'msg'}] {m.content}"
            for m in template_value.messages
        ])
        logger.info(f"【最终提示词】\n{full_text}")
    else:
        logger.info(f"【最终提示词】\n{template_value}")
    return template_value


