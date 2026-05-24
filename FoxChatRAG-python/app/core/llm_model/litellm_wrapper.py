"""
LiteLLM Wrapper

职责:
- 提供 LiteLLM 初始化和配置辅助函数
"""

from loguru import logger
from app.core.db.mysql_client import async_session_local


def format_model_name(model_name: str) -> str:
    """
    格式化模型名称（添加 provider prefix）
    """
    # 已知 provider 的前缀映射
    provider_prefixes = {
        "gpt": "openai",
        "o1": "openai",
        "deepseek": "deepseek",
        "claude": "anthropic",
        "gemini": "gemini",
        "moonshot": "moonshot",
        "glm": "zhipu",
        "qwen": "qwen",
        "astron": "astron",
    }

    # 如果已经包含 provider prefix，直接返回
    if "/" in model_name:
        return model_name

    # 自动识别 provider 并添加 prefix
    for prefix_key, provider in provider_prefixes.items():
        if model_name.startswith(prefix_key):
            formatted = f"{provider}/{model_name}"
            logger.debug(f"【模型名称格式化】{model_name} → {formatted}")
            return formatted

    # 无法识别的 provider，返回原名（让 LiteLLM 自动处理）
    logger.warning(f"【模型名称】无法识别 provider: {model_name}")
    return model_name


async def get_llm_config_for_scenario(llm_id: str, scenario: str, db = None) -> dict:
    """
    获取指定场景的 LLM 配置

    Args:
        llm_id: AI 朋友 ID
        scenario: 场景名称 (chat, memory, summary, extraction, emotion)
        db: 数据库会话（可选，如果没有传入则自动创建）

    Returns:
        配置字典 (model_name, api_key, base_url, temperature, max_tokens, ...)
    """
    from app.service.llm_config_service import get_llm_configs_batch

    # 如果没有传入 db，则自动创建 session
    if db:
        config_map = await get_llm_configs_batch(llm_id, db)
    else:
        async with async_session_local() as session:
            config_map = await get_llm_configs_batch(llm_id, session)

    config = config_map.get(scenario)

    if not config:
        logger.error(f"【配置缺失】llm_id={llm_id}, scenario={scenario}")
        raise ValueError(f"场景 {scenario} 未配置")

    return config