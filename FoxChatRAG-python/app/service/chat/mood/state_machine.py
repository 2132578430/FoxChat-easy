"""
情绪状态机

纯函数、无 IO：输入上一轮状态和本轮观测，输出新状态与注入文案。
"""

from app.schemas.mood import (
    MOOD_LEVEL_ANCHOR,
    MoodConfig,
    MoodLabel,
    MoodObservation,
    MoodState,
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _pull(value: float, target: float, rate: float) -> float:
    return value + (target - value) * rate


def transition(
    prev: MoodState,
    obs: MoodObservation | None,
    current_round: int,
    cfg: MoodConfig,
) -> MoodState:
    decayed = _clamp(prev.intensity * cfg.intensity_decay, 0.0, 1.0)

    if obs is None or obs.certainty != "确定":
        intensity = _pull(decayed, 0.0, cfg.baseline_pull)
        label = prev.label
        pending_label = None
        pending_count = 0
        confidence = cfg.confidence_uncertain
        reason = "观测缺失或不确定"
    else:
        anchor = 0.0 if obs.label == MoodLabel.CALM else MOOD_LEVEL_ANCHOR[obs.level]
        label = prev.label
        pending_label = prev.pending_label
        pending_count = prev.pending_count

        if obs.label == prev.label:
            intensity = (
                cfg.intensity_alpha * anchor
                + (1 - cfg.intensity_alpha) * decayed
            )
            pending_label = None
            pending_count = 0
        else:
            if obs.label == prev.pending_label:
                pending_count = prev.pending_count + 1
            else:
                pending_count = 1
            pending_label = obs.label

            if (
                pending_count >= cfg.switch_confirmations
                or prev.intensity <= cfg.weak_intensity
            ):
                label = obs.label
                intensity = anchor
                pending_label = None
                pending_count = 0
            else:
                intensity = decayed

        confidence = cfg.confidence_certain
        reason = obs.evidence[:80]

    if intensity < cfg.reset_intensity:
        label = prev.baseline_label
        intensity = 0.0
        pending_label = None
        pending_count = 0

    trace = (prev.trace + [(label.value, round(intensity, 3))])[-cfg.trace_size:]
    return prev.model_copy(update={
        "label": label,
        "intensity": round(intensity, 3),
        "confidence": confidence,
        "update_round": current_round,
        "update_reason": reason,
        "pending_label": pending_label,
        "pending_count": pending_count,
        "trace": trace,
    })


def trend_phrase(mood: MoodState) -> str:
    trace = mood.trace
    if len(trace) < 3:
        return "基本稳定"
    recent = trace[-3:]
    if len({label for label, _ in recent}) > 1:
        return "刚刚转变"
    slope = round((recent[-1][1] - recent[0][1]) / 2.0, 6)
    if slope <= -0.05:
        return "正在减弱"
    if slope >= 0.05:
        return "正在增强"
    return "基本稳定"


def mood_level_word(intensity: float) -> str:
    if intensity < 0.45:
        return "轻微"
    if intensity < 0.75:
        return "明显"
    return "强烈"


def render_mood_text(mood: MoodState) -> str:
    if mood.label == MoodLabel.CALM:
        return f"- 当前情绪：{MoodLabel.CALM.value}"
    intensity_word = mood_level_word(mood.intensity)
    trend = trend_phrase(mood)
    if trend == "刚刚转变":
        return f"- 当前情绪：{mood.label.value}（刚转变为{intensity_word}）"
    return f"- 当前情绪：{mood.label.value}（{intensity_word}，{trend}）"
