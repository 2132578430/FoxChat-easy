"""
LLM 调用服务

职责：
- 构建 Prompt 并调用 LLM（流式 + 非流式）
- 检索相关记忆
- 记录 Token 消耗
"""

import asyncio
import json
from typing import List, Optional, AsyncGenerator

import litellm
from loguru import logger
from langchain_core.language_models.chat_models import BaseMessage

from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.core.db.mysql_client import async_session_local
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.llm.prompt_payload_builder import build_prompt_payload
from app.service.chat.memory.history_event_retrieval_service import (
    retrieve_history_events_v2,
    format_history_events,
)
from app.service.chat.strategy.base_strategy import ChatInvokeStrategy, format_model_name
from app.service.llm_config_service import get_llm_configs_batch
from app.util import chroma_util
from app.util.template_util import escape_template

# ── 健谈程度 → 输出长度指导映射 ──────────────────────
# (上限阈值, 指导文本)，按阈值升序排列，查找时取第一个命中
_TALKATIVENESS_GUIDANCE: list[tuple[float, str]] = [
    (0.25, "当前角色极度寡言，每次只回应最必要的词，几乎不展开。越短越好。"),
    (0.55, "当前角色话量适中，像日常聊天一样自然回应，可以适当展开但不要过度。"),
    (0.85, "当前角色健谈，欢迎多段展开，用动作与对话交替构建生动互动。多说话，不要简短回应，至少3-4轮对话内容的量。"),
    (1.00, "当前角色话痨，尽情表达，连续说很多很多话。用丰富的动作和对话交替构建沉浸式互动体验。禁止简短回应，每次回复要像真正话痨的人一样长篇大论。"),
]


def _get_talkativeness_guidance(talkativeness: float) -> str:
    """根据健谈程度分数返回对应的输出长度指导文本。"""
    for threshold, guidance in _TALKATIVENESS_GUIDANCE:
        if talkativeness <= threshold:
            return guidance
    return _TALKATIVENESS_GUIDANCE[-1][1]


async def _build_chat_messages(
    parsed: "ParsedMemories",
    history_msg: List[BaseMessage],
    msg_content: str,
    user_id: str,
    llm_id: str,
    recent_messages: List[str] = None,
    relevant_memories_text: str = "",
    db = None,
) -> tuple[list[dict], dict, str]:
    """
    构建 LLM 消息列表（公共 prompt builder）

    从 invoke_llm_with_retrieval 提取，供流式和非流式路径共用。

    Returns:
        (messages, config_map, system_prompt)
        - messages: LiteLLM 格式消息列表 [{"role":..., "content":...}, ...]
        - config_map: LLM 配置字典 {"chat": {...}, ...}
        - system_prompt: 格式化后的系统提示词（用于日志/调试）
    """
    from app.service.chat.memory.memory_parser import build_static_anchors

    # 批量查询用户配置
    logger.debug(f"[BuildMessages] 开始获取 LLM 配置: llm_id={llm_id}")
    if db:
        config_map = await get_llm_configs_batch(llm_id, db)
    else:
        # 当没有提供数据库会话时，使用默认的异步会话池
        async with async_session_local() as session:
            config_map = await get_llm_configs_batch(llm_id, session)
    logger.debug(f"[BuildMessages] LLM 配置获取完成: llm_id={llm_id}")

    # 获取提示词模版
    prompt_text = await PromptManager.get_prompt("chat_system")
    # 转义模板中的变量，防止 SQL 注入
    prompt_text = escape_template(
        prompt_text,
        ["static_anchors", "user_profile_summary", "historical_context", "current_state", "behavior_guide", "talkativeness_guidance"],
    )

    # 获取角色全局提示词
    soul = await PromptManager.get_soul("soul")

    # 获取历史上下文
    historical_context = relevant_memories_text if relevant_memories_text else parsed.memory_bank_summary

    # 构建静态锚点
    static_anchors = build_static_anchors(
        soul=soul or "",
        role_declaration=parsed.role_declaration,
        core_anchor=parsed.core_anchor_text,
        character_card="",
        character_card_detail=parsed.character_card_detail,
        mes_example=parsed.character_card_examples,
    )

    # 构建行为指南注入文本
    behavior_guide_text = (parsed.behavior_guide_text or "").strip()

    # 根据健谈指数构建长度指导
    talkativeness = parsed.talkativeness
    talkativeness_guidance = _get_talkativeness_guidance(talkativeness)
    logger.debug(f"【健谈指数】talkativeness={talkativeness}, guidance={talkativeness_guidance}")

    # 构建注入提示词
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

    # 构建 messages 列表
    messages = []
    for msg in history_msg:
        msg_type = msg.type if hasattr(msg, 'type') else "user"
        role = {"human": "user", "ai": "assistant"}.get(msg_type, msg_type)
        messages.append({"role": role, "content": msg.content})
    # 用户信息
    messages.append({"role": "user", "content": msg_content})

    # 构建提示词
    system_prompt = prompt_text.format(
        static_anchors=payload.static_anchors,
        user_profile_summary=payload.user_profile_summary,
        historical_context=payload.historical_context,
        current_state=payload.current_state,
        behavior_guide=payload.behavior_guide,
        talkativeness_guidance=payload.talkativeness_guidance,
    )
    messages.insert(0, {"role": "system", "content": system_prompt})

    logger.debug(f"【完整Messages】共 {len(messages)} 条消息")
    for i, msg in enumerate(messages):
        content_preview = msg["content"][:3000] if len(msg["content"]) > 3000 else msg["content"]
        logger.debug(f"  [{i}] role={msg['role']}, content={content_preview}...")

    return messages, config_map, system_prompt

