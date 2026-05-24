"""
LLM 调用策略基类

职责:
- 定义统一的调用接口
- 应用场景默认参数
- 处理 LiteLLM 调用细节
- 异常处理与错误码转换
"""

from typing import List, Dict
from loguru import logger

import asyncio
import litellm


def format_model_name(model_name: str) -> str:
    """
    格式化模型名称（添加 provider prefix）
    
    LiteLLM 要求模型名称包含 provider 前缀，如 'openai/gpt-4'
    对于不包含前缀的模型名称，自动添加 'openai/' 前缀（OpenAI 兼容 API）
    """
    if "/" not in model_name:
        return f"openai/{model_name}"
    return model_name


class LLMInvokeStrategy:
    """LLM 调用策略基类"""

    scenario: str = ""  # 场景名称 (chat, memory, summary, extraction, emotion)
    default_temperature: float = 0.7  # 默认温度
    default_max_tokens: int | None = None  # 默认最大输出长度
    force_json: bool = False  # 是否强制 JSON 输出

    def get_model_params(self, config: dict, **kwargs) -> dict:
        """
        根据场景和用户配置，生成 LiteLLM 参数

        Args:
            config: 用户配置 (model_name, model_api_key, model_base_url, ...)
            **kwargs: 额外参数覆盖

        Returns:
            LiteLLM 参数字典
        """
        # 格式化模型名称（添加 provider 前缀）
        formatted_model = format_model_name(config["model_name"])
        
        params = {
            "model": formatted_model,
            "api_key": config["model_api_key"],
            "base_url": config["model_base_url"],
            "temperature": config.get("model_temperature", self.default_temperature),
        }

        # max_tokens 处理
        max_tokens = kwargs.get("max_tokens", config.get("model_max_tokens", self.default_max_tokens))
        if max_tokens:
            params["max_tokens"] = max_tokens

        # JSON 模式处理
        if self.force_json or config.get("model_response_format") == "json":
            params["response_format"] = {"type": "json_object"}

        # 合并额外 kwargs (kwargs 优先级最高)
        params.update(kwargs)

        logger.debug(f"【策略参数】scenario={self.scenario}, params={params}")
        return params

    async def invoke(
        self,
        messages: List[dict],
        config_map: Dict[str, dict],
        **kwargs
    ) -> str:
        """
        统一调用接口

        Args:
            messages: 消息列表 [{role, content}, ...]
            config_map: 配置字典 {'chat': {...}, 'memory': {...}, ...}
            **kwargs: 额外参数 (temperature, max_tokens, ...)

        Returns:
            LLM 响应文本

        Raises:
            Exception: LiteLLM 调用失败 (转换为错误码)
        """
        # 从 config_map 中提取当前场景的配置
        config = config_map.get(self.scenario)

        if not config:
            raise ValueError(f"配置缺失: scenario={self.scenario} 未配置")

        # 生成调用参数
        params = self.get_model_params(config, **kwargs)

        try:
            logger.info(f"【LiteLLM调用】scenario={self.scenario}, model={params['model']}")

            # 调用 LiteLLM（使用 acompletion 异步方法，带超时和重试）
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await litellm.acompletion(
                        model=params["model"],
                        messages=messages,
                        api_key=params["api_key"],
                        base_url=params["base_url"],
                        temperature=params.get("temperature", self.default_temperature),
                        max_tokens=params.get("max_tokens"),
                        response_format=params.get("response_format"),
                        timeout=120,
                    )
                    break  # 成功，退出重试循环
                except (litellm.exceptions.APIConnectionError, litellm.exceptions.APIStatusError) as e:
                    # 仅重试瞬态网络错误（连接错误或 5xx）
                    status_code = getattr(e, 'status_code', None)
                    if status_code and status_code < 500:
                        raise  # 4xx 错误不是瞬态的，直接抛出
                    if attempt == max_retries - 1:
                        raise  # 重试已用尽
                    logger.warning(
                        f"LLM 调用第 {attempt+1}/{max_retries} 次尝试失败: {e}，"
                        f"{2**attempt}s 后重试..."
                    )
                    await asyncio.sleep(2 ** attempt)

            # 提取响应文本
            content = response.choices[0].message.content

            logger.info(f"【LiteLLM响应】scenario={self.scenario}, length={len(content)}")
            return content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"【LiteLLM错误】scenario={self.scenario}, error={error_msg}")

            # 错误处理: 转换为特定错误码
            if "AuthenticationError" in error_msg or "401" in error_msg:
                raise ValueError("15002: API Key 无效")
            elif "ModelNotFoundError" in error_msg or "model" in error_msg.lower():
                raise ValueError("15003: 模型不存在")
            elif "TimeoutError" in error_msg or "timeout" in error_msg.lower():
                raise ValueError("15004: 连接超时")
            elif "RateLimitError" in error_msg or "429" in error_msg:
                raise ValueError("15005: API 配额已用尽")
            else:
                raise ValueError(f"15000: LiteLLM 调用失败: {error_msg}")


class ChatInvokeStrategy(LLMInvokeStrategy):
    """聊天场景策略"""

    scenario = "chat"
    default_temperature = 0.8  # 高温度，发散性对话
    default_max_tokens = 4096  # 长回复


class MemoryInvokeStrategy(LLMInvokeStrategy):
    """记忆处理场景策略"""

    scenario = "memory"
    default_temperature = 0.3  # 低温度，稳定处理
    default_max_tokens = None  # 不限制


class SummaryInvokeStrategy(LLMInvokeStrategy):
    """消息总结场景策略"""

    scenario = "summary"
    default_temperature = 0.5  # 中温度，平衡总结
    default_max_tokens = 2048  # 简洁总结


class ExtractionInvokeStrategy(LLMInvokeStrategy):
    """信息抽取场景策略"""

    scenario = "extraction"
    default_temperature = 0.0  # 零温度，精确抽取
    force_json = True  # 强制 JSON 输出


class EmotionInvokeStrategy(LLMInvokeStrategy):
    """情绪分类场景策略"""

    scenario = "emotion"
    default_temperature = 0.0  # 零温度，确定性分类
    default_max_tokens = 50  # 短分类结果


# JSON 模式策略 (共享基础配置)
class ChatJSONInvokeStrategy(ChatInvokeStrategy):
    """聊天 JSON 模式策略 (使用 chat 配置 + 强制 JSON)"""

    force_json = True


class MemoryJSONInvokeStrategy(MemoryInvokeStrategy):
    """记忆 JSON 模式策略 (使用 memory 配置 + 强制 JSON)"""

    force_json = True