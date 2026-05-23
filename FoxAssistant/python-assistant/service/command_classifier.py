"""
命令意图分类器

现在使用两层意图判断系统：
- 第一层：关键词组合匹配（微秒级）
- 第二层：语义向量匹配（毫秒级，延迟加载）

复用 intent_classifier 的分类结果
"""

from typing import Tuple
from loguru import logger

from service.intent_classifier import classify_intent, IntentResult
from config.keyword_rules import IntentType


# ============================================================
# CommandType 常量（保持兼容）
# ============================================================

class CommandType:
    """命令类型常量（保持原有兼容）"""
    PLAY_MUSIC = "play_music"
    PAUSE_MUSIC = "pause_music"
    NEXT_SONG = "next_song"
    PREV_SONG = "prev_song"
    QUERY_TIME = "query_time"
    QUERY_WEATHER = "query_weather"
    SET_REMINDER = "set_reminder"
    SHUTDOWN = "shutdown"
    SLEEP = "sleep"
    UNKNOWN = "unknown"
    CHAT_INTENT = "chat_intent"  # 新增：聊天意图


# ============================================================
# 分类函数（兼容原有接口）
# ============================================================

def classify_command(text: str) -> Tuple[str, str]:
    """
    命令意图分类

    Args:
        text: 用户输入文本

    Returns:
        (intent, description) 命令类型和描述
    """
    result: IntentResult = classify_intent(text)

    # 兼容原有返回格式
    return result.intent, result.description