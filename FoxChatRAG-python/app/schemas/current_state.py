"""
当前状态容器 Schema 定义

用于表达"当前是什么局面"。T2a 起只保留 mood 字段。
"""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.mood import MoodLabel, MoodState, normalize_mood_label


class UpdateSource(StrEnum):
    """状态更新来源"""
    RUNTIME = "runtime"
    SUMMARY = "summary"
    USER_EXPLICIT = "user_explicit"


def _legacy_mood(emotion: object) -> dict | None:
    if isinstance(emotion, str):
        value = emotion
        confidence = 0.5
        update_round = 0
        reason = "legacy migration"
    elif isinstance(emotion, dict):
        value = emotion.get("value", "")
        confidence = emotion.get("confidence", 0.5)
        update_round = emotion.get("update_round", 0)
        reason = emotion.get("update_reason", "legacy migration")
    else:
        return None

    label = normalize_mood_label(value) or MoodLabel.CALM
    return {
        "label": label.value,
        "intensity": 0.0 if label == MoodLabel.CALM else 0.30,
        "baseline_label": MoodLabel.CALM.value,
        "confidence": confidence,
        "update_round": update_round,
        "update_reason": reason,
    }


class CurrentState(BaseModel):
    """当前工作状态层容器（T2a 起只保留 mood）"""

    mood: MoodState = Field(default_factory=MoodState, description="当前情绪状态")
    last_update: str = Field(default="", description="最后更新时间（ISO datetime）")
    update_source: UpdateSource = Field(default=UpdateSource.RUNTIME, description="更新来源")

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_emotion(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if data.get("mood"):
            return data
        legacy = data.pop("emotion", None)
        mood = _legacy_mood(legacy)
        if mood is not None:
            data["mood"] = mood
        return data
