"""
记忆上传服务（对账式初始化）

职责：
- 消费模型初始化消息，生成四类初始记忆产物：
  - 角色核心锚点
  - 用户画像
  - 角色卡
  - 初始记忆事件（Redis memory_bank + Chroma）
- 只补齐缺失或非法的产物，合法的产物原样保留
- 由 Python 维护初始化状态：0 未开始 / 1 初始化中 / 2 就绪 / 3 初始化失败
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import text

from app.common.constant import ChromaTypeConstant
from app.common.constant.LLMChatConstant import LLMChatConstant, build_chat_key
from app.core import redis_client
from app.core.db.mysql_client import async_session_local
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.common import safe_json_parse
from app.service.chat.memory.memory_parser import parse_core_anchor
from app.service.chat.profile.user_profile_service import PROFILE_REQUIRED_DIMENSIONS
from app.service.chat.strategy.base_strategy import ExtractionInvokeStrategy, MemoryInvokeStrategy
from app.service.llm_config_service import get_llm_configs_batch, test_llm_connection
from app.util import chroma_util
from app.util.template_util import escape_template, try_parse_json

STATUS_INITIALIZING = 1
STATUS_READY = 2
STATUS_FAILED = 3

INITIAL_MEMORY_SOURCE = "initial"

_ARTIFACT_LABELS = {
    "core_anchor": "角色核心锚点",
    "user_profile": "用户画像",
    "character_card": "角色卡",
    "memory_bank": "初始记忆",
}

_REQUIRED_SCENARIOS = ("chat", "memory", "extraction")
_REQUIRED_MODEL_FIELDS = ("model_name", "model_api_key", "model_base_url")


def _memory_key(user_id: str, llm_id: str, suffix: str) -> str:
    return build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, suffix)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _is_valid_core_anchor(raw: Any) -> bool:
    if not isinstance(raw, str) or not raw.strip():
        return False
    role_declaration, core_anchor = parse_core_anchor(raw)
    return bool(role_declaration and core_anchor)


def _is_valid_user_profile_data(profile: Any) -> bool:
    if not isinstance(profile, dict):
        return False
    return all(_has_value(profile.get(dimension)) for dimension in PROFILE_REQUIRED_DIMENSIONS)


def _is_valid_user_profile(raw: Any) -> bool:
    return _is_valid_user_profile_data(safe_json_parse(raw, default=None, log_warning=False))


def _is_valid_character_card_data(card: Any) -> bool:
    if not isinstance(card, dict):
        return False
    for field in ("名字", "核心描述", "性格关键词", "动作风格", "示例对话"):
        if not _has_value(card.get(field)):
            return False
    if not isinstance(card.get("常用动作"), list) or not card["常用动作"]:
        return False

    behavior_guide = card.get("行为指南")
    if not isinstance(behavior_guide, dict):
        return False
    if not any(
        isinstance(behavior_guide.get(field), list) and behavior_guide[field]
        for field in ("会做的事", "不会做的事", "口头禅")
    ):
        return False

    try:
        talkativeness = float(card.get("健谈程度"))
    except (TypeError, ValueError):
        return False
    return 0.0 <= talkativeness <= 1.0


def _is_valid_character_card(raw: Any) -> bool:
    return _is_valid_character_card_data(safe_json_parse(raw, default=None, log_warning=False))


def _is_valid_memory_bank(raw: Any, chroma_initial_count: int) -> bool:
    if chroma_initial_count <= 0:
        return False
    bank = safe_json_parse(raw, default=None, log_warning=False)
    if not isinstance(bank, list) or not bank:
        return False
    return any(isinstance(item, dict) and _has_value(item.get("content")) for item in bank)


def _normalize_events(parsed: Any) -> list[dict]:
    """展开 {"events": [...]}，并校验事件结构"""
    events = parsed.get("events") if isinstance(parsed, dict) else parsed
    if isinstance(events, str):
        events = try_parse_json(events)
    if not isinstance(events, list):
        raise ValueError("初始记忆输出不是事件数组")

    normalized: list[dict] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"初始记忆第 {index + 1} 条不是对象")
        if not _has_value(event.get("content")):
            raise ValueError(f"初始记忆第 {index + 1} 条缺少 content")
        normalized.append(event)

    if not normalized:
        raise ValueError("初始记忆为空")
    return normalized


def _write_text_artifact(user_id: str, llm_id: str, suffix: str, value: str) -> None:
    redis_client.set(_memory_key(user_id, llm_id, suffix), value)


def _write_json_artifact(user_id: str, llm_id: str, suffix: str, value: Any) -> None:
    redis_client.set(_memory_key(user_id, llm_id, suffix), json.dumps(value, ensure_ascii=False))


async def _call_llm(
    prompt_template: str,
    variables: dict,
    config_map: dict,
    use_json: bool = False,
) -> str:
    prompt_str = await PromptManager.get_prompt(prompt_template)
    prompt_str = escape_template(prompt_str, list(variables.keys()))

    messages = [
        {"role": "system", "content": prompt_str},
        {"role": "user", "content": variables.get("input_content", "")},
    ]

    strategy = ExtractionInvokeStrategy() if use_json else MemoryInvokeStrategy()
    return await strategy.invoke(messages, config_map)


async def _extract_core_anchor(experience: str, config_map: dict) -> str:
    result = await _call_llm("role_memory_core.md", {"input_content": experience}, config_map)
    if not _is_valid_core_anchor(result):
        raise ValueError("角色核心锚点缺少【角色声明】或【角色核心锚点】")
    return result


async def _generate_user_profile(experience: str, config_map: dict) -> dict:
    result = await _call_llm("user_profile.md", {"input_content": experience}, config_map, use_json=True)
    profile = try_parse_json(result)
    if not _is_valid_user_profile_data(profile):
        logger.error(f"用户画像结构不完整，原始输出: {result}")
        raise ValueError("用户画像结构不完整")
    return profile


async def _extract_initial_memories(experience: str, config_map: dict) -> list[dict]:
    result = await _call_llm(
        "memory_event_extractor.md", {"input_content": experience}, config_map, use_json=True
    )
    events = _normalize_events(try_parse_json(result))

    now = datetime.now()
    timestamp = now.strftime("%H%M%S%f")
    today = now.strftime("%Y-%m-%d")
    for index, event in enumerate(events):
        content_hash = hashlib.md5(event["content"].encode()).hexdigest()[:12]
        event["event_id"] = f"evt_{timestamp}_{index}_{content_hash}"
        event["memory_source"] = INITIAL_MEMORY_SOURCE
        event["occurred_at"] = today
        event["last_seen_at"] = today
        event.setdefault("actor", "UNKNOWN")
        event.setdefault("category", "event")
        event.setdefault("type", "event")
    return events


async def _generate_character_card(experience: str, config_map: dict) -> dict:
    result = await _call_llm("character_card.md", {"input_content": experience}, config_map, use_json=True)
    card = try_parse_json(result)
    if not _is_valid_character_card_data(card):
        logger.error(f"角色卡结构不完整，原始输出: {result}")
        raise ValueError("角色卡结构不完整")
    return card


async def _claim_initialization(llm_id: str, user_id: str) -> bool:
    """以原子 CAS 抢占初始化权：只有 0/3/NULL 才能进入初始化"""
    async with async_session_local() as session:
        result = await session.execute(
            text(
                "UPDATE llm_user SET isApply = :status "
                "WHERE id = :llm_id AND user_id = :user_id "
                "AND (isApply IS NULL OR isApply IN (0, 3))"
            ),
            {"status": STATUS_INITIALIZING, "llm_id": llm_id, "user_id": user_id},
        )
        await session.commit()
        return result.rowcount == 1


async def _set_apply_status(llm_id: str, status: int) -> None:
    async with async_session_local() as session:
        result = await session.execute(
            text("UPDATE llm_user SET isApply = :status WHERE id = :llm_id"),
            {"status": status, "llm_id": llm_id},
        )
        await session.commit()
        if result.rowcount != 1:
            raise RuntimeError(f"llm_user 状态更新影响行数为 {result.rowcount}")
    logger.info(f"【初始化状态】llmId={llm_id}, isApply={status}")


async def _safe_set_apply_status(llm_id: str, status: int) -> None:
    try:
        await _set_apply_status(llm_id, status)
    except Exception as e:
        logger.error(f"【初始化状态】llmId={llm_id}, 写入 isApply={status} 失败: {e}")


async def _precheck_llm(llm_id: str) -> dict:
    async with async_session_local() as session:
        config_map = await get_llm_configs_batch(llm_id, session)

    missing = [
        f"{scenario}.{field}"
        for scenario in _REQUIRED_SCENARIOS
        for field in _REQUIRED_MODEL_FIELDS
        if not (config_map.get(scenario) or {}).get(field)
    ]
    if missing:
        raise RuntimeError(f"模型配置不完整: {', '.join(missing)}")

    chat_config = config_map["chat"]
    logger.info(f"【初始化预校验】测试模型连接: model={chat_config.get('model_name')}")
    conn_result = await test_llm_connection(
        model_name=chat_config["model_name"],
        api_key=chat_config["model_api_key"],
        base_url=chat_config["model_base_url"],
    )
    if not conn_result.get("success"):
        raise RuntimeError(f"模型连接测试失败: {conn_result.get('message')}")

    logger.info(f"【初始化预校验通过】llmId={llm_id}")
    return config_map


async def _load_artifact_states(user_id: str, llm_id: str) -> dict[str, bool]:
    chroma_initial_count = await chroma_util.count_history_events(
        user_id, llm_id, memory_source=INITIAL_MEMORY_SOURCE
    )
    states = {
        "core_anchor": _is_valid_core_anchor(
            redis_client.get(_memory_key(user_id, llm_id, LLMChatConstant.CORE_ANCHOR))
        ),
        "user_profile": _is_valid_user_profile(
            redis_client.get(_memory_key(user_id, llm_id, LLMChatConstant.USER_PROFILE))
        ),
        "character_card": _is_valid_character_card(
            redis_client.get(_memory_key(user_id, llm_id, LLMChatConstant.CHARACTER_CARD))
        ),
        "memory_bank": _is_valid_memory_bank(
            redis_client.get(_memory_key(user_id, llm_id, LLMChatConstant.MEMORY_BANK)),
            chroma_initial_count,
        ),
    }
    logger.info(
        f"【初始化对账】llmId={llm_id}, chroma_initial={chroma_initial_count}, states={states}"
    )
    return states


async def _regenerate_core_anchor(
    experience: str, user_id: str, llm_id: str, config_map: dict
) -> None:
    value = await _extract_core_anchor(experience, config_map)
    _write_text_artifact(user_id, llm_id, LLMChatConstant.CORE_ANCHOR, value)
    logger.info(f"【初始化】角色核心锚点已重建: llmId={llm_id}")


async def _regenerate_user_profile(
    experience: str, user_id: str, llm_id: str, config_map: dict
) -> None:
    value = await _generate_user_profile(experience, config_map)
    _write_json_artifact(user_id, llm_id, LLMChatConstant.USER_PROFILE, value)
    logger.info(f"【初始化】用户画像已重建: llmId={llm_id}")


async def _regenerate_character_card(
    experience: str, user_id: str, llm_id: str, config_map: dict
) -> None:
    value = await _generate_character_card(experience, config_map)
    _write_json_artifact(user_id, llm_id, LLMChatConstant.CHARACTER_CARD, value)
    logger.info(f"【初始化】角色卡已重建: llmId={llm_id}")


async def _regenerate_memory_bank(
    experience: str, user_id: str, llm_id: str, config_map: dict
) -> None:
    events = await _extract_initial_memories(experience, config_map)

    await chroma_util.delete(
        ChromaTypeConstant.CHAT,
        user_id=user_id,
        llm_id=llm_id,
        is_event=True,
        memory_source=INITIAL_MEMORY_SOURCE,
    )
    uploaded = await chroma_util.upload_history_events_batch(
        events, user_id, llm_id, memory_source=INITIAL_MEMORY_SOURCE
    )
    if uploaded != len(events):
        raise RuntimeError(f"初始记忆写入数量不一致: {uploaded}/{len(events)}")

    stored_count = await chroma_util.count_history_events(
        user_id, llm_id, memory_source=INITIAL_MEMORY_SOURCE
    )
    if stored_count != len(events):
        raise RuntimeError(f"初始记忆 Chroma 校验失败: {stored_count}/{len(events)}")

    bank = safe_json_parse(
        redis_client.get(_memory_key(user_id, llm_id, LLMChatConstant.MEMORY_BANK)),
        default=[],
        log_warning=False,
    )
    if not isinstance(bank, list):
        bank = []
    bank = [
        item
        for item in bank
        if not (isinstance(item, dict) and item.get("memory_source") == INITIAL_MEMORY_SOURCE)
    ]
    bank.extend(events)
    _write_json_artifact(user_id, llm_id, LLMChatConstant.MEMORY_BANK, bank)
    logger.info(f"【初始化】初始记忆已重建: llmId={llm_id}, count={len(events)}")


_REGENERATORS = {
    "core_anchor": _regenerate_core_anchor,
    "user_profile": _regenerate_user_profile,
    "character_card": _regenerate_character_card,
    "memory_bank": _regenerate_memory_bank,
}


async def _reconcile_artifacts(
    experience: str,
    user_id: str,
    llm_id: str,
    config_map: dict,
    states: dict[str, bool],
) -> None:
    # 从Dict中获取不存在的信息
    pending = [name for name in _REGENERATORS if not states.get(name)]
    if not pending:
        logger.info(f"【初始化对账】四类产物均已存在且合法，跳过生成: llmId={llm_id}")
        return

    labels = [_ARTIFACT_LABELS[name] for name in pending]
    logger.info(f"【初始化对账】待补齐: {labels}, llmId={llm_id}")

    results = await asyncio.gather(
        *(_REGENERATORS[name](experience, user_id, llm_id, config_map) for name in pending),
        return_exceptions=True,
    )
    for name, result in zip(pending, results):
        if isinstance(result, BaseException):
            logger.error(f"【初始化】{_ARTIFACT_LABELS[name]}生成失败: {result}")


async def chat_init(body: str | bytes):
    """
    模型初始记忆上传（对账式）

    Args:
        body: MQ 消息体，形如 {"data": {"userId": ..., "llmId": ..., "experience": ...}}
    """
    msg_json = safe_json_parse(body)
    if not isinstance(msg_json, dict):
        raise ValueError("初始记忆消息不是 JSON 对象")

    data_json = msg_json.get("data")
    if not isinstance(data_json, dict):
        raise ValueError("初始记忆消息缺少 data")

    user_id = data_json.get("userId")
    llm_id = data_json.get("llmId")
    experience = data_json.get("experience")
    if not all(isinstance(value, str) and value.strip() for value in (user_id, llm_id, experience)):
        raise ValueError("初始记忆消息缺少 userId/llmId/experience")

    claimed = await _claim_initialization(llm_id, user_id)
    if not claimed:
        logger.info(
            f"【初始化跳过】llmId={llm_id}, 当前状态不是 0/3，跳过重复初始化"
        )
        return

    logger.info(f"【初始化开始】userId={user_id}, llmId={llm_id}")
    ready = False
    try:
        # 确认聊天、记忆、抽取等用途的模型配置齐全，并测试聊天模型能否连接。失败会抛出异常，后续初始化不会继续
        config_map = await _precheck_llm(llm_id)
        # 把传入的 experience 保存起来
        _write_text_artifact(user_id, llm_id, LLMChatConstant.RAW_EXPERIENCE, experience)

        # 加载角色卡等信息，将含有数据的信息返回来
        states = await _load_artifact_states(user_id, llm_id)
        # 生成角色卡等信息，已含有的信息跳过
        await _reconcile_artifacts(experience, user_id, llm_id, config_map, states)

        states = await _load_artifact_states(user_id, llm_id)
        invalid = [_ARTIFACT_LABELS[name] for name, valid in states.items() if not valid]
        if invalid:
            raise RuntimeError(f"初始化产物校验失败: {', '.join(invalid)}")

        await _set_apply_status(llm_id, STATUS_READY)
        ready = True
        logger.info(f"【初始化完成】userId={user_id}, llmId={llm_id}")
    finally:
        if not ready:
            await _safe_set_apply_status(llm_id, STATUS_FAILED)
