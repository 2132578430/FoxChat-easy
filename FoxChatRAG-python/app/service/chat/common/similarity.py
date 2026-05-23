"""
相似度计算工具

统一文本相似度计算方法。
"""

from typing import Set


def calc_jaccard_similarity(content1: str, content2: str) -> float:
    """
    计算两个内容的字符级 Jaccard 相似度

    Jaccard 相似度 = 交集大小 / 并集大小

    Args:
        content1: 第一个内容
        content2: 第二个内容

    Returns:
        相似度值 (0.0 ~ 1.0)

    Examples:
        >>> calc_jaccard_similarity("hello world", "hello")
        0.5

        >>> calc_jaccard_similarity("", "hello")
        0.0
    """
    if not content1 or not content2:
        return 0.0

    set1: Set[str] = set(content1)
    set2: Set[str] = set(content2)

    intersection = len(set1 & set2)
    union = max(len(set1), len(set2))

    return intersection / union if union > 0 else 0.0


def calc_word_overlap_ratio(text1: str, text2: str) -> float:
    """
    计算两个文本的词汇重叠比例

    Args:
        text1: 第一个文本
        text2: 第二个文本

    Returns:
        重叠比例 (0.0 ~ 1.0)
    """
    if not text1 or not text2:
        return 0.0

    words1 = set(text1.split())
    words2 = set(text2.split())

    if not words1 or not words2:
        return 0.0

    overlap = len(words1 & words2)
    union = len(words1 | words2)

    return overlap / union if union > 0 else 0.0