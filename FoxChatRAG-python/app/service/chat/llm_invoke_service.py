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
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.language_models.chat_models import BaseMessage

from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.prompt_payload_builder import build_prompt_payload, payload_to_invoke_dict
from app.service.chat.history_event_retrieval_service import (
    retrieve_history_events_v2,
    format_history_events,
)
from app.service.chat.strategy.base_strategy import ChatInvokeStrategy
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
        db: 数据库会话（可选，用于查询配置）

    Returns:
        LLM 响应文本
    """
    from app.service.chat.memory_parser import build_static_anchors
    from app.service.llm_config_service import get_llm_configs_batch

    # 获取用户配置（批量查询）
    if db:
        config_map = await get_llm_configs_batch(llm_id, db)
    else:
        # 如果没有 db，使用默认配置（向后兼容）
        logger.warning(f"【LLM调用】无 db session，使用默认配置")
        config_map = {}

    prompt_text = await PromptManager.get_prompt("chat_system")
    prompt_text = escape_template(
        prompt_text,
        ["static_anchors", "user_profile_summary", "historical_context", "current_state"],
    )
    template = ChatPromptTemplate(
        [
            ("system", prompt_text),
            MessagesPlaceholder("history_msg"),
            ("human", "Reply with a response that matches the current memory and identity according to the above prompts and memory template:\n{user_message}")
        ]
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

    payload = build_prompt_payload(
        static_anchors=static_anchors,
        user_profile_summary=parsed.user_profile_summary,
        historical_context=historical_context,
        current_state=parsed.current_state,
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
        messages.append({
            "role": msg.type if hasattr(msg, 'type') else "user",
            "content": msg.content
        })
    messages.append({
        "role": "user",
        "content": f"Reply with a response that matches the current memory and identity according to the above prompts and memory template:\n{msg_content}"
    })

    # 添加 system prompt 到消息开头
    system_prompt = template.format(**payload_to_invoke_dict(payload))
    messages.insert(0, {"role": "system", "content": system_prompt})

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


