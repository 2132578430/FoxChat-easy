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

import json
from typing import Dict, List, Optional

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_chat_key
from app.core.db.redis_client import redis_client
from app.core.db.mysql_client import async_session_local
from app.service.chat.strategy.base_strategy import MemoryJSONInvokeStrategy
from app.core.prompts.prompt_manager import PromptManager
from app.util.template_util import escape_template


PROFILE_REQUIRED_DIMENSIONS = ["核心身份", "核心性格", "语言风格", "互动模式", "价值观", "长期兴趣", "绝对边界"]


async def _get_user_profile(user_id: str, llm_id: str) -> Optional[Dict]:
    """从 Redis 获取用户画像"""
    profile_key = build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.USER_PROFILE)
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


async def _get_llm_config(llm_id: str, db=None) -> dict:
    """获取 LLM 配置（提取重复的 config_map 获取逻辑）"""
    from app.service.llm_config_service import get_llm_configs_batch
    if not llm_id:
        return {}
    if db:
        return await get_llm_configs_batch(llm_id, db)
    async with async_session_local() as session:
        return await get_llm_configs_batch(llm_id, session)


async def _invoke_with_prompt(
    prompt_name: str,
    variables: list[str],
    user_content: str,
    strategy,
    config_map: dict,
) -> str:
    """
    统一的 prompt 获取 → escape → 拼 messages → invoke

    Args:
        prompt_name: Prompt 文件名称
        variables: 需要转义的变量列表
        user_content: Human 消息内容
        strategy: LLMInvokeStrategy 实例
        config_map: LLM 配置字典

    Returns:
        LLM 响应文本
    """
    prompt_text = await PromptManager.get_prompt(prompt_name)
    prompt_text = escape_template(prompt_text, variables)
    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": user_content},
    ]
    return await strategy.invoke(messages, config_map)


async def _save_user_profile(profile: Dict, user_id: str, llm_id: str) -> bool:
    """将用户画像保存到 Redis"""
    try:
        profile_key = build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.USER_PROFILE)
        redis_client.set(profile_key, json.dumps(profile, ensure_ascii=False))
        logger.info(f"user_profile 更新成功: user_id={user_id}, llm_id={llm_id}")
        return True
    except Exception as e:
        logger.error(f"user_profile 保存失败: {e}, user_id={user_id}")
        return False


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
        strategy = MemoryJSONInvokeStrategy()
        config_map = await _get_llm_config(llm_id, db)
        result = await _invoke_with_prompt(
            "user_profile_updater",
            ["current_profile", "chat_history"],
            f"Current profile: {json.dumps(current_profile, ensure_ascii=False)}\nChat history: {json.dumps(recent_msg_list, ensure_ascii=False)}",
            strategy,
            config_map,
        )

        updated_profile = json.loads(result)

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
    1. 获取当前画像
    2. 调用 LLM 更新画像（内部已有结构校验）
    3. 保存到 Redis
    """
    if not recent_msg_list:
        logger.debug(f"最近消息列表为空，跳过 user_profile 更新: user_id={user_id}")
        return

    try:
        current_profile = await _get_user_profile(user_id, llm_id)

        if not current_profile:
            logger.info(f"当前 user_profile 不存在，无法更新: user_id={user_id}")
            return

        logger.debug(f"开始更新 user_profile: user_id={user_id}")

        # 使用策略层更新（内部已做结构校验）
        updated_profile = await _update_user_profile(current_profile, recent_msg_list, llm_id, db)

        success = await _save_user_profile(updated_profile, user_id, llm_id)
        if success:
            logger.info(f"user_profile 更新成功: user_id={user_id}")
        else:
            logger.error(f"user_profile 保存失败: user_id={user_id}")

    except Exception as e:
        logger.error(f"user_profile 更新过程中发生错误: {str(e)[:200]}")
        logger.debug(f"user_id={user_id}, 异常类型: {type(e).__name__}")
