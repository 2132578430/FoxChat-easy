"""
意图判断模块

两层架构：
- 第一层：规则模板匹配（微秒级，覆盖80%高频场景）
- 第二层：语义向量匹配（毫秒级，覆盖99.5%场景）

关键设计：
- embedding 复用：避免重复调用 embedding API
- INTENT_EMBEDDINGS 预计算：启动时计算样例 embedding 缓存
"""

import re
import numpy as np
from typing import Optional, List, Tuple
from loguru import logger

from app.common.constant.intent_config import (
    INTENT_RULES,
    INTENT_EXAMPLES,
    RETRIEVAL_STRATEGY,
    IntentResult,
    IntentType,
)
from app.core.llm_model.model import chroma_model


# ============================================================
# INTENT_EMBEDDINGS 缓存（启动时预计算）
# ============================================================

INTENT_EMBEDDINGS: dict = {}  # {intent_type: np.array(embeddings)}
INTENT_LABELS: List[str] = []  # 所有意图类型列表

def _init_intent_embeddings():
    """
    初始化意图向量缓存

    启动时预计算所有样例的 embedding，避免运行时重复计算
    """
    global INTENT_EMBEDDINGS, INTENT_LABELS

    INTENT_LABELS = list(INTENT_EXAMPLES.keys())

    for intent_type, examples in INTENT_EXAMPLES.items():
        try:
            # 批量计算 embedding
            embeddings = chroma_model.embed(examples)  # 返回 List[List[float]]
            INTENT_EMBEDDINGS[intent_type] = np.array(embeddings)
            logger.info(f"【意图向量库】预计算 {intent_type}: {len(examples)} 条样例")
        except Exception as e:
            logger.warning(f"【意图向量库】预计算失败 {intent_type}: {e}")
            INTENT_EMBEDDINGS[intent_type] = np.array([])

# 启动时自动初始化（延迟初始化，避免循环导入）
_initialized = False

def _ensure_initialized():
    """确保向量库已初始化"""
    global _initialized
    if not _initialized:
        _init_intent_embeddings()
        _initialized = True


# ============================================================
# 第一层：规则模板匹配
# ============================================================

def match_intent_by_rule(query: str) -> Optional[IntentResult]:
    """
    规则模板匹配（微秒级）

    Args:
        query: 用户查询文本

    Returns:
        IntentResult 如果匹配成功，否则 None
    """
    for pattern, intent, scope_str, description in INTENT_RULES:
        try:
            if re.match(pattern, query, re.IGNORECASE):
                # 获取检索策略
                strategy = RETRIEVAL_STRATEGY.get(intent, RETRIEVAL_STRATEGY["default"])

                # 处理 scope
                if scope_str == "skip":
                    scope = []
                    skip = True
                elif scope_str == "all":
                    scope = []
                    skip = False
                else:
                    scope = [scope_str]
                    skip = False

                return IntentResult(
                    intent=intent,
                    scope=scope,
                    top_k=strategy.get("top_k", 4),
                    skip=skip,
                    confidence=1.0,  # 规则匹配置信度=1.0
                )
        except re.error as e:
            logger.warning(f"【规则匹配】正则错误: {pattern} - {e}")
            continue

    return None  # 未匹配


# ============================================================
# 第二层：语义向量匹配
# ============================================================

def match_intent_by_semantic(
    query: str,
    query_embedding: Optional[np.ndarray] = None,
) -> Optional[IntentResult]:
    """
    语义向量匹配（毫秒级）

    Args:
        query: 用户查询文本
        query_embedding: 可选，预计算的查询 embedding（复用）

    Returns:
        IntentResult 如果匹配成功，否则 None
    """
    _ensure_initialized()

    # 获取查询 embedding（复用或计算）
    if query_embedding is None:
        try:
            query_embedding = np.array(chroma_model.embed(query))
        except Exception as e:
            logger.warning(f"【语义匹配】embedding 计算失败: {e}")
            return None

    # 计算与各意图样例的相似度
    best_intent = None
    best_score = 0.0

    for intent_type, embeddings in INTENT_EMBEDDINGS.items():
        if len(embeddings) == 0:
            continue

        # 计算与所有样例的 cosine similarity
        # query_embedding: (dim,)
        # embeddings: (n_examples, dim)

        # 归一化
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        embeddings_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)

        # cosine similarity
        similarities = np.dot(embeddings_norm, query_norm)
        max_sim = np.max(similarities)
        avg_sim = np.mean(similarities)

        # 取最高相似度作为该意图的分数
        score = max_sim * 0.7 + avg_sim * 0.3  # 加权

        if score > best_score:
            best_score = score
            best_intent = intent_type

    # 阈值判断
    if best_score < 0.5 or best_intent is None:
        return None

    # 获取检索策略
    strategy = RETRIEVAL_STRATEGY.get(best_intent, RETRIEVAL_STRATEGY["default"])

    return IntentResult(
        intent=best_intent,
        scope=strategy.get("scope", []),
        top_k=strategy.get("top_k", 4),
        skip=strategy.get("skip", False),
        confidence=float(best_score),
    )


# ============================================================
# 主函数：两层意图判断
# ============================================================

def classify_intent(
    query: str,
    query_embedding: Optional[np.ndarray] = None,
) -> IntentResult:
    """
    两层意图判断

    流程：
    1. 规则匹配（微秒级）
    2. 未匹配 → 语义匹配（毫秒级）
    3. 都未匹配 → 默认策略

    Args:
        query: 用户查询文本
        query_embedding: 可选，预计算的查询 embedding（用于复用）

    Returns:
        IntentResult（始终返回，不会是 None）
    """
    # 第一层：规则匹配
    result = match_intent_by_rule(query)
    if result:
        logger.debug(f"【意图判断】规则匹配: {result.intent} (conf={result.confidence:.2f})")
        return result

    # 第二层：语义匹配
    result = match_intent_by_semantic(query, query_embedding)
    if result:
        logger.debug(f"【意图判断】语义匹配: {result.intent} (conf={result.confidence:.2f})")
        return result

    # 未匹配：返回默认策略
    default_strategy = RETRIEVAL_STRATEGY["default"]
    logger.debug(f"【意图判断】未匹配，使用默认策略")

    return IntentResult(
        intent=IntentType.DEFAULT,
        scope=default_strategy.get("scope", []),
        top_k=default_strategy.get("top_k", 4),
        skip=default_strategy.get("skip", False),
        confidence=0.0,
    )


# ============================================================
# 辅助函数：获取检索参数
# ============================================================

def get_retrieval_params(intent_result: IntentResult) -> dict:
    """
    根据意图结果获取检索参数

    Args:
        intent_result: 意图判断结果

    Returns:
        检索参数字典: {"skip": bool, "top_k": int, "scope": List[str]}
    """
    return {
        "skip": intent_result.skip,
        "top_k": intent_result.top_k,
        "scope": intent_result.scope,
    }