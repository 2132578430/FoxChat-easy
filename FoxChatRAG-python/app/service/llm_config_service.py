"""
LLM 配置服务模块

职责:
- 批量查询 LLM 配置 (5 个场景一次性查询)
- 保存/更新/删除配置
- 配置完整性验证
- 测试连接验证
"""

import json
from typing import Dict, List
from loguru import logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_config import LlmConfig


async def test_llm_connection(
    model_name: str,
    api_key: str,
    base_url: str
) -> Dict[str, any]:
    """
    测试 LLM 连接 (使用 LiteLLM 进行最小化调用)

    Args:
        model_name: 模型名称 (e.g., 'gpt-4o', 'deepseek/deepseek-chat')
        api_key: API 密钥
        base_url: 服务地址

    Returns:
        测试结果: {'success': True/False, 'message': str}
    """
    try:
        import litellm

        logger.info(f"【测试连接】model={model_name}, base_url={base_url}")

        # 自动添加 openai 前缀（用于 OpenAI 兼容的 API）
        if "/" not in model_name:
            actual_model = f"openai/{model_name}"
        else:
            actual_model = model_name

        # 发送最小化测试请求 (1 token prompt)
        response = await litellm.acompletion(
            model=actual_model,
            messages=[{"role": "user", "content": "test"}],
            api_key=api_key,
            base_url=base_url,
            max_tokens=1,
        )

        logger.info(f"【测试连接】成功: model={model_name}")
        return {"success": True, "message": "连接成功"}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"【测试连接】失败: {error_msg}")

        # 根据异常类型返回特定错误消息
        if "AuthenticationError" in error_msg or "401" in error_msg:
            return {"success": False, "message": "认证失败：无效的 API Key"}
        elif "ModelNotFoundError" in error_msg or "model" in error_msg.lower():
            return {"success": False, "message": "模型不存在"}
        elif "TimeoutError" in error_msg or "timeout" in error_msg.lower():
            return {"success": False, "message": "连接超时，请检查网络或 Base URL"}
        elif "RateLimitError" in error_msg or "429" in error_msg:
            return {"success": False, "message": "API 配额已用尽"}
        else:
            return {"success": False, "message": f"连接失败: {error_msg}"}


async def get_llm_configs_batch(llm_id: str, db: AsyncSession) -> Dict[str, dict]:
    """
    批量查询 LLM 配置 (一次查询返回 5 个场景配置)

    Args:
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        配置字典: {'chat': {...}, 'memory': {...}, 'summary': {...}, 'extraction': {...}, 'emotion': {...}}
    """
    query = select(LlmConfig).where(LlmConfig.llm_id == llm_id)
    result = await db.execute(query)
    configs = result.scalars().all()

    config_map = {}
    for config in configs:
        scenario = config.scenario
        config_map[scenario] = {
            "id": config.id,
            "llm_id": config.llm_id,
            "scenario": config.scenario,
            "model_name": config.model_name,
            "model_api_key": config.model_api_key,
            "model_base_url": config.model_base_url,
            "model_temperature": float(config.model_temperature) if config.model_temperature else None,
            "model_max_tokens": config.model_max_tokens,
            "model_response_format": config.model_response_format,
            "is_default": config.is_default,
        }

    logger.info(f"【批量查询】llm_id={llm_id}, 返回 {len(config_map)} 个配置")
    return config_map


