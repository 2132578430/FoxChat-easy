"""
历史事件检索服务（主动检索版）

职责：
- 从 memory_bank (Redis) 或 Chroma 检索历史事件
- 按 actor、event_type、importance、freshness 等 metadata 过滤与排序
- 结果去重、预算控制
- 格式化为稳定短文本块供 relevant_memories 使用

【主动检索说明】2026-05-05
移除触发词机制，改为每轮主动检索。
检索逻辑在 chat_msg_service._search_relevant_memories 中实现。
"""

import json
from datetime import datetime
from typing import List, Optional, Dict

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key, EVENT_TYPE_LABELS
from app.core.db.redis_client import redis_client
from app.schemas.memory_event import MemoryEvent, EventActor, EventDetailType, EventType
from app.util.chroma_util import search_history_events
from app.service.chat.common import calc_jaccard_similarity, safe_json_parse


# 检索配置
MAX_HISTORY_EVENTS = 6  # 最多返回 6 条
MAX_AGE_DAYS = 30  # 最多考虑 30 天内的事件

# 去重阈值：相似度 >= 0.95 则去重
DEDUP_SIMILARITY_THRESHOLD = 0.95

# 事件类型 → 重要性映射（替代 LLM 判断的 importance，确保确定性）
IMPORTANCE_BY_TYPE: dict[str, float] = {
    "boundary":          0.90,  # 用户画的红线，绝不能忘
    "commitment":        0.80,  # 承诺约定，忘了会失信
    "identity":          0.70,  # 身份信息，长期稳定
    "preference":        0.55,  # 偏好，需要记住但不紧急
    "follow_up":         0.50,  # 跟进事项，有时效性
    "share_experience":  0.40,  # 经历分享
    "relation_change":   0.35,  # 关系变化
    "express_emotion":   0.30,  # 情绪表达
    "interaction":       0.25,  # 互动测试
    "other":             0.30,
}


def _calculate_content_similarity(content1: str, content2: str) -> float:
    """计算内容相似度（使用公共模块）"""
    return calc_jaccard_similarity(content1, content2)


def should_deduplicate(event1: MemoryEvent, event2: MemoryEvent) -> bool:
    """
    判断两个事件是否应该去重

    去重规则：
    - content 完全相同 → 去重
    - content 相似度 >= 0.95 → 去重
    - event_id 相同 → 去重（续写合并场景）

    Args:
        event1: 第一个事件
        event2: 第二个事件

    Returns:
        True 如果应该去重，False 否则
    """
    # 完全相同
    if event1.content == event2.content:
        return True

    # 相同 event_id（续写合并）
    if event1.event_id and event1.event_id == event2.event_id:
        return True

    # 相似度阈值去重
    similarity = _calculate_content_similarity(event1.content, event2.content)
    if similarity >= DEDUP_SIMILARITY_THRESHOLD:
        return True

    return False


def _dict_to_memory_event(event_dict: dict, content: str = None) -> MemoryEvent:
    """
    将字典转换为 MemoryEvent，处理字段别名和枚举安全转换

    Args:
        event_dict: 事件字典（来自 Redis 或 Chroma metadata）
        content: 可选的内容覆盖（当从不同来源获取时）

    Returns:
        MemoryEvent 对象
    """
    # 处理旧字段别名
    occurred_at = event_dict.get("occurred_at") or event_dict.get("time", "")
    last_seen_at = event_dict.get("last_seen_at") or event_dict.get("time", "")

    # 枚举安全转换
    actor_val = event_dict.get("actor", "UNKNOWN")
    try:
        actor = EventActor(actor_val)
    except ValueError:
        actor = EventActor.UNKNOWN

    event_type_val = event_dict.get("event_type", "other")
    try:
        event_type = EventDetailType(event_type_val)
    except ValueError:
        event_type = EventDetailType.OTHER

    type_val = event_dict.get("type", "event")
    try:
        event_type_enum = EventType(type_val)
    except ValueError:
        event_type_enum = EventType.EVENT

    return MemoryEvent(
        event_id=event_dict.get("event_id", ""),
        occurred_at=occurred_at,
        last_seen_at=last_seen_at,
        actor=actor,
        type=event_type_enum,
        event_type=event_type,
        content=content or event_dict.get("content", ""),
        keywords=event_dict.get("keywords", []),
        importance=event_dict.get("importance", 0.5),
        source_snippet=event_dict.get("source_snippet", ""),
        source_round=event_dict.get("source_round", 0),
        activity_score=event_dict.get("activity_score", 1.0),
    )


