"""
JSON 安全解析工具

统一处理 JSON 解析的异常和默认值返回。
"""

import json
from typing import Any, Optional, TypeVar, Callable
from loguru import logger

T = TypeVar('T')


def safe_json_parse(
    json_str: Optional[str],
    default: T = None,
    parser: Optional[Callable[[str], T]] = None,
    log_warning: bool = True,
) -> T:
    """
    安全解析 JSON 字符串

    Args:
        json_str: JSON 字符串（可能为 None 或空）
        default: 解析失败时的默认返回值
        parser: 可选的自定义解析函数（如 model_validate）
        log_warning: 是否在解析失败时输出警告日志

    Returns:
        解析后的对象，或默认值

    Examples:
        >>> safe_json_parse('{"key": "value"}')
        {'key': 'value'}

        >>> safe_json_parse(None, default={})
        {}

        >>> safe_json_parse('invalid', default=[])
        []
    """
    if not json_str:
        return default

    try:
        result = json.loads(json_str)
        if parser:
            return parser(result)
        return result
    except json.JSONDecodeError as e:
        if log_warning:
            logger.warning(f"JSON 解析失败: {e}, 原始内容: {json_str[:100]}...")
        return default