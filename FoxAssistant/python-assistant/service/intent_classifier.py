"""
意图分类器

两层架构：
- 第一层：关键词组合匹配（微秒级，覆盖80%高频场景）
- 第二层：语义向量匹配（毫秒级，覆盖99.5%场景）- 延迟加载

关键设计：
- 向量模型懒加载：只有在关键词匹配失败时才加载
- 使用 sentence-transformers（无需 Ollama）
- INTENT_EMBEDDINGS 预计算：模型加载后计算样例 embedding 缓存
"""

import json
import numpy as np
from typing import Optional, List
from dataclasses import dataclass
from loguru import logger
from pathlib import Path

from config.keyword_rules import KEYWORD_RULES, NEGATION_WORDS, IntentType


# ============================================================
# IntentResult 数据结构
# ============================================================

@dataclass
class IntentResult:
    """意图判断结果"""
    intent: str
    description: str
    confidence: float = 1.0  # 规则匹配=1.0，语义匹配为实际相似度
    matched_by: str = "keyword"  # "keyword" or "semantic"


# ============================================================
# INTENT_EMBEDDINGS 缓存（懒加载）
# ============================================================

INTENT_EMBEDDINGS: dict = {}  # {intent_type: np.array(embeddings)}
INTENT_LABELS: List[str] = []  # 所有意图类型列表
INTENT_SAMPLES: dict = {}  # 样例库
_embedding_model = None  # sentence-transformers 模型
_model_loaded = False  # 模型是否已尝试加载
_samples_loaded = False  # 样例是否已加载


def load_intent_samples():
    """
    加载意图样例（启动时执行，不加载模型）
    """
    global INTENT_SAMPLES, INTENT_LABELS, _samples_loaded

    if _samples_loaded:
        return

    samples_path = Path(__file__).parent.parent / "config" / "intent_samples.json"
    if not samples_path.exists():
        logger.warning("【意图样例】文件不存在: intent_samples.json")
        return

    try:
        with open(samples_path, "r", encoding="utf-8") as f:
            INTENT_SAMPLES = json.load(f)
        INTENT_LABELS = list(INTENT_SAMPLES.keys())
        _samples_loaded = True
        logger.info(f"【意图样例】已加载 {len(INTENT_LABELS)} 个意图类型")
    except Exception as e:
        logger.error(f"【意图样例】加载失败: {e}")


def init_embedding_model():
    """
    延迟加载 embedding 模型（只在需要时加载）

    使用 sentence-transformers（无需 Ollama）
    """
    global _embedding_model, _model_loaded

    if _model_loaded:
        return _embedding_model is not None

    try:
        import os
        import sys
        # 强制离线模式：使用本地缓存，避免网络超时
        os.environ['HF_HUB_OFFLINE'] = '1'

        logger.debug(f"【向量模型】尝试导入 sentence_transformers (Python: {sys.executable})")
        from sentence_transformers import SentenceTransformer
        # BGE 中文向量模型（轻量、中文效果好）
        _embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        _model_loaded = True
        logger.info("【向量模型】sentence-transformers 已加载")
        return True
    except ImportError as e:
        logger.warning(f"【向量模型】sentence-transformers 未安装: {e}")
    except Exception as e:
        logger.warning(f"【向量模型】加载失败: {e}")

    _model_loaded = True  # 标记已尝试加载（避免重复尝试）
    return False


def init_intent_embeddings():
    """
    初始化意图向量缓存（模型加载后执行）

    预计算所有样例的 embedding
    """
    global INTENT_EMBEDDINGS

    if not _samples_loaded:
        load_intent_samples()

    if _embedding_model is None:
        logger.info("【向量模型】未加载，跳过预计算")
        return

    if len(INTENT_EMBEDDINGS) > 0:
        return  # 已初始化

    for intent_type, examples in INTENT_SAMPLES.items():
        try:
            # 批量计算 embedding
            embeddings = _embedding_model.encode(examples)
            INTENT_EMBEDDINGS[intent_type] = np.array(embeddings)
            logger.info(f"【意图向量库】预计算 {intent_type}: {len(examples)} 条样例")
        except Exception as e:
            logger.warning(f"【意图向量库】预计算失败 {intent_type}: {e}")
            INTENT_EMBEDDINGS[intent_type] = np.array([])