def deduplicate_with_recent_window(
    events: List[MemoryEvent],
    recent_messages: List[str],
) -> List[MemoryEvent]:
    """
    与最近窗口去重，避免 C 层和 D 层大段重复（任务 2.4）

    Args:
        events: 检索结果
        recent_messages: 最近窗口消息列表

    Returns:
        去重后的事件
    """
    if not recent_messages:
        return events

    # 提取最近窗口的关键词集合
    recent_keywords = set()
    for msg in recent_messages[-6:]:  # 最近 6 条消息
        recent_keywords.update(msg.split())

    deduplicated = []
    for event in events:
        event_keywords = set(event.content.split())

        # 计算与最近窗口的重叠度
        overlap = len(event_keywords & recent_keywords)
        overlap_ratio = overlap / max(len(event_keywords), 1)

        # 如果事件内容主要都在最近窗口中，则抑制
        if overlap_ratio >= 0.7:  # 70% 以上重叠
            logger.debug(f"【最近窗口去重】抑制高重叠事件: {event.content[:30]}...")
            continue

        deduplicated.append(event)

    return deduplicated


def format_history_events(events: List[MemoryEvent]) -> str:
    """
    格式化历史事件为 stable short text block

    V2升级：注入 actor + 中文 event_type 标签，让模型理解结构

    Args:
        events: MemoryEvent 列表

    Returns:
        格式化后的短文本，适合注入 relevant_memories
    """
    if not events:
        return ""

    lines = ["【相关历史事件】"]

    for event in events:
        # actor 标签
        actor_prefix = "用户" if event.actor == EventActor.USER else "角色"

        # event_type 中文标签
        event_type_str = event.event_type.value if event.event_type else "other"
        type_label = EVENT_TYPE_LABELS.get(event_type_str, "其他")

        # 格式：- [类型标签] actor内容
        event_line = f"- [{type_label}] {actor_prefix}{event.content}"

        # 如果有明确时间锚点，可选择性加上
        if event.occurred_at and len(event.occurred_at) >= 10:
            time_hint = event.occurred_at[:10]  # YYYY-MM-DD
            if time_hint != datetime.now().strftime("%Y-%m-%d"):
                event_line = f"- [{time_hint}] [{type_label}] {actor_prefix}{event.content}"

        lines.append(event_line)

    return "\n".join(lines)


# ============================================================
# 阶段5 V2升级：混合检索 + Rerank + activity_score排序
# ============================================================

def _bm25_retrieve_from_memory_bank(
    query: str,
    user_id: str,
    llm_id: str,
    max_results: int = 10,
    scope: Optional[List[str]] = None,
) -> List[MemoryEvent]:
    """
    BM25关键词召回（从memory_bank构建临时索引）

    使用标准 BM25 算法：IDF + 词频饱和 + 文档长度归一化
    参数：k1=1.5, b=0.75

    Args:
        query: 用户查询文本
        user_id: 用户ID
        llm_id: 模型ID
        max_results: 返回数量上限
        scope: 可选，event_type 过滤列表（如 ["follow_up", "commitment"]）

    Returns:
        MemoryEvent列表（按BM25分数排序，分数已归一化到 [0, 1]）
    """
    import jieba
    import math

    memory_bank_key = build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id)
    existing = redis_client.get(memory_bank_key)
    if not existing:
        return []

    memory_bank = safe_json_parse(existing, default=[], log_warning=False)
    if not memory_bank:
        return []

    # 查询分词
    query_terms = [t for t in jieba.cut(query) if len(t) > 1]
    if not query_terms:
        return []

    # ── 预处理：全库分词 + IDF ──
    N = len(memory_bank)
    doc_info: list[tuple[dict, list[str]]] = []  # [(event_dict, [tokens])]
    df: dict[str, int] = {}  # document frequency

    for event_dict in memory_bank:
        content = event_dict.get("content", "")
        if not content:
            doc_info.append((event_dict, []))
            continue
        tokens = [t for t in jieba.cut(content) if len(t) > 1]
        doc_info.append((event_dict, tokens))
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    # IDF: Robertson-Sparck Jones 平滑
    idf: dict[str, float] = {}
    for term, freq in df.items():
        idf[term] = math.log((N - freq + 0.5) / (freq + 0.5) + 1)

    # 未见词的 IDF（最大值）
    default_idf = math.log((N + 0.5) / 0.5 + 1)

    # 平均文档长度
    doc_lengths = [len(tokens) for _, tokens in doc_info if tokens]
    avgdl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0

    # BM25 超参
    k1 = 1.5
    b = 0.75

    candidates: list[MemoryEvent] = []

    for event_dict, tokens in doc_info:
        if not tokens:
            continue

        # scope 过滤：只检索指定 event_type
        if scope:
            event_type = event_dict.get("event_type", "other")
            if event_type not in scope:
                continue

        content = event_dict.get("content", "")
        doc_len = len(tokens)

        # 本文档词频
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        # 标准 BM25 累加
        score = 0.0
        for term in query_terms:
            term_idf = idf.get(term, default_idf)
            term_tf = tf.get(term, 0)
            if term_tf == 0:
                continue
            numerator = term_tf * (k1 + 1)
            denominator = term_tf + k1 * (1 - b + b * doc_len / avgdl)
            score += term_idf * numerator / denominator

        if score > 0:
            try:
                event = _dict_to_memory_event(event_dict, content)
                event._bm25_score = score
                candidates.append(event)
            except Exception as e:
                logger.debug(f"BM25事件转换失败: {e}")
                continue

    # 按分数排序，并归一化到 [0, 1]
    sorted_candidates = sorted(candidates, key=lambda e: e._bm25_score, reverse=True)
    if sorted_candidates:
        max_score = max(e._bm25_score for e in sorted_candidates)
        for e in sorted_candidates:
            e._bm25_score = e._bm25_score / max(max_score, 0.001)

    return sorted_candidates[:max_results]


