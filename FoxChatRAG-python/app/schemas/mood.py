"""
情绪状态数据模型

模型只输出标签、序数等级和确定性；数值强度由代码锚点生成。
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MoodLabel(StrEnum):
    CALM = "平静"
    HAPPY = "开心"
    EXCITED = "兴奋"
    SECURE = "安心"
    MOVED = "感动"
    ANTICIPATING = "期待"
    SAD = "难过"
    DISAPPOINTED = "失望"
    AGGRIEVED = "委屈"
    ANGRY = "愤怒"
    ANXIOUS = "焦虑"
    MISSING = "思念"
    EMBARRASSED = "尴尬"
    TIRED = "疲惫"


class MoodLevel(StrEnum):
    MILD = "轻微"
    CLEAR = "明显"
    STRONG = "强烈"


MOOD_LEVEL_ANCHOR: dict[MoodLevel, float] = {
    MoodLevel.MILD: 0.30,
    MoodLevel.CLEAR: 0.60,
    MoodLevel.STRONG: 0.90,
}

MOOD_LEVEL_ALIASES: dict[str, MoodLevel] = {
    "轻微": MoodLevel.MILD,
    "轻度": MoodLevel.MILD,
    "低": MoodLevel.MILD,
    "mild": MoodLevel.MILD,
    "low": MoodLevel.MILD,
    "明显": MoodLevel.CLEAR,
    "中等": MoodLevel.CLEAR,
    "中": MoodLevel.CLEAR,
    "clear": MoodLevel.CLEAR,
    "medium": MoodLevel.CLEAR,
    "moderate": MoodLevel.CLEAR,
    "强烈": MoodLevel.STRONG,
    "很强": MoodLevel.STRONG,
    "高": MoodLevel.STRONG,
    "strong": MoodLevel.STRONG,
    "high": MoodLevel.STRONG,
}

_MOOD_LABEL_ALIASES: dict[str, MoodLabel] = {
    "平静": MoodLabel.CALM,
    "calm": MoodLabel.CALM,
    "neutral": MoodLabel.CALM,
    "开心": MoodLabel.HAPPY,
    "happy": MoodLabel.HAPPY,
    "兴奋": MoodLabel.EXCITED,
    "excited": MoodLabel.EXCITED,
    "安心": MoodLabel.SECURE,
    "secure": MoodLabel.SECURE,
    "感动": MoodLabel.MOVED,
    "moved": MoodLabel.MOVED,
    "期待": MoodLabel.ANTICIPATING,
    "anticipating": MoodLabel.ANTICIPATING,
    "难过": MoodLabel.SAD,
    "sad": MoodLabel.SAD,
    "悲伤": MoodLabel.SAD,
    "失望": MoodLabel.DISAPPOINTED,
    "disappointed": MoodLabel.DISAPPOINTED,
    "厌恶": MoodLabel.DISAPPOINTED,
    "disgust": MoodLabel.DISAPPOINTED,
    "委屈": MoodLabel.AGGRIEVED,
    "aggrieved": MoodLabel.AGGRIEVED,
    "愤怒": MoodLabel.ANGRY,
    "angry": MoodLabel.ANGRY,
    "焦虑": MoodLabel.ANXIOUS,
    "anxious": MoodLabel.ANXIOUS,
    "恐惧": MoodLabel.ANXIOUS,
    "fear": MoodLabel.ANXIOUS,
    "思念": MoodLabel.MISSING,
    "missing": MoodLabel.MISSING,
    "尴尬": MoodLabel.EMBARRASSED,
    "embarrassed": MoodLabel.EMBARRASSED,
    "疲惫": MoodLabel.TIRED,
    "tired": MoodLabel.TIRED,
    "惊讶": MoodLabel.EXCITED,
    "surprised": MoodLabel.EXCITED,
}


def normalize_mood_label(raw: str | None) -> MoodLabel | None:
    if not raw:
        return None
    value = str(raw).strip()
    for label in MoodLabel:
        if value == label.value:
            return label
    return _MOOD_LABEL_ALIASES.get(value.lower())


def normalize_mood_level(raw: str | None) -> MoodLevel | None:
    if not raw:
        return None
    value = str(raw).strip()
    for level in MoodLevel:
        if value == level.value:
            return level
    return MOOD_LEVEL_ALIASES.get(value.lower())


class MoodObservation(BaseModel):
    label: MoodLabel
    level: MoodLevel
    certainty: Literal["确定", "不确定"] = "不确定"
    evidence: str = ""

    @field_validator("label", mode="before")
    @classmethod
    def _normalize_label(cls, value):
        if isinstance(value, MoodLabel):
            return value
        normalized = normalize_mood_label(value)
        if normalized is None:
            raise ValueError(f"非法情绪标签: {value}")
        return normalized

    @field_validator("level", mode="before")
    @classmethod
    def _normalize_level(cls, value):
        if isinstance(value, MoodLevel):
            return value
        normalized = normalize_mood_level(value)
        if normalized is None:
            raise ValueError(f"非法情绪等级: {value}")
        return normalized


class MoodState(BaseModel):
    label: MoodLabel = MoodLabel.CALM
    intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    baseline_label: MoodLabel = MoodLabel.CALM
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    update_round: int = 0
    update_reason: str = ""
    pending_label: MoodLabel | None = None
    pending_count: int = 0
    trace: list[tuple[str, float]] = Field(default_factory=list)

    @field_validator("label", "baseline_label", "pending_label", mode="before")
    @classmethod
    def _normalize_labels(cls, value):
        if value is None or isinstance(value, MoodLabel):
            return value
        normalized = normalize_mood_label(value)
        if normalized is None:
            raise ValueError(f"非法情绪标签: {value}")
        return normalized


class MoodConfig(BaseModel):
    injection_enabled: bool = True
    sensor_timeout_seconds: float = 8.0
    sensor_max_tokens: int = 120
    sensor_temperature: float = 0.2

    intensity_alpha: float = 0.45
    intensity_decay: float = 0.80
    baseline_pull: float = 0.05

    switch_confirmations: int = 2
    weak_intensity: float = 0.30
    reset_intensity: float = 0.10
    trace_size: int = 5

    confidence_certain: float = 0.85
    confidence_uncertain: float = 0.35

    context_messages: int = 6
    context_message_chars: int = 200
    context_role_chars: int = 400
    context_event_chars: int = 300
