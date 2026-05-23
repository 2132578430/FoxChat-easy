"""
历史事件向量索引闭环验证脚本

验证要点：
1. 新增持久化事件出现在 Chroma 中（任务 4.1）
2. 续写合并事件同步到 Chroma（任务 4.2）
3. V2 检索能返回索引的结构化事件（任务 4.3）

使用方式：
    python scripts/verify_history_event_indexing.py
"""

import asyncio
import json
from datetime import datetime

from loguru import logger

from app.common.constant.LLMChatConstant import build_memory_key, LLMChatConstant
from app.core.db.redis_client import redis_client
from app.util import chroma_util
from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.schemas.memory_event import MemoryEvent, EventActor, EventDetailType, EventType


# 测试常量
TEST_USER_ID = "test_user_event_indexing"
TEST_LLM_ID = "test_llm_event_indexing"


async def test_new_event_appears_in_chroma():
    """
    任务 4.1: 验证新增事件出现在 Chroma 中
    """
    logger.info("=" * 60)
    logger.info("【验证1】新增事件出现在 Chroma")
    logger.info("=" * 60)

    # 1. 清理测试数据
    memory_bank_key = build_memory_key(LLMChatConstant.MEMORY_BANK, TEST_USER_ID, TEST_LLM_ID)
    redis_client.delete(memory_bank_key)

    # 2. 创建测试事件
    test_event = MemoryEvent(
        event_id="evt_test_001",
        occurred_at=datetime.now().isoformat(),
        last_seen_at=datetime.now().isoformat(),
        actor=EventActor.USER,
        type=EventType.EVENT,
        event_type=EventDetailType.SHARE_EXPERIENCE,
        content="测试用户分享了考试压力的经历",
        keywords=["考试", "压力"],
        importance=0.8,
        source_snippet="我最近考试压力很大",
        source_round=1,
        activity_score=1.0,
    )

    # 3. 模拟持久化流程：写入 Redis + Chroma
    event_dict = test_event.model_dump()

    # 写入 memory_bank
    redis_client.set(memory_bank_key, json.dumps([event_dict], ensure_ascii=False))
    logger.info(f"✓ Redis memory_bank 写入成功: {test_event.event_id}")

    # 写入 Chroma
    await chroma_util.upload_history_event(
        event_content=test_event.content,
        event_id=test_event.event_id,
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        actor=test_event.actor.value,
        event_type=test_event.event_type.value,
        importance=test_event.importance,
        keywords=test_event.keywords,
        source_round=test_event.source_round,
        occurred_at=test_event.occurred_at,
        last_seen_at=test_event.last_seen_at,
        type=test_event.type.value,
        source_snippet=test_event.source_snippet,
        activity_score=test_event.activity_score,
    )
    logger.info(f"✓ Chroma 事件索引写入成功: {test_event.event_id}")

    # 4. 从 Chroma 检索验证
    documents = await chroma_util.search_history_events(
        query="考试压力",
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        k=5,
    )

    if documents:
        found = any(doc.metadata.get("event_id") == test_event.event_id for doc in documents)
        if found:
            logger.info(f"✓ Chroma 检索成功命中事件: {test_event.event_id}")
            logger.info(f"  检索返回 {len(documents)} 条结果")
            for doc in documents[:3]:
                logger.info(f"  - event_id: {doc.metadata.get('event_id', '')[:20]}")
                logger.info(f"    content: {doc.page_content[:50]}...")
                logger.info(f"    is_event: {doc.metadata.get('is_event')}")
                logger.info(f"    importance: {doc.metadata.get('importance')}")
                logger.info(f"    occurred_at: {doc.metadata.get('occurred_at', '')[:19]}")
            return True
        else:
            logger.warning(f"✗ Chroma 检索未命中目标事件")
            return False
    else:
        logger.warning(f"✗ Chroma 检索无结果")
        return False