async def invoke_llm_with_retrieval(
    parsed: "ParsedMemories",
    history_msg: List[BaseMessage],
    msg_content: str,
    user_id: str,
    llm_id: str,
    recent_messages: List[str] = None,
    relevant_memories_text: str = "",
    db = None,
) -> str:
    """
    使用预计算的检索结果调用 LLM（非流式）

    Args:
        parsed: 解析后的记忆数据
        history_msg: 历史消息列表
        msg_content: 用户消息内容
        user_id: 用户 ID
        llm_id: 模型 ID
        recent_messages: 最近消息列表
        relevant_memories_text: 预计算的检索结果文本
        db: 数据库会话（可选）

    Returns:
        LLM 响应文本
    """
    messages, config_map, _ = await _build_chat_messages(
        parsed=parsed,
        history_msg=history_msg,
        msg_content=msg_content,
        user_id=user_id,
        llm_id=llm_id,
        recent_messages=recent_messages,
        relevant_memories_text=relevant_memories_text,
        db=db,
    )

    strategy = ChatInvokeStrategy()
    return await strategy.invoke(messages, config_map)


async def stream_llm_with_retrieval(
    parsed: "ParsedMemories",
    history_msg: List[BaseMessage],
    msg_content: str,
    user_id: str,
    llm_id: str,
    recent_messages: List[str] = None,
    relevant_memories_text: str = "",
    db = None,
) -> AsyncGenerator[str, None]:
    """
    流式 LLM 调用（使用预计算的检索结果）

    与 invoke_llm_with_retrieval 共享同一套 _build_chat_messages，
    区别仅在于 LLM 调用方式：stream=True 逐 token yield。

    Yields:
        str: 每个 LLM token
    """
    messages, config_map, _ = await _build_chat_messages(
        parsed=parsed,
        history_msg=history_msg,
        msg_content=msg_content,
        user_id=user_id,
        llm_id=llm_id,
        recent_messages=recent_messages,
        relevant_memories_text=relevant_memories_text,
        db=db,
    )

    config = config_map.get("chat", {})
    if not config:
        raise ValueError("chat 场景未配置模型")

    model = format_model_name(config["model_name"])

    logger.info(f"[StreamLLM] model={model}, messages={len(messages)}条")

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
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
                    yield chunk.choices[0].delta.content

            return  # 成功，退出

        except (litellm.exceptions.APIConnectionError, litellm.exceptions.APIError) as e:
            last_error = e
            status_code = getattr(e, 'status_code', None)
            if status_code and status_code < 500:
                raise
            if attempt == max_retries - 1:
                raise
            logger.warning(f"[StreamLLM] 第 {attempt+1}/{max_retries} 次尝试失败: {e}，{2**attempt}s 后重试...")
            await asyncio.sleep(2 ** attempt)

    if last_error:
        raise last_error


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
        from app.service.chat.llm.intent_classifier import classify_intent
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


