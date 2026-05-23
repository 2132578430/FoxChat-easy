"""
用户画像服务模块

职责：
- 查询用户画像（从 Redis）
- 保存用户画像（到 Redis）
- 构建用户画像更新 Chain
- 基于对话历史更新画像

重构说明：
- 使用策略层替代硬编码的 get_memory_json_model()
- 需要传入 llm_id 和 db 参数以查询用户配置
"""

import asyncio
import json
from typing import Dict, List, Optional

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core.db.redis_client import redis_client
from app.service.chat.strategy.base_strategy import MemoryJSONInvokeStrategy
from app.core.prompts.prompt_manager import PromptManager
from app.exception.BusinessException import BusinessException
from app.common.constant.MsgStatusConstant import MsgStatusConstant
from app.util.template_util import escape_template

CHAIN_CACHE: Dict[str, any] = {}

PROFILE_REQUIRED_DIMENSIONS = ["核心身份", "核心性格", "语言风格", "互动模式", "价值观", "长期兴趣", "绝对边界"]


async def _get_user_profile(user_id: str, llm_id: str) -> Optional[Dict]:
    """从 Redis 获取用户画像"""
    profile_key = build_memory_key(LLMChatConstant.USER_PROFILE, user_id, llm_id)
    profile_json = redis_client.get(profile_key)

    if not profile_json:
        logger.debug(f"user_profile 不存在: user_id={user_id}, llm_id={llm_id}")
        return None

    try:
        profile = json.loads(profile_json)
        logger.debug(f"成功获取 user_profile: user_id={user_id}")
        return profile
    except json.JSONDecodeError as e:
        logger.error(f"user_profile JSON 解析失败: {e}, user_id={user_id}")
        return None


async def _save_user_profile(profile: Dict, user_id: str, llm_id: str) -> bool:
    """将用户画像保存到 Redis"""
    try:
        profile_key = build_memory_key(LLMChatConstant.USER_PROFILE, user_id, llm_id)
        redis_client.set(profile_key, json.dumps(profile, ensure_ascii=False))
        logger.info(f"user_profile 更新成功: user_id={user_id}, llm_id={llm_id}")
        return True
    except Exception as e:
        logger.error(f"user_profile 保存失败: {e}, user_id={user_id}")
        return False


async def _build_profile_updater_chain(llm_id: str = None, db = None):
    """
    构建用户画像更新 Chain（使用策略层）

    Args:
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        (template, strategy) 供直接调用
    """
    from langchain_core.prompts import ChatPromptTemplate

    prompt_template = await PromptManager.get_prompt("user_profile_updater")
    prompt_template = escape_template(prompt_template, ["current_profile", "chat_history"])

    if not prompt_template:
        raise BusinessException(MsgStatusConstant.RAG_MESSAGE_EXAM_ERROR)

    template = ChatPromptTemplate([("system", prompt_template)])

    # 使用 Memory JSON 策略
    strategy = MemoryJSONInvokeStrategy()

    return template, strategy


def _validate_profile_structure(profile: Dict) -> bool:
    """验证用户画像结构完整性"""
    missing_dims = [d for d in PROFILE_REQUIRED_DIMENSIONS if d not in profile]
    if missing_dims:
        logger.warning(f"user_profile 缺少维度: {missing_dims}")
        return False
    return True


async def _update_user_profile(current_profile: Dict, recent_msg_list: List[str], llm_id: str = None, db = None) -> Optional[Dict]:
    """
    调用 LLM 更新用户画像（使用策略层）

    Args:
        current_profile: 当前画像
        recent_msg_list: 对话历史
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        更新后的画像或 None
    """
    if not recent_msg_list:
        logger.debug("对话历史为空，跳过 user_profile 更新")
        return current_profile

    try:
        template, strategy = await _build_profile_updater_chain(llm_id, db)

        # 构建 messages
        prompt_text = await PromptManager.get_prompt("user_profile_updater")
        prompt_text = escape_template(prompt_text, ["current_profile", "chat_history"])

        messages = [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": f"Current profile: {json.dumps(current_profile, ensure_ascii=False)}\nChat history: {json.dumps(recent_msg_list, ensure_ascii=False)}"}
        ]

        # 获取配置
        from app.service.llm_config_service import get_llm_configs_batch
        config_map = {}
        if llm_id and db:
            config_map = await get_llm_configs_batch(llm_id, db)

        result = await strategy.invoke(messages, config_map)

        updated_profile = json.loads(result.content)

        if not _validate_profile_structure(updated_profile):
            logger.warning("user_profile 更新后的结构不完整，保留原数据")
            return current_profile

        logger.info("user_profile 已更新")
        return updated_profile

    except json.JSONDecodeError as e:
        logger.error(f"user_profile 更新失败: JSON 解析错误 - {e}")
        return current_profile
    except Exception as e:
        logger.error(f"user_profile 更新失败: {e}")
        return current_profile


async def update_user_profile_in_summary(user_id: str, llm_id: str, recent_msg_list: List[str], db = None) -> None:
    """
    在消息总结流程中更新用户画像（使用策略层）

    Args:
        user_id: 用户 ID
        llm_id: AI 朋友 ID
        recent_msg_list: 对话历史
        db: 数据库会话

    流程：
    1. 并行获取当前画像
    2. 调用 LLM 分析对话，更新画像
    3. 验证结构完整性
    4. 保存到 Redis
    """
    if not recent_msg_list:
        logger.debug(f"最近消息列表为空，跳过 user_profile 更新: user_id={user_id}")
        return

    try:
        current_profile, _ = await asyncio.gather(
            _get_user_profile(user_id, llm_id),
            _build_profile_updater_chain(llm_id, db),
        )

        if not current_profile:
            logger.info(f"当前 user_profile 不存在，无法更新: user_id={user_id}")
            return

        logger.debug(f"开始更新 user_profile: user_id={user_id}")

        # 使用策略层更新
        updated_profile = await _update_user_profile(current_profile, recent_msg_list, llm_id, db)

        if not _validate_profile_structure(updated_profile):
            logger.warning("user_profile 更新后的结构不完整，保留原数据")
            return

        success = await _save_user_profile(updated_profile, user_id, llm_id)
        if success:
            logger.info(f"user_profile 更新成功: user_id={user_id}")
        else:
            logger.error(f"user_profile 保存失败: user_id={user_id}")

    except Exception as e:
        logger.error(f"user_profile 更新过程中发生错误: {str(e)[:200]}")
        logger.debug(f"user_id={user_id}, 异常类型: {type(e).__name__}")