async def _vector_retrieve_from_chroma(
    query: str,
    user_id: str,
    llm_id: str,
    max_results: int = 10,
    scope: Optional[List[str]] = None,
) -> List[MemoryEvent]:
    """
    向量语义检索（从Chroma事件库）

    V2新增：使用chroma_util.search_history_events
    V3新增：支持 event_type scope 过滤

    Args:
        query: 用户查询文本
        user_id: 用户ID
        llm_id: 模型ID
        max_results: 返回数量上限
        scope: 可选，event_type 过滤列表（如 ["follow_up", "commitment"]）

    Returns:
        MemoryEvent列表（按向量相似度排序）
    """
    # 构建 metadata 过滤条件
    filter_metadata = None
    if scope:
        filter_metadata = {"event_type": {"$in": scope}}

    documents = await search_history_events(
        query=query,
        user_id=user_id,
        llm_id=llm_id,
        filter_metadata=filter_metadata,
        k=max_results,
    )

    events = []
    for doc in documents:
        try:
            # 使用 metadata 作为字典，page_content 作为内容
            event = _dict_to_memory_event(doc.metadata, doc.page_content)
            # 使用 ChromaDB 返回的实际相似度分数
            event._vector_score = doc.metadata.get("_chroma_distance", 1.0)
            events.append(event)
        except Exception as e:
            logger.debug(f"向量事件转换失败: {e}")
            continue

    return events


def _is_generic_summary(content: str) -> bool:
    """
    判断内容是否为通用摘要（而非具体事件）

    V2排序规则：通用摘要应被具体事件优先替代

    判断标准：
    - 内容以"用户"、"角色"开头但缺乏具体行为描述
    - 包含大量泛化词汇如"提到了"、"讨论了"、"一般"
    - 无明确时间锚点或具体对象
    """
    generic_markers = ["提到了", "讨论了", "一般", "通常", "经常", "有时候", "偶尔"]
    specific_markers = ["承诺", "约定", "偏好", "边界", "决定", "选择", "要求", "拒绝"]

    # 通用摘要特征
    generic_count = sum(1 for m in generic_markers if m in content)
    # 具体事件特征
    specific_count = sum(1 for m in specific_markers if m in content)

    # 缺乏具体标记且有多条通用标记 -> 可能是摘要
    if generic_count >= 2 and specific_count == 0:
        return True

    # 内容过短且无具体信息
    if len(content) < 20 and specific_count == 0:
        return True

    return False


def _compute_specificity_bonus(event: MemoryEvent) -> float:
    """
    计算事件特异性加分（不含 event_type——该维度已移入 IMPORTANCE_BY_TYPE）

    加分规则：
    - 包含明确时间锚点：+0.05
    - 包含明确对象名：+0.05
    """
    bonus = 0.0

    # 时间锚点加分
    if event.occurred_at and len(event.occurred_at) >= 10:
        bonus += 0.05

    # 内容包含具体对象（非通用词）
    content = event.content
    specific_objects = ["用户", "角色", "我", "你"]
    has_specific_object = any(obj in content for obj in specific_objects)
    if has_specific_object and not _is_generic_summary(content):
        bonus += 0.05

    return bonus


