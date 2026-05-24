"""
情绪分类服务模块

职责：
- 调用 LLM 分析模型回复的情绪状态
- 返回情绪标签和确定性
- 与 current_state 模块配合更新 Redis 状态（阶段2升级）

重构说明：
- 使用策略层替代硬编码的 get_emotion_model()
- 需要传入 llm_id 和 db 参数以查询用户配置
"""

import re

from langchain_core.prompts import PromptTemplate
from loguru import logger

from app.service.chat.strategy.base_strategy import EmotionInvokeStrategy
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.state_manager import update_current_state, get_current_state
from app.schemas.current_state import UpdateSource
from app.util.template_util import escape_template
from app.core.db.mysql_client import async_session_local


async def classify_emotion(model_reply: str, llm_id: str = None, db = None) -> tuple[str, str]:
    """
    分析模型回复的情绪状态（使用策略层）

    Args:
        model_reply: 模型的回复文本
        llm_id: AI 朋友 ID（用于查询配置）
        db: 数据库会话（可选，如果没有传入则自动创建）

    Returns:
        (emotion_label, certainty): 情绪标签和确定性
    """
    try:
        strategy = EmotionInvokeStrategy()

        prompt_text = await PromptManager.get_prompt("emotion_classifier")
        prompt_text = escape_template(prompt_text, ["model_reply"])

        # 构建 messages
        messages = [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": model_reply}
        ]

        # 获取配置（如果没有传入 db，则自动创建 session）
        from app.service.llm_config_service import get_llm_configs_batch
        if llm_id:
            if db:
                config_map = await get_llm_configs_batch(llm_id, db)
            else:
                async with async_session_local() as session:
                    config_map = await get_llm_configs_batch(llm_id, session)
        else:
            config_map = {}

        result_text = await strategy.invoke(messages, config_map)
        
        emotion, certainty = _parse_emotion_result(result_text)
        
        logger.info(f"【情绪分类】模型回复: \"{model_reply[:50]}...\" → {emotion}:{certainty}")
        
        return (emotion, certainty)
        
    except Exception as e:
        logger.error(f"情绪分类调用失败: {e}")
        return ("neutral", "不确定")


def _parse_emotion_result(result_text: str) -> tuple[str, str]:
    """
    解析 LLM 返回的情绪分类结果
    
    Args:
        result_text: LLM 返回的文本
    
    Returns:
        (emotion, certainty): 解析后的情绪和确定性
    """
    import json
    
    text = result_text.strip()
    
    text = re.sub(r'<思索>.*?</思索>', '', text, flags=re.DOTALL).strip()
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    lines = text.split('\n')
    clean_lines = [line for line in lines if not line.strip().startswith('思索') and not line.strip().startswith('think')]
    text = '\n'.join(clean_lines).strip()
    
    json_match = re.search(r'\{[^{}]*"emotion"[^{}]*\}', text)
    if json_match:
        try:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            emotion = result.get("emotion", "neutral")
            certainty = result.get("certainty", "不确定")
            return (emotion, certainty)
        except json.JSONDecodeError:
            pass
    
    pattern1 = r"^([\u4e00-\u9fa5a-zA-Z]+)\s*[:：]\s*(确定|不确定)$"
    match = re.match(pattern1, text)
    
    if match:
        emotion = match.group(1)
        certainty = match.group(2)
        return (emotion, certainty)
    
    pattern2 = r"(开心|悲伤|愤怒|惊讶|恐惧|厌恶|neutral)"
    emotion_match = re.search(pattern2, text)
    certainty_match = re.search(r"(确定|不确定)", text)
    
    if emotion_match and certainty_match:
        return (emotion_match.group(1), certainty_match.group(1))
    
    if emotion_match:
        return (emotion_match.group(1), "不确定")
    
    logger.warning(f"情绪分类结果解析失败，原始输出: '{result_text[:200]}'")
    return ("neutral", "不确定")


async def classify_and_update_emotion(
    user_id: str,
    llm_id: str,
    model_reply: str,
    current_round: int = 0,
    db = None,
) -> None:
    """
    分析情绪并更新状态（供后台任务调用）

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        model_reply: 模型回复
        current_round: 当前全局轮数
        db: 数据库会话
    """
    try:
        emotion, certainty = await classify_emotion(model_reply, llm_id, db)

        # 阶段2：更新状态容器.情绪
        if certainty == "确定":
            update_current_state(
                user_id=user_id,
                llm_id=llm_id,
                field_name="emotion",
                new_value=emotion,
                confidence=0.9,
                source=UpdateSource.RUNTIME,
                reason=f"情绪分类结果: {emotion}",
                current_round=current_round,
            )
            logger.info(f"【情绪更新】emotion = {emotion}")
        else:
            logger.debug(f"【情绪保持】确定性不足，保持原状态")

    except Exception as e:
        logger.error(f"情绪分类后台任务失败: {e}")