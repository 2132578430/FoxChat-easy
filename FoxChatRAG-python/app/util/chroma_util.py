import hashlib
from typing import List

import jieba
from flashrank import Ranker
from langchain_chroma import Chroma
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from app.chroma import CHROMA_MAP, easy_txt_splitter
from app.common.constant import ChromaTypeConstant
def _build_chroma_filter(metadata: dict | None) -> dict | None:
    """构建chroma过滤语法"""
    if not metadata:
        return None

    if len(metadata) == 1:
        return dict(metadata)

    return {
        "$and": [{key: value} for key, value in metadata.items()]
    }

async def delete(chroma_type: ChromaTypeConstant, **metadata):
    """删除元数据相关的chroma数据"""
    import asyncio
    chroma: Chroma = CHROMA_MAP[chroma_type]

    await asyncio.to_thread(
        lambda: chroma.delete(where=_build_chroma_filter(metadata))
    )

async def search(
    chroma_type: ChromaTypeConstant,
    msg_content: str,
    metadata: dict | None = None,
    limit: int = 5
) -> List[Document]:
    """
    根据消息和元数据获取chroma中的字段

    Args:
        chroma_type: 向量库类型
        msg_content: 检索文本
        metadata: 元数据过滤条件
        limit: 返回结果数量上限（默认5）
    """
    import time
    from loguru import logger

    chroma: Chroma = CHROMA_MAP[chroma_type]

    # 检查 collection 大小，为空则直接返回
    count = chroma._collection.count()
    logger.info(f"[PERF] collection count: {count}")
    if count == 0:
        logger.info("[PERF] collection 为空，跳过搜索")
        return []

    # 拆分计时：embedding vs chroma search
    t0 = time.time()
    embedding = chroma._embedding_function.embed_query(msg_content)
    t1 = time.time()
    logger.info(f"[PERF] embed_query: {t1 - t0:.3f}s")

    # 用预计算的 embedding 做搜索，避免重复调 API
    chroma_filter = _build_chroma_filter(metadata)
    results = chroma._collection.query(
        query_embeddings=[embedding],
        n_results=limit,  # ChromaDB 使用 n_results，不是 k
        where=chroma_filter,
    )
    t2 = time.time()
    logger.info(f"[PERF] chroma query: {t2 - t1:.3f}s, total: {t2 - t0:.3f}s")

    # 转换为 Document 列表，保留相似度分数
    documents = []
    if results and results['documents'] and results['documents'][0]:
        distances = results.get('distances', [[]])[0] if 'distances' in results else []
        for i, (doc_data, meta_data) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            # 将 L2 距离转为 0-1 相似度（归一化向量 L2 范围 [0, 2]）
            if i < len(distances):
                score = max(0.0, min(1.0, 1.0 - distances[i] / 2.0))
            else:
                score = 1.0
            meta_data = dict(meta_data) if meta_data else {}
            meta_data["_chroma_distance"] = score
            documents.append(Document(page_content=doc_data, metadata=meta_data))

    return documents

async def _split_chunk(documents: list[Document]) -> list[Document]:
    """
    对文档进行简单分段
    """
    documents: list[Document] = easy_txt_splitter.split_documents(documents)

    return documents

async def upload(chroma_type: ChromaTypeConstant, documents: list, source_id: str, **metadata):
    """
    # 向量库存入文档集合
    :param chroma_type: 向量数据库
    :param documents: 文档本体
    :param source_id: 文档唯一标识
    """
    chroma: Chroma = CHROMA_MAP[chroma_type]

    # 将消息唯一id的hash值作为id前缀，保证向量库存的文件不重复
    pre_id = hashlib.md5(source_id.encode('utf-8')).hexdigest()

    # 给每一个传入的文档添加元数据
    for document in documents:
        for key, value in metadata.items():
            document.metadata[key] = value
        # V2隔离：若未指定is_event，默认为False（summary类文档）
        if "is_event" not in document.metadata:
            document.metadata["is_event"] = False

    chroma.add_documents(
        documents,
        ids=[pre_id + str(i) for i in range(len(documents))],
    )


# 阶段4新增：历史事件向量库操作