def _merge_and_rank_candidates(
    bm25_events: List[MemoryEvent],
    vector_events: List[MemoryEvent],
    max_results: int = 8,
) -> List[MemoryEvent]:
    """
    合并并排序多路召回结果

    V2升级：显式排序规则优先具体事件而非通用摘要

    排序规则：
    1. 去重（完全相同才去重：content相同或event_id相同）
    2. 重要性基于 event_type 固定映射（不再依赖 LLM 判断的 importance）
    3. 综合分数 = 0.30*相关性 + 0.25*importance(event_type) + 0.15*freshness + 0.15*activity + 0.15*特异性
    4. 通用摘要惩罚：当存在高重要性事件时，摘要降权
    5. activity_score衰减：超过MAX_AGE_DAYS的事件按比例衰减

    Args:
        bm25_events: BM25召回结果
        vector_events: 向量召回结果
        max_results: 最终返回数量

    Returns:
        排序后的MemoryEvent列表
    """
    # 1. 合并去重（完全重复才去重）
    merged = []
    for event in bm25_events + vector_events:
        # 检查是否与已有事件重复
        is_duplicate = False
        for existing in merged:
            if should_deduplicate(event, existing):
                is_duplicate = True
                # 保留分数更高的版本
                existing_score = getattr(existing, "_bm25_score", 0) + getattr(existing, "_vector_score", 0)
                new_score = getattr(event, "_bm25_score", 0) + getattr(event, "_vector_score", 0)
                if new_score > existing_score:
                    merged.remove(existing)
                    merged.append(event)
                break
        if not is_duplicate:
            merged.append(event)

    candidates = merged

    # 2. 检测是否存在高重要性事件（替代旧的具体事件检测）
    def _get_importance(event: MemoryEvent) -> float:
        event_type_str = event.event_type.value if event.event_type else "other"
        return IMPORTANCE_BY_TYPE.get(event_type_str, 0.3)

    has_specific_events = any(
        _get_importance(e) >= 0.55 for e in candidates
    )

    # 3. 综合排序（importance 由 event_type 决定，不再依赖 LLM 判断）
    def compute_final_score(event: MemoryEvent) -> float:
        # 相关性分数（BM25 + vector 取均值，双路命中优于单路）
        bm25 = getattr(event, "_bm25_score", 0.0)
        vector = getattr(event, "_vector_score", 0.0)
        relevance = ((bm25 + vector) / 2.0) * 0.30

        # 重要性（event_type 固定映射，确定性强）
        importance = _get_importance(event) * 0.25

        # 新鲜度
        try:
            last_seen_time = datetime.fromisoformat(event.last_seen_at.replace("Z", "+00:00"))
            days_ago = (datetime.now() - last_seen_time).days
            freshness = max(0, (MAX_AGE_DAYS - days_ago) / MAX_AGE_DAYS) * 0.15
        except Exception:
            freshness = 0.0

        # activity_score（活跃度衰减）
        activity = event.activity_score * 0.15
        # 超过MAX_AGE_DAYS的事件应用额外衰减
        try:
            last_seen_time = datetime.fromisoformat(event.last_seen_at.replace("Z", "+00:00"))
            days_ago = (datetime.now() - last_seen_time).days
            if days_ago > MAX_AGE_DAYS:
                decay_factor = 1.0 - (days_ago - MAX_AGE_DAYS) / (MAX_AGE_DAYS * 2)
                decay_factor = max(0.1, decay_factor)
                activity *= decay_factor
        except Exception:
            pass

        # 特异性加分（仅含时间锚点 + 具体对象，不含 event_type）
        specificity = _compute_specificity_bonus(event) * 0.15

        # 通用摘要惩罚：当存在高重要性事件时，通用摘要降权
        if has_specific_events and _is_generic_summary(event.content):
            specificity -= 0.15  # 惩罚分数

        final_score = relevance + importance + freshness + activity + specificity
        return max(0, final_score)  # 确保分数非负

    sorted_candidates = sorted(candidates, key=compute_final_score, reverse=True)

    # 4. 排除低价值摘要（当存在高价值具体事件时）
    if has_specific_events:
        # 过滤掉分数过低的通用摘要
        filtered = []
        for event in sorted_candidates:
            if _is_generic_summary(event.content) and compute_final_score(event) < 0.3:
                logger.debug(f"【V2排序】排除低价值摘要: {event.content[:30]}...")
                continue
            filtered.append(event)
        sorted_candidates = filtered

    # 5. 预算控制
    return sorted_candidates[:max_results]


