"""
记忆上传服务

职责：
- 处理用户初始记忆上传
- 并发生成多层记忆结构：
  - 角色核心锚点
  - 用户画像
  - 角色卡
  - 初始记忆（统一提取器）

重构说明：
- 使用策略层替代 LLM_MAP 编码模型
- 支持用户自定义模型配置（通过 llm_id）
"""

import asyncio
import hashlib
import json
from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core import redis_client
from app.core.db.mysql_client import async_session_local
from app.service.chat.strategy.base_strategy import ExtractionInvokeStrategy, MemoryInvokeStrategy
from app.core.prompts.prompt_manager import PromptManager
from app.service.llm_config_service import get_llm_configs_batch
from app.service.chat.common import safe_json_parse
from app.util import chroma_util
from app.util.template_util import escape_template, try_parse_json


async def _call_llm(
    prompt_template: str,
    variables: dict,
    llm_id: str,
    db,
    use_json: bool = False,
) -> str:
    """
    调用模型（使用策略层）

    Args:
        prompt_template: 提示词模板文件名（不含.md后缀）
        variables: 模板变量字典，如 {"input_content": "用户输入内容"}
        llm_id: AI 朋友 ID（用于查询用户配置）
        db: 数据库会话
        use_json: 是否使用 JSON 模式

    Returns:
        模型返回的字符串结果
    """
    prompt_str = await PromptManager.get_prompt(prompt_template)
    prompt_str = escape_template(prompt_str, list(variables.keys()))

    # 构建 messages
    messages = [
        {"role": "system", "content": prompt_str},
        {"role": "user", "content": variables.get("input_content", "")}
    ]

    # 获取用户配置（如果没有传入 db，则自动创建 session）
    if llm_id:
        if db:
            config_map = await get_llm_configs_batch(llm_id, db)
        else:
            async with async_session_local() as session:
                config_map = await get_llm_configs_batch(llm_id, session)
    else:
        config_map = {}

    # 选择策略
    strategy = ExtractionInvokeStrategy() if use_json else MemoryInvokeStrategy()

    return await strategy.invoke(messages, config_map)


async def _extract_core_anchor(experience: str, llm_id: str, db) -> str:
    """
    生成角色核心（使用策略层）
    """
    return await _call_llm("role_memory_core.md", {"input_content": experience}, llm_id, db, use_json=False)


async def _generate_user_profile(experience: str, llm_id: str, db) -> dict:
    """
    生成用户画像（使用策略层）
    """
    result = await _call_llm("user_profile.md", {"input_content": experience}, llm_id, db, use_json=True)
    parsed = try_parse_json(result)
    if parsed is None:
        logger.error(f"用户画像 JSON 解析失败，原始输出: {result}")
        return {}
    return parsed


async def _extract_initial_memories(experience: str, llm_id: str, db) -> list:
    """
    提取初始记忆（事件+状态统一提取）

    调用统一提取器 memory_event_extractor.md
    """
    from datetime import datetime

    result = await _call_llm("memory_event_extractor.md", {"input_content": experience}, llm_id, db, use_json=True)
    parsed = try_parse_json(result)
    if parsed is None:
        logger.error(f"初始记忆 JSON 解析失败，原始输出: {result}")
        return []
    events = parsed if isinstance(parsed, list) else []
    # 覆盖 LLM 生成的 event_id，防止与后续总结提取的事件 ID 碰撞
    ts = datetime.now().strftime("%H%M%S%f")
    for i, event in enumerate(events):
        content_hash = hashlib.md5(event.get("content", "").encode()).hexdigest()[:12]
        event["event_id"] = f"evt_{ts}_{i}_{content_hash}"
    return events


async def _generate_character_card(experience: str, llm_id: str, db) -> dict:
    """
    生成角色卡（基于 SillyTavern 结构）
    """
    result = await _call_llm("character_card.md", {"input_content": experience}, llm_id, db, use_json=True)
    parsed = try_parse_json(result)
    if parsed is None:
        logger.error(f"角色卡 JSON 解析失败，原始输出: {result}")
        return {}
    return parsed


