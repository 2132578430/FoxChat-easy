"""
记忆解析服务

职责：
- 解析角色卡、核心锚点、用户画像、记忆银行
- 构建静态锚点块
- 解析当前状态容器
"""

import json
import re
from datetime import datetime
from typing import List, Optional, Tuple

from loguru import logger

from app.service.chat.common import safe_json_parse, map_emotion_to_cn


def parse_character_card(json_str: str) -> Tuple[str, str]:
    """
    解析角色卡，返回 (示例对话, 详细描述)

    Args:
        json_str: 角色卡 JSON 字符串

    Returns:
        (examples, detail): 示例对话和详细描述
    """
    if not json_str:
        return "", ""

    card = safe_json_parse(json_str, default={})
    if not card:
        logger.warning("角色卡JSON解析失败")
        return "", ""

    examples = card.get("示例对话", "")

    parts = []
    if card.get("性格关键词"):
        parts.append(f"性格关键词：{card['性格关键词']}")
    if card.get("动作风格"):
        parts.append(f"动作风格：{card['动作风格']}")
    if card.get("常用动作"):
        parts.append(f"常用动作：{', '.join(card['常用动作'])}")
    if card.get("核心描述"):
        parts.append(f"核心描述：{card['核心描述']}")

    return examples, "\n".join(parts) if parts else ""


def parse_core_anchor(text: str) -> Tuple[str, str]:
    """
    解析核心锚点，返回 (角色声明, 核心锚点文本)

    Args:
        text: 核心锚点文本

    Returns:
        (role_declaration, core_anchor_text): 角色声明和核心锚点
    """
    if not text:
        return "", ""

    role_declaration = ""
    core_anchor_text = ""

    role_match = re.search(r'【角色声明】\s*(.+?)(?=【角色核心锚点】|$)', text, re.DOTALL)
    if role_match:
        role_declaration = role_match.group(1).strip()

    anchor_match = re.search(r'【角色核心锚点】\s*(.+?)(?=【绝对边界】|$)', text, re.DOTALL)
    if anchor_match:
        core_anchor_text = anchor_match.group(1).strip()

    return role_declaration, core_anchor_text


def build_static_anchors(
    soul: str,
    role_declaration: str,
    core_anchor: str,
    character_card: str,
    character_card_detail: str,
    mes_example: str,
) -> str:
    """
    构建 A1 静态锚点块

    按顺序拼接各子部分，非空部分带子标题，空部分跳过。

    Args:
        soul: 角色灵魂内容
        role_declaration: 角色声明内容
        core_anchor: 角色核心锚点内容
        character_card: 角色详细卡内容
        character_card_detail: 角色特征补充内容
        mes_example: 示例对话风格内容

    Returns:
        拼接后的静态锚点字符串
    """
    sections = [
        ("【角色灵魂（Soul）】", soul),
        ("【角色声明】", role_declaration),
        ("【角色核心锚点】", core_anchor),
        ("【角色详细卡】", character_card),
        ("【角色特征补充】", character_card_detail),
        ("【示例对话风格】", mes_example),
    ]

    parts = []
    for header, content in sections:
        if content and content.strip():
            parts.append(f"{header}\n{content.strip()}")

    return "\n\n".join(parts) if parts else ""


def _is_placeholder(value) -> bool:
    """判断值是否为占位符"""
    if not value:
        return True
    if isinstance(value, str):
        return value == "[未提及]"
    if isinstance(value, list):
        return all(_is_placeholder(item) for item in value)
    if isinstance(value, dict):
        return all(_is_placeholder(item) for item in value.values())
    return False


def _format_value(value) -> str:
    """格式化值为字符串"""
    if isinstance(value, list):
        return "、".join(str(item) for item in value if not _is_placeholder(item))
    return str(value)


def parse_user_profile(json_str: str) -> str:
    """
    解析用户画像

    Args:
        json_str: 用户画像 JSON 字符串

    Returns:
        格式化后的用户画像文本
    """
    if not json_str:
        return ""

    profile = safe_json_parse(json_str, default={})
    if not profile:
        logger.warning("user_profile JSON解析失败")
        return ""

    parts = []
    for dim_key, dim_val in profile.items():
        if isinstance(dim_val, dict):
            items = [
                f"{k}：{_format_value(v)}"
                for k, v in dim_val.items()
                if not _is_placeholder(v)
            ]
            if items:
                parts.append(f"{dim_key}：{', '.join(items)}")
        elif isinstance(dim_val, list):
            filtered = [_format_value(v) for v in dim_val if not _is_placeholder(v)]
            if filtered:
                parts.append(f"{dim_key}：{', '.join(filtered)}")
        elif not _is_placeholder(dim_val):
            parts.append(f"{dim_key}：{dim_val}")

    return "\n".join(parts) if parts else ""


def parse_memory_bank(json_str: str) -> str:
    """
    解析 Memory Bank，只取最近5条作为保底

    Args:
        json_str: Memory Bank JSON 字符串

    Returns:
        格式化后的记忆银行文本
    """
    if not json_str:
        return ""

    bank = safe_json_parse(json_str, default=[])
    if not isinstance(bank, list) or not bank:
        logger.warning("memory_bank JSON解析失败")
        return ""

    recent_items = bank[-5:] if len(bank) > 5 else bank
    logger.info(f"Memory Bank: 共 {len(bank)} 条，注入最近 {len(recent_items)} 条")

    lines = []
    for item in recent_items:
        time_val = item.get("time", "某时")
        content_val = item.get("content", "")
        type_val = item.get("type", "event")
        lines.append(f"- [{time_val}]（{type_val}）{content_val}")
    return "\n".join(lines)


def parse_current_state(json_str: str, current_round: int = 0) -> str:
    """
    解析当前状态容器，生成摘要注入 Prompt

    Args:
        json_str: current_state JSON 字符串
        current_round: 当前全局轮数（用于过期判断）

    Returns:
        结构化摘要文本，控制在 80~150 tokens
    """
    if not json_str:
        return build_default_state_summary()

    try:
        from app.schemas.current_state import CurrentState

        state_dict = safe_json_parse(json_str, default={})
        if not isinstance(state_dict, dict):
            logger.warning(f"current_state JSON 不是 dict")
            return build_default_state_summary()

        state = CurrentState.model_validate(state_dict)

        # 获取有效字段
        valid_fields = state.get_valid_fields_for_injection(current_round)

        if not valid_fields:
            return ""

        # 构建摘要
        lines = []

        # 当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"- 当前时间：{current_time}")

        # 情绪
        if "情绪" in valid_fields:
            lines.append(f"- 情绪：{map_emotion_to_cn(valid_fields['情绪'])}")

        # 未完成事项
        valid_items = [
            item for item in state.unfinished_items
            if item.is_valid_for_injection(current_round)
        ]
        if valid_items:
            today = datetime.now().strftime("%Y-%m-%d")
            for item in valid_items[:2]:
                if item.created_at and item.due_at:
                    created_date = item.created_at[:10] if len(item.created_at) >= 10 else item.created_at
                    due_date = item.due_at[:10] if len(item.due_at) >= 10 else item.due_at
                    lines.append(f"- 未完成：[{created_date}录入] {item.content} [预期{due_date}/今天{today}]")
                else:
                    lines.append(f"- 未完成：{item.content}")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"current_state JSON 解析失败: {e}")
        return build_default_state_summary()


def build_default_state_summary() -> str:
    """构建默认状态摘要（只注入时间）"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"- 当前时间：{current_time}"