async def _rerank_candidates(
    query: str,
    events: List[MemoryEvent],
    top_k: int = 4,
) -> List[MemoryEvent]:
    """
    Rerank二次排序

    V2新增：使用FlashrankRerank对合并结果做相关性重估

    Args:
        query: 用户查询文本
        events: 合并后的候选事件
        top_k: 最终返回数量

    Returns:
        Rerank后的事件列表
    """
    if len(events) <= top_k:
        return events

    try:
        from langchain_community.document_compressors import FlashrankRerank
        from langchain_core.documents import Document

        # 转换为Document格式
        documents = [
            Document(page_content=event.content, metadata={"event_id": event.event_id})
            for event in events
        ]

        # FlashrankRerank
        reranker = FlashrankRerank(top_n=top_k)
        compressed = reranker.compress_documents(
            documents=documents,
            query=query,
        )

        # 按rerank结果还原MemoryEvent顺序
        reranked_ids = [doc.metadata.get("event_id") for doc in compressed]
        reranked_events = []
        for event_id in reranked_ids:
            for event in events:
                if event.event_id == event_id:
                    reranked_events.append(event)
                    break

        # 补充：如果有事件没被rerank返回但仍在top_k范围内
        remaining = [e for e in events if e not in reranked_events]
        while len(reranked_events) < top_k and remaining:
            reranked_events.append(remaining.pop(0))

        return reranked_events[:top_k]

    except Exception as e:
        logger.warning(f"Rerank失败: {e}, 使用原始排序")
        return events[:top_k]


async def retrieve_history_events_v2(
    query: str,
    user_id: str,
    llm_id: str,
    filter_metadata: Optional[Dict] = None,
    max_results: int = MAX_HISTORY_EVENTS,
    recent_messages: Optional[List[str]] = None,
    enable_rerank: bool = True,
    scope: Optional[List[str]] = None,
    top_k: Optional[int] = None,
) -> List[MemoryEvent]:
    """
    历史事件检索V2（阶段5）

    混合检索流程：
    1. BM25关键词召回（memory_bank）
    2. 向量语义检索（Chroma）
    3. 合并去重 + 综合排序（activity_score纳入）
    4. Rerank二次排序
    5. 与最近窗口去重
    6. 预算控制

    V3新增：支持 scope 过滤和动态 top_k

    Args:
        query: 用户查询文本
        user_id: 用户ID
        llm_id: 模型ID
        filter_metadata: 过滤条件
        max_results: 返回数量上限（默认）
        recent_messages: 最近窗口消息（用于去重）
        enable_rerank: 是否启用rerank
        scope: 可选，event_type 过滤列表
        top_k: 可选，动态 top_k（覆盖默认值）

    Returns:
        MemoryEvent列表（按综合相关性排序）
    """
    # 使用动态 top_k（如果提供）
    final_max_results = top_k if top_k is not None else max_results

    logger.info(f"【V2检索】开始混合检索: query={query[:30]}..., scope={scope}, top_k={final_max_results}")

    # 1. BM25召回
    bm25_events = _bm25_retrieve_from_memory_bank(
        query=query,
        user_id=user_id,
        llm_id=llm_id,
        max_results=10,
        scope=scope,
    )
    logger.debug(f"【V2检索】BM25召回: {len(bm25_events)} 条")

    # 2. 向量召回
    vector_events = await _vector_retrieve_from_chroma(
        query=query,
        user_id=user_id,
        llm_id=llm_id,
        max_results=10,
        scope=scope,
    )
    logger.debug(f"【V2检索】向量召回: {len(vector_events)} 条")

    # 3. 合并排序（activity_score纳入）
    merged_events = _merge_and_rank_candidates(
        bm25_events=bm25_events,
        vector_events=vector_events,
        max_results=final_max_results * 2,  # 给rerank留空间
    )
    logger.debug(f"【V2检索】合并后: {len(merged_events)} 条")

    # 4. Rerank
    if enable_rerank and len(merged_events) > final_max_results:
        merged_events = await _rerank_candidates(
            query=query,
            events=merged_events,
            top_k=final_max_results,
        )
        logger.debug(f"【V2检索】Rerank后: {len(merged_events)} 条")

    # 5. 与最近窗口去重
    if recent_messages:
        merged_events = deduplicate_with_recent_window(merged_events, recent_messages)

    # 6. 预算控制
    if len(merged_events) > final_max_results:
        merged_events = merged_events[:final_max_results]

    logger.info(f"【V2检索】最终返回: {len(merged_events)} 条")
    return merged_events