"""
情绪映射工具

统一英文情绪标签到中文的映射。
"""

# 英文情绪到中文的映射表
EMOTION_CN_MAP = {
    "neutral": "平静",
    "happy": "开心",
    "sad": "难过",
    "anger": "愤怒",
    "angry": "愤怒",
    "surprise": "惊讶",
    "surprised": "惊讶",
    "fear": "恐惧",
    "fearful": "恐惧",
    "disgust": "厌恶",
    "disgusted": "厌恶",
    # 中文情绪（保持原样）
    "开心": "开心",
    "悲伤": "悲伤",
    "愤怒": "愤怒",
    "惊讶": "惊讶",
    "恐惧": "恐惧",
    "厌恶": "厌恶",
    "平静": "平静",
}


def map_emotion_to_cn(emotion: str) -> str:
    """
    将情绪标签映射为中文

    Args:
        emotion: 英文或中文情绪标签

    Returns:
        中文情绪标签

    Examples:
        >>> map_emotion_to_cn("happy")
        '开心'

        >>> map_emotion_to_cn("开心")
        '开心'

        >>> map_emotion_to_cn("unknown")
        'unknown'
    """
    if not emotion:
        return "平静"
    return EMOTION_CN_MAP.get(emotion.lower(), emotion)