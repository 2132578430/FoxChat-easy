"""RedisJSON 写入辅助工具。"""

import json
from typing import Any


def serialize_redis_json_value(value: Any) -> str:
    """将 Python 值序列化为 RedisJSON 可接受的 JSON 字符串。"""
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return json.dumps(value, ensure_ascii=False)

    raise TypeError(f"不支持的 RedisJSON 值类型: {type(value)!r}")


def json_set_safe(redis_like, key: str, path: str, value: Any) -> None:
    """安全执行 JSON.SET，确保 value 始终是合法 JSON 文本。"""
    redis_like.execute_command("JSON.SET", key, path, serialize_redis_json_value(value))