async def _process_memory_task(
    task_name: str,
    extractor_func,
    constant_key,
    user_id: str,
    llm_id: str,
    experience: str,
    serialize_json: bool = False,
    write_to_chroma: bool = False,
):
    """
    并发处理单个记忆任务

    Args:
        write_to_chroma: 是否写入 Chroma（用于初始记忆）
    """
    try:
        result = await extractor_func(experience, llm_id, None)

        # 写入 Redis（如果指定了 constant_key）
        if constant_key:
            redis_key = build_memory_key(constant_key, user_id, llm_id)
            redis_client.set(redis_key, json.dumps(result, ensure_ascii=False) if serialize_json else result)

        # 写入 Chroma（用于初始记忆，批量上传优化）
        if write_to_chroma and isinstance(result, list) and result:
            count = await chroma_util.upload_history_events_batch(result, user_id, llm_id)
            logger.info(f"{task_name}已写入 Chroma: {count} 条")

        logger.info(f"{task_name}已生成")
        return result
    except Exception as e:
        logger.error(f"{task_name}生成失败: {e}")
        default = {} if serialize_json else ""
        return default


async def chat_init(body: str):
    """
    模型经历上传 - 多层记忆架构（并发处理）

    Args:
        body: 请求体 JSON 字符串
    """
    msg_json = safe_json_parse(body)
    if not msg_json:
        logger.warning("初始记忆JSON解析失败")
        return

    data_json = msg_json.get("data")
    user_id = data_json.get("userId")
    experience = data_json.get("experience")
    llm_id = data_json.get("llmId")

    if data_json is None or user_id is None or experience is None or llm_id is None:
        logger.error("接收初始记忆有误")
        raise ValueError("接收初始记忆有误")

    core_anchor_key = build_memory_key(LLMChatConstant.CORE_ANCHOR, user_id, llm_id)
    existing_core_anchor = redis_client.get(core_anchor_key)
    if existing_core_anchor:
        logger.info(f"用户 {user_id} 的角色核心锚点已存在（llmId={llm_id}），跳过重复初始化")
        # 确保 is_apply 为 2（可能上次初始化完成后没更新成功）
        try:
            from sqlalchemy import text
            async with async_session_local() as session:
                result = await session.execute(
                    text("SELECT is_apply FROM llm_user WHERE id = :llm_id"),
                    {"llm_id": llm_id}
                )
                row = result.fetchone()
                if row and row[0] != 2:
                    await session.execute(
                        text("UPDATE llm_user SET is_apply = 2 WHERE id = :llm_id"),
                        {"llm_id": llm_id}
                    )
                    await session.commit()
                    logger.info(f"【激活完成-补偿】llmId={llm_id}, is_apply已更新为2")
        except Exception as e:
            logger.error(f"【激活完成-补偿】llmId={llm_id}, 更新is_apply失败: {e}", exc_info=True)
        return

    logger.info(f"开始处理用户 {user_id} 的初始记忆...")

    raw_key = build_memory_key(LLMChatConstant.RAW_EXPERIENCE, user_id, llm_id)
    redis_client.set(raw_key, experience)

    await asyncio.gather(
        _process_memory_task("角色核心锚点", _extract_core_anchor, LLMChatConstant.CORE_ANCHOR, user_id, llm_id, experience),
        _process_memory_task("用户画像", _generate_user_profile, LLMChatConstant.USER_PROFILE, user_id, llm_id, experience, serialize_json=True),
        _process_memory_task("角色卡", _generate_character_card, LLMChatConstant.CHARACTER_CARD, user_id, llm_id, experience, serialize_json=True),
        _process_memory_task("初始记忆", _extract_initial_memories, LLMChatConstant.MEMORY_BANK, user_id, llm_id, experience, serialize_json=True, write_to_chroma=True),
    )

    # 更新 MySQL：标记创造物已启用（is_apply = 2）
    try:
        from sqlalchemy import text
        async with async_session_local() as session:
            await session.execute(
                text("UPDATE llm_user SET is_apply = 2 WHERE id = :llm_id"),
                {"llm_id": llm_id}
            )
            await session.commit()
        logger.info(f"【激活完成】llmId={llm_id}, is_apply已更新为2")
    except Exception as e:
        logger.error(f"【激活完成】llmId={llm_id}, 更新is_apply失败: {e}", exc_info=True)

    logger.info(f"用户 {user_id} 的初始记忆处理完成")