"""
相似度计算工具

统一文本相似度计算方法。
"""

import jieba
from typing import Set, List


def calc_jaccard_similarity(content1: str, content2: str) -> float:
    """
    计算两个内容的 Jaccard 相似度（基于 jieba 分词）

    Jaccard 相似度 = 交集大小 / 并集大小
    Returns:
        相似度值 (0.0 ~ 1.0)
    """
    if not content1 or not content2:
        return 0.0

    tokens1: List[str] = [t for t in jieba.cut(content1) if len(t) > 1]
    tokens2: List[str] = [t for t in jieba.cut(content2) if len(t) > 1]

    set1: Set[str] = set(tokens1)
    set2: Set[str] = set(tokens2)

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0