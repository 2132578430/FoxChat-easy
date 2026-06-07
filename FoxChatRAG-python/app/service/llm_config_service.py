"""
LLM 配置服务模块

职责:
- 批量查询 LLM 配置 (5 个场景一次性查询)
- 配置完整性验证
- 测试连接验证

注意：
  LLM 配置的增删改由 Java 端 LlmConfigServiceImpl 直接操作 MySQL，
  Python 不再维护重复的 save/delete 逻辑。
  仅保留 Java 无法替代的功能：查询（chat 流程内部使用）和连通性测试（需要 litellm）。
"""

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
    # 查询后根据模型类型分类存储配置
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