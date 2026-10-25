"""
情绪传感器

调用中间场景 LLM，把对话上下文观察为 标签 + 序数等级 + 确定性。
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.db.mysql_client import async_session_local
from app.core.prompts.prompt_manager import PromptManager
from app.core.settings import global_settings
from app.schemas.mood import MoodConfig, MoodObservation, MoodState
from app.service.chat.mood.state_machine import mood_level_word
from app.service.chat.strategy.base_strategy import EmotionInvokeStrategy
from app.service.chat.types import ParsedMemories
from app.service.llm_config_service import get_llm_configs_batch


@dataclass
class MoodSenseResult:
    observation: MoodObservation | None
    latency_ms: int


def _truncate(text: Any, limit: int) -> str:
    value = "" if text is None else str(text)
    value = value.strip()
    return value[:limit] if limit > 0 else value


def _role_label(message: Any) -> str:
    msg_type = getattr(message, "type", "")
    return {"human": "用户", "ai": "角色"}.get(msg_type, "系统")


def _history_text(history_msg: list, cfg: MoodConfig) -> str:
    messages = list(history_msg or [])[-cfg.context_messages:]
    if not messages:
        return "（无）"
    return "\n".join(
        f"{_role_label(msg)}：{_truncate(getattr(msg, 'content', ''), cfg.context_message_chars)}"
        for msg in messages
    )


def _prev_mood_text(prev_mood: MoodState) -> str:
    if prev_mood.label.value == "平静":
        return "平静"
    return f"{prev_mood.label.value}（{mood_level_word(prev_mood.intensity)}）"


def build_sensor_context(
    parsed: ParsedMemories,
    history_msg: list,
    msg_content: str,
    ai_response: str,
    prev_mood: MoodState,
    cfg: MoodConfig,
) -> str:
    role_text = "\n".join(
        part for part in (
            _truncate(parsed.role_declaration, cfg.context_role_chars),
            _truncate(parsed.core_anchor_text, cfg.context_role_chars),
        ) if part
    )
    return "\n".join([
        "【角色设定】",
        role_text or "（无）",
        "【最近对话】",
        _history_text(history_msg, cfg),
        "【当前用户消息】",
        _truncate(msg_content, cfg.context_role_chars) or "（无）",
        "【角色本轮回复】",
        _truncate(ai_response, cfg.context_role_chars) or "（无）",
        "【记忆摘要】",
        _truncate(parsed.memory_bank_summary, cfg.context_event_chars) or "（无）",
        "【上一轮情绪】",
        _prev_mood_text(prev_mood),
    ])


def _level_from_legacy_intensity(raw: Any) -> str | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    logger.warning(f"【情绪传感器】旧格式 intensity={value}，按区间映射为等级")
    if value >= 0.75:
        return "强烈"
    if value >= 0.45:
        return "明显"
    return "轻微"


def _normalize_certainty(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    return "确定" if value in {"确定", "certain", "yes", "true"} else "不确定"


def parse_mood_observation(result_text: str) -> MoodObservation | None:
    if not result_text or not result_text.strip():
        return None

    text = re.sub(r"<(?:think|思索)>.*?</(?:think|思索)>", "", result_text, flags=re.DOTALL | re.IGNORECASE).strip()
    start = text.find("{")
    if start < 0:
        logger.warning(f"【情绪传感器】未找到 JSON: {text[:200]}")
        return None

    try:
        payload, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as e:
        logger.warning(f"【情绪传感器】JSON 解析失败: {e}; raw={text[:200]}")
        return None

    if not isinstance(payload, dict):
        logger.warning(f"【情绪传感器】JSON 不是对象: {text[:200]}")
        return None

    payload = dict(payload)
    if "label" not in payload and "emotion" in payload:
        payload["label"] = payload.pop("emotion")
    if "level" not in payload and "intensity" in payload:
        payload["level"] = _level_from_legacy_intensity(payload.pop("intensity"))
    if "evidence" not in payload and "reason" in payload:
        payload["evidence"] = payload.pop("reason")
    payload["certainty"] = _normalize_certainty(payload.get("certainty"))

    try:
        return MoodObservation.model_validate(payload)
    except Exception as e:
        logger.warning(f"【情绪传感器】观测值非法: {e}; raw={text[:200]}")
        return None


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


async def sense_mood(context: str, llm_id: str | None = None, db=None) -> MoodSenseResult:
    started = time.perf_counter()
    cfg = global_settings.mood

    try:
        prompt_text = await PromptManager.get_prompt("emotion_classifier")
        if not prompt_text:
            logger.warning("【情绪传感器】提示词加载失败")
            return MoodSenseResult(None, _elapsed_ms(started))

        messages = [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": context},
        ]

        if llm_id:
            if db is not None:
                config_map = await get_llm_configs_batch(llm_id, db)
            else:
                async with async_session_local() as session:
                    config_map = await get_llm_configs_batch(llm_id, session)
        else:
            config_map = {}

        strategy = EmotionInvokeStrategy()
        strategy.timeout_seconds = cfg.sensor_timeout_seconds
        result_text = await asyncio.wait_for(
            strategy.invoke(
                messages,
                config_map,
                temperature=cfg.sensor_temperature,
                max_tokens=cfg.sensor_max_tokens,
            ),
            timeout=cfg.sensor_timeout_seconds,
        )

        observation = parse_mood_observation(result_text)
        latency_ms = _elapsed_ms(started)
        if observation is None:
            logger.warning(f"【情绪传感器】未得到有效观测 latency_ms={latency_ms}")
        else:
            logger.debug(
                f"【情绪传感器】obs=({observation.label.value},{observation.level.value},"
                f"{observation.certainty}) latency_ms={latency_ms}"
            )
        return MoodSenseResult(observation, latency_ms)

    except asyncio.TimeoutError:
        latency_ms = _elapsed_ms(started)
        logger.warning(f"【情绪传感器】超时 {cfg.sensor_timeout_seconds}s")
        return MoodSenseResult(None, latency_ms)
    except Exception as e:
        latency_ms = _elapsed_ms(started)
        logger.warning(f"【情绪传感器】调用失败: {e}")
        return MoodSenseResult(None, latency_ms)
