"""
聊天服务公共工具模块

统一导出所有公共函数和常量。
"""

from app.service.chat.common.json_parser import safe_json_parse
from app.service.chat.common.emotion_mapper import EMOTION_CN_MAP, map_emotion_to_cn
from app.service.chat.common.similarity import calc_jaccard_similarity, calc_word_overlap_ratio
from app.common.constant.LLMChatConstant import build_chat_key

__all__ = [
    # JSON 解析
    "safe_json_parse",
    # 情绪映射
    "EMOTION_CN_MAP",
    "map_emotion_to_cn",
    # 相似度计算
    "calc_jaccard_similarity",
    "calc_word_overlap_ratio",
    # Redis key 构建
    "build_chat_key",
]