# 启动时只加载样例（不加载模型）
load_intent_samples()


# ============================================================
# 第一层：关键词组合匹配
# ============================================================

def match_intent_by_keyword(text: str) -> Optional[IntentResult]:
    """
    关键词组合匹配（微秒级）

    Args:
        text: 用户输入文本

    Returns:
        IntentResult 如果匹配成功，否则 None
    """
    for keywords, intent, description, negation_words in KEYWORD_RULES:
        # 检查是否包含所有关键词
        all_keywords_present = all(kw in text for kw in keywords)

        if not all_keywords_present:
            continue

        # 检查否定词
        has_negation = any(nw in text for nw in negation_words)

        if has_negation:
            # 有否定词，跳过此规则
            logger.debug(f"【关键词匹配】\"{text}\" 包含否定词，跳过 {intent}")
            continue

        logger.debug(f"【关键词匹配】\"{text}\" → {intent}")
        return IntentResult(
            intent=intent,
            description=description,
            confidence=1.0,
            matched_by="keyword"
        )

    return None  # 未匹配


# ============================================================
# 第二层：语义向量匹配（延迟加载）
# ============================================================

def match_intent_by_semantic(text: str) -> Optional[IntentResult]:
    """
    语义向量匹配（毫秒级）

    如果向量模型未加载，会尝试延迟加载

    Args:
        text: 用户输入文本

    Returns:
        IntentResult 如果匹配成功，否则 None
    """
    global _embedding_model, INTENT_EMBEDDINGS

    # 延迟加载模型（第一次需要语义匹配时才加载）
    if _embedding_model is None:
        if not init_embedding_model():
            # 模型加载失败，快速返回 None（降级为 chat_intent）
            logger.info("【语义匹配】向量模型不可用，跳过语义匹配")
            return None
        # 模型加载成功，预计算 embedding
        init_intent_embeddings()

    # 检查向量库是否可用
    if len(INTENT_EMBEDDINGS) == 0:
        logger.info("【语义匹配】向量库未初始化，跳过语义匹配")
        return None

    try:
        # 计算查询 embedding（sentence-transformers.encode 返回 numpy array）
        query_embedding = _embedding_model.encode(text)
    except Exception as e:
        # embedding 计算失败，快速返回 None
        logger.info(f"【语义匹配】embedding 计算失败: {e}")
        return None

    # 计算与各意图样例的相似度
    best_intent = None
    best_score = 0.0
    best_description = ""

    for intent_type, embeddings in INTENT_EMBEDDINGS.items():
        if len(embeddings) == 0:
            continue

        # 计算 cosine similarity
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
            # 从样例推断描述
            best_description = f"语义匹配({intent_type})"

    # 阈值判断（提高到 0.75，过滤模糊聊天词）
    threshold = 0.75
    if best_score < threshold or best_intent is None:
        logger.debug(f"【语义匹配】\"{text}\" 最佳分数 {best_score:.2f} < 阈值 {threshold}")
        return None

    logger.debug(f"【语义匹配】\"{text}\" → {best_intent} (score={best_score:.2f})")
    return IntentResult(
        intent=best_intent,
        description=best_description,
        confidence=best_score,
        matched_by="semantic"
    )


# ============================================================
# 主函数：两层意图判断
# ============================================================

def classify_intent(text: str) -> IntentResult:
    """
    两层意图判断

    流程：
    1. 关键词匹配（微秒级）
    2. 未匹配 → 语义匹配（毫秒级）
    3. 都未匹配 → 默认 chat_intent

    Args:
        text: 用户输入文本

    Returns:
        IntentResult（始终返回，不会是 None）
    """
    # 第一层：关键词匹配
    result = match_intent_by_keyword(text)
    if result:
        logger.info(f"【意图判断】关键词匹配: {result.intent} (conf={result.confidence:.2f})")
        return result

    # 第二层：语义匹配
    result = match_intent_by_semantic(text)
    if result:
        logger.info(f"【意图判断】语义匹配: {result.intent} (conf={result.confidence:.2f})")
        return result

    # 未匹配：返回聊天意图
    logger.info(f"【意图判断】未匹配，返回 chat_intent: \"{text}\"")
    return IntentResult(
        intent=IntentType.CHAT_INTENT,
        description="聊天意图",
        confidence=0.0,
        matched_by="default"
    )