async def upload_history_events_batch(
    events: List[dict],
    user_id: str,
    llm_id: str,
) -> int:
    """
    批量上传历史事件（性能优化：单次 embedding + 单次 HTTP）

    Args:
        events: 事件列表，每个事件包含完整的 metadata 字段
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        上传成功的事件数量
    """
    if not events:
        return 0

    documents = []
    ids = []

    for event in events:
        content = event.get("content", "")
        if not content:
            continue

        event_id = event.get("event_id", f"evt_{hashlib.md5(content.encode()).hexdigest()[:16]}")
        category = event.get("category", "event")

        doc = Document(
            page_content=content,
            metadata={
                "user_id": user_id,
                "llm_id": llm_id,
                "event_id": event_id,
                "actor": event.get("actor", "USER"),
                "type": event.get("type", "event"),
                "event_type": event.get("event_type", "other"),
                "importance": event.get("importance", 0.5),
                "keywords": event.get("keywords", []),
                "source_round": event.get("source_round", 0),
                "occurred_at": event.get("occurred_at", ""),
                "last_seen_at": event.get("last_seen_at", ""),
                "source_snippet": event.get("source_snippet", ""),
                "activity_score": event.get("activity_score", 1.0),
                "is_event": True,
                "category": category,
            }
        )
        documents.append(doc)
        ids.append(event_id)

    if not documents:
        return 0

    # 批量上传（单次 embedding 计算）
    chroma: Chroma = CHROMA_MAP[ChromaTypeConstant.CHAT]
    chroma.add_documents(documents, ids=ids)

    return len(documents)


async def upload_history_event(
    event_content: str,
    event_id: str,
    user_id: str,
    llm_id: str,
    actor: str,
    event_type: str,
    importance: float,
    keywords: List[str],
    source_round: int,
    occurred_at: str = "",
    last_seen_at: str = "",
    type: str = "event",
    source_snippet: str = "",
    activity_score: float = 1.0,
    category: str = "event",  # 新增：区分 state/event
) -> None:
    """
    上传历史事件到向量库（阶段4→wire-history-events-to-chroma补齐）

    Args:
        event_content: 事件内容文本
        event_id: 事件唯一标识
        user_id: 用户 ID
        llm_id: 模型 ID
        actor: 事件主体 (USER/AI)
        event_type: 事件细类
        importance: 重要程度
        keywords: 关键词列表
        source_round: 来源轮次
        occurred_at: 事件发生时间（ISO datetime）
        last_seen_at: 最近一次出现时间（用于续写合并）
        type: 事件大类 (event/state)
        source_snippet: 原文片段，防止摘要失真
        activity_score: 活性分数，后续支持事件衰减
        category: 记忆类型（state/event），用于区分身份偏好和具体事件
    """
    document = Document(
        page_content=event_content,
        metadata={
            "user_id": user_id,
            "llm_id": llm_id,
            "event_id": event_id,
            "actor": actor,
            "type": type,
            "event_type": event_type,
            "importance": importance,
            "keywords": keywords,
            "source_round": source_round,
            "occurred_at": occurred_at,
            "last_seen_at": last_seen_at,
            "source_snippet": source_snippet,
            "activity_score": activity_score,
            "is_event": True,  # 统一标记为 True，用 category 区分
            "category": category,  # 新增字段
        }
    )

    await upload(
        ChromaTypeConstant.CHAT,
        [document],
        event_id,
        user_id=user_id,
        llm_id=llm_id,
    )


async def search_history_events(
    query: str,
    user_id: str,
    llm_id: str,
    filter_metadata: dict | None = None,
    k: int = 5,
) -> List[Document]:
    """
    检索历史事件（阶段4）

    Args:
        query: 检索查询文本
        user_id: 用户 ID
        llm_id: 模型 ID
        filter_metadata: 额外的 metadata 过滤条件（如 actor, event_type）
        k: 返回数量上限

    Returns:
        事件 Document 列表（按相似度排序）
    """
    # 基础 metadata 过滤：用户+模型+事件标记
    base_metadata = {
        "user_id": user_id,
        "llm_id": llm_id,
        "is_event": True,
    }

    # 合并额外过滤条件
    if filter_metadata:
        base_metadata.update(filter_metadata)

    documents = await search(
        ChromaTypeConstant.CHAT,
        query,
        base_metadata,
        limit=k  # 传递检索数量限制
    )

    # 按重要性和时间排序后截取 top-k
    # 第一版先按相似度返回，后续可增加 importance 排序
    return documents[:k]