async def test_continuation_merge_sync():
    """
    任务 4.2: 验证续写合并同步到 Chroma
    """
    logger.info("=" * 60)
    logger.info("【验证2】续写合并事件同步")
    logger.info("=" * 60)

    # 1. 创建初始事件
    original_event = MemoryEvent(
        event_id="evt_test_002",
        occurred_at=datetime.now().isoformat(),
        last_seen_at=datetime.now().isoformat(),
        actor=EventActor.USER,
        type=EventType.EVENT,
        event_type=EventDetailType.SHARE_EXPERIENCE,
        content="用户提到明天考试",
        keywords=["考试"],
        importance=0.7,
        source_round=2,
        activity_score=1.0,
    )

    # 2. 写入初始版本
    await chroma_util.upload_history_event(
        event_content=original_event.content,
        event_id=original_event.event_id,
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        actor=original_event.actor.value,
        event_type=original_event.event_type.value,
        importance=original_event.importance,
        keywords=original_event.keywords,
        source_round=original_event.source_round,
        occurred_at=original_event.occurred_at,
        last_seen_at=original_event.last_seen_at,
        type=original_event.type.value,
        source_snippet=original_event.source_snippet,
        activity_score=original_event.activity_score,
    )
    logger.info(f"✓ Chroma 初始事件写入: {original_event.event_id}")

    # 3. 模拟续写合并
    merged_content = f"{original_event.content} [续写] 考试结果出来了，考得还不错"
    merged_event_dict = original_event.model_dump()
    merged_event_dict["content"] = merged_content
    merged_event_dict["last_seen_at"] = datetime.now().isoformat()
    merged_event_dict["importance"] = 0.85  # 提升重要性
    merged_event_dict["keywords"] = ["考试", "结果"]

    # 4. 删除旧版本 + 写入新版本
    await chroma_util.delete(
        ChromaTypeConstant.CHAT,
        event_id=original_event.event_id,
    )
    logger.info(f"✓ Chroma 旧版本删除: {original_event.event_id}")

    await chroma_util.upload_history_event(
        event_content=merged_content,
        event_id=original_event.event_id,  # 使用同一 event_id
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        actor=merged_event_dict["actor"],
        event_type=merged_event_dict["event_type"],
        importance=merged_event_dict["importance"],
        keywords=merged_event_dict["keywords"],
        source_round=merged_event_dict["source_round"],
        occurred_at=merged_event_dict["occurred_at"],
        last_seen_at=merged_event_dict["last_seen_at"],
        type=merged_event_dict["type"],
        source_snippet=merged_event_dict.get("source_snippet", ""),
        activity_score=merged_event_dict["activity_score"],
    )
    logger.info(f"✓ Chroma 续写版本写入: {original_event.event_id}")

    # 5. 验证检索命中续写版本
    documents = await chroma_util.search_history_events(
        query="考试结果",
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        k=5,
    )

    if documents:
        found_doc = None
        for doc in documents:
            if doc.metadata.get("event_id") == original_event.event_id:
                found_doc = doc
                break

        if found_doc:
            logger.info(f"✓ Chroma 检索命中续写版本: {original_event.event_id}")
            logger.info(f"  content: {found_doc.page_content[:80]}...")
            logger.info(f"  importance: {found_doc.metadata.get('importance')} (提升后)")
            logger.info(f"  last_seen_at: {found_doc.metadata.get('last_seen_at', '')[:19]}")

            # 验证内容包含续写标记
            if "[续写]" in found_doc.page_content:
                logger.info(f"✓ 续写标记保留在 Chroma 文档中")
                return True
            else:
                logger.warning(f"✗ 续写标记未保留")
                return False
        else:
            logger.warning(f"✗ Chroma 检索未命中续写事件")
            return False
    else:
        logger.warning(f"✗ Chroma 检索无结果")
        return False


async def test_v2_retrieval_returns_indexed_events():
    """
    任务 4.3: 验证 V2 检索能返回索引的结构化事件
    """
    logger.info("=" * 60)
    logger.info("【验证3】V2 检索返回索引事件")
    logger.info("=" * 60)

    # 导入 V2 检索函数
    from app.service.chat.history_event_retrieval_service import retrieve_history_events_v2

    # 创建第三个测试事件
    test_event_3 = MemoryEvent(
        event_id="evt_test_003",
        occurred_at=datetime.now().isoformat(),
        last_seen_at=datetime.now().isoformat(),
        actor=EventActor.AI,
        type=EventType.EVENT,
        event_type=EventDetailType.COMMITMENT,
        content="AI承诺明天继续跟进考试情况",
        keywords=["承诺", "跟进"],
        importance=0.9,
        source_round=3,
        activity_score=1.0,
    )

    # 写入 Chroma
    await chroma_util.upload_history_event(
        event_content=test_event_3.content,
        event_id=test_event_3.event_id,
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        actor=test_event_3.actor.value,
        event_type=test_event_3.event_type.value,
        importance=test_event_3.importance,
        keywords=test_event_3.keywords,
        source_round=test_event_3.source_round,
        occurred_at=test_event_3.occurred_at,
        last_seen_at=test_event_3.last_seen_at,
        type=test_event_3.type.value,
        source_snippet=test_event_3.source_snippet,
        activity_score=test_event_3.activity_score,
    )
    logger.info(f"✓ Chroma 测试事件写入: {test_event_3.event_id}")

    # 调用 V2 检索
    events = await retrieve_history_events_v2(
        query="AI承诺跟进",
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        max_results=5,
        enable_rerank=False,  # 简化测试，不启用 rerank
    )

    if events:
        found = any(e.event_id == test_event_3.event_id for e in events)
        if found:
            logger.info(f"✓ V2 检索返回索引事件: {test_event_3.event_id}")
            logger.info(f"  检索返回 {len(events)} 条事件")
            for e in events[:3]:
                logger.info(f"  - event_id: {e.event_id}")
                logger.info(f"    content: {e.content[:50]}...")
                logger.info(f"    importance: {e.importance}")
                logger.info(f"    actor: {e.actor.value}")
            return True
        else:
            logger.warning(f"✗ V2 检索未命中目标事件")
            return False
    else:
        logger.warning(f"✗ V2 检索无结果")
        return False


async def main():
    """运行所有验证"""
    logger.info("\n" + "=" * 60)
    logger.info("历史事件向量索引闭环验证")
    logger.info("=" * 60 + "\n")

    results = {}

    # 验证1: 新增事件出现在 Chroma
    results["new_event_in_chroma"] = await test_new_event_appears_in_chroma()

    # 验证2: 续写合并同步
    results["continuation_merge_sync"] = await test_continuation_merge_sync()

    # 验证3: V2 检索返回索引事件
    results["v2_retrieval_indexed_events"] = await test_v2_retrieval_returns_indexed_events()

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("验证结果汇总")
    logger.info("=" * 60)
    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{name}: {status}")

    all_passed = all(results.values())
    if all_passed:
        logger.info("\n✓ 所有验证通过！事件向量索引闭环已完成。")
    else:
        logger.warning("\n✗ 部分验证失败，需检查实现。")

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())