"""
LiteLLM Wrapper - 替代硬编码的 model.py 单例实例

职责:
- 提供 LiteLLM 初始化和配置辅助函数
- 保留向后兼容性（暂时保留旧的 singleton 实例）
- 逐步迁移策略：新代码用策略层，旧代码暂时保留

Note: 这是过渡性的 wrapper，最终会被策略层完全替代
"""

from loguru import logger


def format_model_name(model_name: str) -> str:
    """
    格式化模型名称（添加 provider prefix）

    Args:
        model_name: 用户提供的模型名称 (e.g., 'gpt-4o', 'deepseek-chat')

    Returns:
        LiteLLM 格式的模型名称 (e.g., 'openai/gpt-4o', 'deepseek/deepseek-chat')

    Examples:
        - 'gpt-4o' → 'openai/gpt-4o'
        - 'deepseek-chat' → 'deepseek/deepseek-chat'
        - 'claude-3-sonnet' → 'anthropic/claude-3-sonnet'
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


async def get_llm_config_for_scenario(llm_id: str, scenario: str, db) -> dict:
    """
    获取指定场景的 LLM 配置

    Args:
        llm_id: AI 朋友 ID
        scenario: 场景名称 (chat, memory, summary, extraction, emotion)
        db: 数据库会话

    Returns:
        配置字典 (model_name, api_key, base_url, temperature, max_tokens, ...)
    """
    from app.service.llm_config_service import get_llm_configs_batch

    config_map = await get_llm_configs_batch(llm_id, db)
    config = config_map.get(scenario)

    if not config:
        logger.error(f"【配置缺失】llm_id={llm_id}, scenario={scenario}")
        raise ValueError(f"场景 {scenario} 未配置")

    return config


# ============================================================
# 向后兼容：保留旧的 singleton 实例引用（暂时）
# ============================================================

# 这些实例会被逐步废弃，新代码应该使用策略层
# deprecated_instances = {
#     "ds_model": None,
#     "kimi_model": None,
#     "glm_model": None,
#     ...
# }

logger.info("【LiteLLM Wrapper】初始化完成 - 新代码请使用策略层")