async def save_llm_config(
    llm_id: str,
    scenario: str,
    config_data: dict,
    db: AsyncSession
) -> str:
    """
    保存或更新 LLM 配置

    Args:
        llm_id: AI 朋友 ID
        scenario: 场景名称
        config_data: 配置数据
        db: 数据库会话

    Returns:
        配置 ID
    """
    # 检查是否已存在配置
    query = select(LlmConfig).where(
        LlmConfig.llm_id == llm_id,
        LlmConfig.scenario == scenario
    )
    result = await db.execute(query)
    existing_config = result.scalar_one_or_none()

    if existing_config:
        # 更新现有配置
        existing_config.model_name = config_data["model_name"]
        existing_config.model_api_key = config_data["model_api_key"]
        existing_config.model_base_url = config_data["model_base_url"]
        existing_config.model_temperature = config_data.get("model_temperature")
        existing_config.model_max_tokens = config_data.get("model_max_tokens")
        existing_config.model_response_format = config_data.get("model_response_format")

        await db.commit()
        logger.info(f"【更新配置】llm_id={llm_id}, scenario={scenario}")
        return existing_config.id
    else:
        # 创建新配置
        import uuid
        config_id = str(uuid.uuid4())

        new_config = LlmConfig(
            id=config_id,
            llm_id=llm_id,
            scenario=scenario,
            model_name=config_data["model_name"],
            model_api_key=config_data["model_api_key"],
            model_base_url=config_data["model_base_url"],
            model_temperature=config_data.get("model_temperature"),
            model_max_tokens=config_data.get("model_max_tokens"),
            model_response_format=config_data.get("model_response_format"),
            is_default=False,
        )

        db.add(new_config)
        await db.commit()
        logger.info(f"【创建配置】llm_id={llm_id}, scenario={scenario}, id={config_id}")
        return config_id


async def save_llm_configs_batch(
    llm_id: str,
    configs: List[dict],
    db: AsyncSession
) -> Dict[str, str]:
    """
    批量保存 5 个场景配置

    Args:
        llm_id: AI 朋友 ID
        configs: 配置列表 (每个包含 scenario 字段)
        db: 数据库会话

    Returns:
        配置 ID 字典: {'chat': 'id1', 'memory': 'id2', ...}
    """
    config_ids = {}
    for config in configs:
        scenario = config["scenario"]
        config_id = await save_llm_config(llm_id, scenario, config, db)
        config_ids[scenario] = config_id

    logger.info(f"【批量保存】llm_id={llm_id}, 保存 {len(config_ids)} 个配置")
    return config_ids


async def delete_llm_config(llm_id: str, scenario: str, db: AsyncSession) -> bool:
    """
    删除 LLM 配置

    Args:
        llm_id: AI 朋友 ID
        scenario: 场景名称
        db: 数据库会话

    Returns:
        是否成功删除
    """
    query = select(LlmConfig).where(
        LlmConfig.llm_id == llm_id,
        LlmConfig.scenario == scenario
    )
    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if config:
        await db.delete(config)
        await db.commit()
        logger.info(f"【删除配置】llm_id={llm_id}, scenario={scenario}")
        return True
    else:
        logger.warning(f"【删除配置】配置不存在: llm_id={llm_id}, scenario={scenario}")
        return False


async def validate_config_count(llm_id: str, db: AsyncSession) -> bool:
    """
    验证配置数量是否为 5 (所有场景都已配置)

    Args:
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        配置数量是否为 5
    """
    query = select(LlmConfig).where(LlmConfig.llm_id == llm_id)
    result = await db.execute(query)
    configs = result.scalars().all()

    count = len(configs)
    is_valid = count == 5

    if is_valid:
        logger.debug(f"【配置验证】llm_id={llm_id}, 配置完整 ({count}/5)")
    else:
        logger.warning(f"【配置验证】llm_id={llm_id}, 配置不完整 ({count}/5)")

    return is_valid


async def get_missing_scenarios(llm_id: str, db: AsyncSession) -> List[str]:
    """
    获取缺失的场景列表

    Args:
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        缺失的场景名称列表
    """
    required_scenarios = ["chat", "memory", "summary", "extraction", "emotion"]

    config_map = await get_llm_configs_batch(llm_id, db)
    existing_scenarios = list(config_map.keys())

    missing_scenarios = [s for s in required_scenarios if s not in existing_scenarios]

    logger.info(f"【缺失场景】llm_id={llm_id}, missing={missing_scenarios}")
    return missing_scenarios