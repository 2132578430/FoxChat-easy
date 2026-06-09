"""
统一 Prompt Payload 构建器

阶段6收敛：在 LLM 调用前一次性决定：
- 哪些块注入
- 注入顺序
- 空块是否省略

职责：
- 接收各层原始内容
- 执行空块抑制
- 输出最终 payload 字典

使用方式：
    from app.service.chat.llm.prompt_payload_builder import build_prompt_payload

    payload = build_prompt_payload(
        static_anchors=...,
        user_profile_summary=...,
        historical_context=...,
        current_state=...,
        behavior_guide=...,
        talkativeness_guidance=...,
    )
"""

from dataclasses import dataclass
from typing import List
from loguru import logger


@dataclass
class PromptPayload:
    """最终 Prompt Payload 结构"""
    static_anchors: str
    user_profile_summary: str
    historical_context: str
    current_state: str
    behavior_guide: str
    talkativeness_guidance: str

    # 元信息（调试用）
    blocks_injected: List[str]  # 实际注入的块名
    blocks_omitted: List[str]   # 空块省略的块名


def _is_empty_block(content: str) -> bool:
    """判断块内容是否为空（应省略）"""
    if not content:
        return True
    stripped = content.strip()
    if not stripped:
        return True
    if stripped in ("", "无", "暂无", "未提及"):
        return True
    return False


def build_prompt_payload(
    static_anchors: str,
    user_profile_summary: str,
    historical_context: str,
    current_state: str,
    behavior_guide: str,
    talkativeness_guidance: str,
) -> PromptPayload:
    """
    构建最终 Prompt Payload

    Args:
        static_anchors: A1 静态锚点内容
        user_profile_summary: A2 用户画像+硬边界内容
        historical_context: C 历史上下文内容
        current_state: B 当前状态内容
        behavior_guide: 行为指南内容
        talkativeness_guidance: 健谈程度指导

    Returns:
        PromptPayload 对象
    """
    blocks_injected = []
    blocks_omitted = []

    # 空块抑制
    final_static_anchors = static_anchors
    if _is_empty_block(static_anchors):
        final_static_anchors = ""
        blocks_omitted.append("static_anchors")
        logger.debug("【空块抑制】A1 静态锚点 为空，已省略")
    else:
        blocks_injected.append("static_anchors")

    final_user_profile = user_profile_summary
    if _is_empty_block(user_profile_summary):
        final_user_profile = ""
        blocks_omitted.append("user_profile_summary")
        logger.debug("【空块抑制】A2 用户画像+硬边界 为空，已省略")
    else:
        blocks_injected.append("user_profile_summary")

    final_historical_context = historical_context
    if _is_empty_block(historical_context):
        final_historical_context = ""
        blocks_omitted.append("historical_context")
        logger.debug("【空块抑制】C 历史上下文 为空，已省略")
    else:
        blocks_injected.append("historical_context")

    final_current_state = current_state
    if _is_empty_block(current_state):
        final_current_state = ""
        blocks_omitted.append("current_state")
        logger.debug("【空块抑制】B 当前状态 为空，已省略")
    else:
        blocks_injected.append("current_state")

    final_behavior_guide = behavior_guide
    if _is_empty_block(behavior_guide):
        final_behavior_guide = ""
        blocks_omitted.append("behavior_guide")
        logger.debug("【空块抑制】行为指南 为空，已省略")
    else:
        blocks_injected.append("behavior_guide")

    final_talkativeness_guidance = talkativeness_guidance
    if _is_empty_block(talkativeness_guidance):
        final_talkativeness_guidance = ""
        blocks_omitted.append("talkativeness_guidance")
        logger.debug("【空块抑制】健谈程度指导 为空，已省略")
    else:
        blocks_injected.append("talkativeness_guidance")

    payload = PromptPayload(
        static_anchors=final_static_anchors,
        user_profile_summary=final_user_profile,
        historical_context=final_historical_context,
        current_state=final_current_state,
        behavior_guide=final_behavior_guide,
        talkativeness_guidance=final_talkativeness_guidance,
        blocks_injected=blocks_injected,
        blocks_omitted=blocks_omitted,
    )

    logger.debug(f"【Payload构建】注入块: {blocks_injected}, 空块省略: {blocks_omitted}")

    return payload
