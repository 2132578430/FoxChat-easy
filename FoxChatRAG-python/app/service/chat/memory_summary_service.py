"""
记忆总结服务模块

职责：
- 18轮对话后的消息总结（存入向量数据库）
- 从对话中提取关键事件（存入 Memory Bank）
- Memory Bank 压缩（超过阈值时触发）
- 用户画像更新（在总结流程中调用）

重构说明：
- 使用策略层替代硬编码的 get_extraction_model(), get_memory_model()
- 所有函数需要传入 llm_id 和 db 参数以查询用户配置
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import List, Tuple, Optional

from langchain_core.documents import Document
from loguru import logger

from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.common.constant.FileTypeConstant import FileTypeConstant
from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core.db.redis_client import redis_client
from app.core.db.mysql_client import async_session_local
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.strategy.base_strategy import ExtractionInvokeStrategy, MemoryInvokeStrategy, SummaryInvokeStrategy
from app.util import loader_util, chroma_util
from app.util.template_util import escape_template, try_parse_json
from app.service.chat.user_profile_service import update_user_profile_in_summary
from app.service.chat.common import safe_json_parse, calc_jaccard_similarity

# 配置常量
MEMORY_BANK_MAX_SIZE = 50
MEMORY_BANK_COMPRESS_TARGET = 30
RECENT_MSG_KEEP_SIZE = 10
SUMMARY_TRIGGER_THRESHOLD = 18

# 去重配置
DEDUP_CHECK_WINDOW = 20  # 检查最近20条
DEDUP_SIMILARITY_THRESHOLD = 0.6  # 内容相似度阈值
PROGRESS_KEYWORDS = ["后来", "结果", "还是", "已经", "最后", "终于", "完成了", "解决了"]


# ============================================================
# 工具函数
# ============================================================

def _load_event_list(raw_text: str) -> List[dict]:
    """解析事件列表"""
    events = try_parse_json(raw_text)
    if events is None or not isinstance(events, list):
        raise json.JSONDecodeError("event payload is not a valid list", raw_text, 0)
    return events


def _get_memory_bank(user_id: str, llm_id: str) -> List[dict]:
    """获取 memory_bank"""
    key = build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id)
    existing = redis_client.get(key)
    return safe_json_parse(existing, default=[], log_warning=False)


def _save_memory_bank(memory_bank: List[dict], user_id: str, llm_id: str) -> None:
    """保存 memory_bank"""
    key = build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id)
    redis_client.set(key, json.dumps(memory_bank, ensure_ascii=False))


# ============================================================
# LLM Chain 构建
# ============================================================

async def _build_chain(prompt_name: str, variables: List[str], human_template: str, llm_id: str = None, db = None, scenario: str = "extraction"):
    """
    通用 Chain 构建器（使用策略层）

    Args:
        prompt_name: Prompt 名称
        variables: 需要转义的变量列表
        human_template: Human 模板
        llm_id: AI 朋友 ID（用于查询配置）
        db: 数据库会话
        scenario: 场景名称（默认 extraction）

    Returns:
        Chain 对象（已废弃，现在返回 (template, strategy) 供直接调用）
    """
    from langchain_core.prompts import ChatPromptTemplate

    prompt_str = await PromptManager.get_prompt(prompt_name)
    prompt_str = escape_template(prompt_str, variables)
    template = ChatPromptTemplate([
        ("system", prompt_str),
        ("human", human_template)
    ])

    # 返回 template 和 strategy（不再使用 LangChain chain）
    if scenario == "extraction":
        strategy = ExtractionInvokeStrategy()
    elif scenario == "memory":
        strategy = MemoryInvokeStrategy()
    elif scenario == "summary":
        strategy = SummaryInvokeStrategy()
    else:
        strategy = ExtractionInvokeStrategy()

    return template, strategy


async def _build_summary_chain(llm_id: str = None, db = None):
    """构建消息总结 Chain（使用策略层）"""
    return await _build_chain(
        "memory_summary",
        ["recent_msg_list"],
        "The chat history between the user and the role currently played by the AI is: {chat_history_msg}",
        llm_id=llm_id,
        db=db,
        scenario="summary"
    )


async def _build_event_extractor_chain(llm_id: str = None, db = None):
    """构建事件提取 Chain（使用策略层）"""
    return await _build_chain(
        "memory_event_extractor.md",
        ["input_content"],
        "Extract structured memory events from this conversation:\n{input_content}",
        llm_id=llm_id,
        db=db,
        scenario="extraction"
    )


# ============================================================
# 事件提取
# ============================================================

async def _extract_memory_events(recent_msg_list: List[str], llm_id: str = None, db = None) -> List[dict]:
    """
    从对话历史中提取关键事件（使用策略层）

    Args:
        recent_msg_list: 最近消息列表
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        事件列表
    """
    if not recent_msg_list:
        return []

    chat_history = "\n".join(recent_msg_list)
    template, strategy = await _build_event_extractor_chain(llm_id, db)

    # 构建 messages
    prompt_text = await PromptManager.get_prompt("memory_event_extractor.md")
    prompt_text = escape_template(prompt_text, ["input_content"])

    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": f"Extract structured memory events from this conversation:\n{chat_history}"}
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

    result = await strategy.invoke(messages, config_map)

    try:
        events = _load_event_list(result)
        current_time = datetime.now().strftime("%Y-%m-%d")
        ts = datetime.now().strftime("%H%M%S%f")  # 微秒精度时间戳，防碰撞
        for i, event in enumerate(events):
            event["occurred_at"] = current_time
            event["last_seen_at"] = current_time
            if "time" in event:
                del event["time"]
            if "actor" not in event or not event["actor"]:
                event["actor"] = "UNKNOWN"
            if "keywords" not in event:
                event["keywords"] = []
            # 覆盖 LLM 生成的 event_id，防止跨轮次 ID 碰撞导致 ChromaDB upsert 覆盖
            content_hash = hashlib.md5(event.get("content", "").encode()).hexdigest()[:12]
            event["event_id"] = f"evt_{ts}_{i}_{content_hash}"
        return events
    except json.JSONDecodeError as e:
        logger.warning(f"事件提取 JSON 解析失败: {e}; 原始输出: {result}")
        return []


# ============================================================
# 去重与续写判断
# ============================================================

def _calc_content_similarity(content1: str, content2: str) -> float:
    """计算内容相似度（使用公共模块）"""
    return calc_jaccard_similarity(content1, content2)


def _check_duplicate_or_continuation(
    new_event: dict,
    existing_events: List[dict]
) -> Tuple[bool, bool, Optional[dict]]:
    """
    检查去重或续写

    Returns:
        (is_duplicate, is_continuation, merge_target)
    """
    new_actor = new_event.get("actor", "UNKNOWN")
    new_event_type = new_event.get("event_type", "other")
    new_content = new_event.get("content", "")

    for existing in existing_events[-DEDUP_CHECK_WINDOW:]:
        # 同桶判断
        if existing.get("actor", "UNKNOWN") != new_actor:
            continue
        if existing.get("event_type", "other") != new_event_type:
            continue

        existing_content = existing.get("content", "")

        # 短窗重复判断
        similarity = _calc_content_similarity(new_content, existing_content)
        if similarity >= DEDUP_SIMILARITY_THRESHOLD:
            logger.debug(f"【事件去重】跳过（相似度 {similarity:.2f}): {new_content[:30]}...")
            return True, False, None

        # 长窗续写判断
        has_progress = any(kw in new_content for kw in PROGRESS_KEYWORDS)
        if has_progress and existing_content:
            overlap = len(set(new_content.split()) & set(existing_content.split()))
            if overlap >= 1:
                logger.debug(f"【事件续写】合并: {new_content[:30]}...")
                return False, True, existing

    return False, False, None


def _merge_continuation_event(target: dict, new_event: dict) -> None:
    """续写合并：更新目标事件"""
    target["content"] = f"{target.get('content', '')} [续写] {new_event.get('content', '')}"
    target["last_seen_at"] = new_event.get("time", "")
    target["importance"] = max(target.get("importance", 0.5), new_event.get("importance", 0.5))
    target["activity_score"] = max(target.get("activity_score", 1.0), new_event.get("activity_score", 1.0))
    if "keywords" in new_event:
        merged = list(set(target.get("keywords", []) + new_event["keywords"]))
        target["keywords"] = merged[:5]


# ============================================================
# Chroma 同步
# ============================================================

async def _sync_event_to_chroma(event: dict, user_id: str, llm_id: str) -> bool:
    """同步单个事件到 Chroma"""
    try:
        await chroma_util.upload_history_event(
            event_content=event.get("content", ""),
            event_id=event.get("event_id", ""),
            user_id=user_id,
            llm_id=llm_id,
            actor=event.get("actor", "UNKNOWN"),
            event_type=event.get("event_type", "other"),
            importance=event.get("importance", 0.5),
            keywords=event.get("keywords", []),
            source_round=event.get("source_round", 0),
            occurred_at=event.get("occurred_at", ""),
            last_seen_at=event.get("last_seen_at", ""),
            type=event.get("type", "event"),
            source_snippet=event.get("source_snippet", ""),
            activity_score=event.get("activity_score", 1.0),
            category=event.get("category", "event"),  # 新增 category
        )
        return True
    except Exception as e:
        logger.warning(f"【Chroma同步】失败: {event.get('event_id', '')[:30]}, error={e}")
        return False


async def _sync_merged_event_to_chroma(event_id: str, event: dict, user_id: str, llm_id: str) -> bool:
    """同步续写合并事件到 Chroma（删除旧版本+重写）"""
    try:
        await chroma_util.delete(ChromaTypeConstant.CHAT, event_id=event_id)
        await _sync_event_to_chroma(event, user_id, llm_id)
        return True
    except Exception as e:
        logger.warning(f"【Chroma续写同步】失败: {event_id[:30]}, error={e}")
        return False


# ============================================================
# 去重追加主流程
# ============================================================

async def _deduplicate_and_append_events(
    new_events: List[dict],
    user_id: str,
    llm_id: str,
) -> None:
    """去重并追加事件"""
    memory_bank = _get_memory_bank(user_id, llm_id)

    deduplicated = []
    merged_ids = []

    for new_event in new_events:
        is_dup, is_cont, target = _check_duplicate_or_continuation(new_event, memory_bank)

        if is_dup:
            continue

        if is_cont and target:
            _merge_continuation_event(target, new_event)
            if target.get("event_id"):
                merged_ids.append(target["event_id"])
        else:
            deduplicated.append(new_event)

    # 更新 Redis
    if deduplicated:
        memory_bank.extend(deduplicated)
        _save_memory_bank(memory_bank, user_id, llm_id)
        logger.info(f"【历史事件入库】新增 {len(deduplicated)} 条")

        # 同步新增事件到 Chroma（批量上传优化）
        await chroma_util.upload_history_events_batch(deduplicated, user_id, llm_id)

    # 同步续写合并事件
    if merged_ids:
        for event_id in merged_ids:
            for event in memory_bank[-DEDUP_CHECK_WINDOW:]:
                if event.get("event_id") == event_id:
                    await _sync_merged_event_to_chroma(event_id, event, user_id, llm_id)
                    break


# ============================================================
# Memory Bank 压缩
# ============================================================

async def _compress_memory_bank_if_needed(user_id: str, llm_id: str, db = None) -> None:
    """
    检查并压缩 Memory Bank（使用策略层）

    Args:
        user_id: 用户 ID
        llm_id: AI 朋友 ID
        db: 数据库会话
    """
    memory_bank = _get_memory_bank(user_id, llm_id)
    if len(memory_bank) < MEMORY_BANK_MAX_SIZE:
        return

    logger.info(f"memory_bank 压缩触发: {len(memory_bank)} 条")

    prompt_str = await PromptManager.get_prompt("memory_bank_compress")
    prompt_str = escape_template(prompt_str, ["target_size", "memory_bank_json"])

    # 构建 messages
    messages = [
        {"role": "user", "content": prompt_str.format(
            target_size=MEMORY_BANK_COMPRESS_TARGET,
            memory_bank_json=json.dumps(memory_bank, ensure_ascii=False, indent=2),
        )}
    ]

    # 使用 Memory 策略
    strategy = MemoryInvokeStrategy()

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

    result = await strategy.invoke(messages, config_map)

    try:
        compressed = json.loads(result)
        _save_memory_bank(compressed, user_id, llm_id)
        logger.info(f"memory_bank 压缩完成: {len(memory_bank)} → {len(compressed)}")
    except json.JSONDecodeError:
        logger.warning("memory_bank 压缩 JSON 解析失败")


# ============================================================
# 事件处理全链
# ============================================================

async def _extract_compress_events(recent_msg_list: List[str], user_id: str, llm_id: str, db = None) -> None:
    """事件处理：提取 → 追加 → 压缩"""
    events = await _extract_memory_events(recent_msg_list, llm_id, db)
    if not events:
        logger.info("[Event Task] 未提取到事件")
        return

    await _deduplicate_and_append_events(events, user_id, llm_id)
    await _compress_memory_bank_if_needed(user_id, llm_id, db)


# ============================================================
# Summary 生成（纯文本上传，不再做结构化提取）
# ============================================================

async def _summary_and_upload(recent_msg_list: List[str], user_id: str, llm_id: str, db = None) -> str:
    """
    生成对话摘要文本并上传（使用策略层）

    Args:
        recent_msg_list: 最近消息列表
        user_id: 用户 ID
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        摘要文本
    """
    template, strategy = await _build_summary_chain(llm_id, db)

    # 构建 messages
    prompt_text = await PromptManager.get_prompt("memory_summary")
    prompt_text = escape_template(prompt_text, ["recent_msg_list"])

    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": f"The chat history between the user and the role currently played by the AI is:\n{'\n'.join(recent_msg_list)}"}
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

    summary = await strategy.invoke(messages, config_map)

    # 纯文本直接上传
    docs = loader_util.load_file(summary, FileTypeConstant.STR)
    await chroma_util.upload(
        ChromaTypeConstant.CHAT,
        docs,
        user_id + llm_id + summary,
        user_id=user_id,
        llm_id=llm_id,
    )
    logger.info(f"【Summary】写入对话摘要")
    return summary


# ============================================================
# 并发总结主流程
# ============================================================

async def async_summary_msg_parallel(recent_msg_key: str, recent_msg_size: int, user_id: str, llm_id: str, db = None) -> None:
    """
    并发执行总结任务（使用策略层）

    Args:
        recent_msg_key: Redis key
        recent_msg_size: 消息数量
        user_id: 用户 ID
        llm_id: AI 朋友 ID
        db: 数据库会话
    """
    if recent_msg_size < SUMMARY_TRIGGER_THRESHOLD:
        return

    # 获取并裁剪消息
    pip = redis_client.pipeline()
    pip.lrange(recent_msg_key, RECENT_MSG_KEEP_SIZE, -1)
    pip.ltrim(recent_msg_key, 0, RECENT_MSG_KEEP_SIZE - 1)
    result = pip.execute()

    msg_list = result[0]
    msg_list.reverse()
    logger.debug(f"记忆总结: 处理 {len(msg_list)} 条, 保留 {RECENT_MSG_KEEP_SIZE} 条")

    # 并发执行
    await asyncio.gather(
        _summary_and_upload(msg_list, user_id, llm_id, db),
        _extract_compress_events(msg_list, user_id, llm_id, db),
        update_user_profile_in_summary(user_id, llm_id, msg_list, db),  # TODO: 也需要添加 db 参数
    )
    logger.info("【并发总结】完成")


# ============================================================
# Hybrid Trigger: 分布式锁 + 计数器队列
# ============================================================

async def trigger_summary_with_counter(
    recent_msg_key: str,
    recent_msg_size: int,
    user_id: str,
    llm_id: str,
    trigger_source: str
) -> None:
    """触发器入口（带分布式锁）"""
    lock_key = f"summary_lock:{user_id}:{llm_id}"

    # 尝试获取锁（60s超时）
    if not redis_client.set(lock_key, "1", nx=True, ex=60):
        # 锁被占用 → 队列计数
        counter_key = f"summary_counter:{user_id}:{llm_id}"
        redis_client.incr(counter_key)
        redis_client.expire(counter_key, 300)
        logger.info(f"[{trigger_source}] Lock held, queued")
        return

    try:
        await execute_summary_loop(recent_msg_key, user_id, llm_id, trigger_source)
    finally:
        redis_client.delete(lock_key)


async def execute_summary_loop(
    recent_msg_key: str,
    user_id: str,
    llm_id: str,
    trigger_source: str
) -> None:
    """执行总结循环（处理队列任务）"""
    counter_key = f"summary_counter:{user_id}:{llm_id}"

    while True:
        size = redis_client.llen(recent_msg_key)

        if size < SUMMARY_TRIGGER_THRESHOLD:
            counter = int(redis_client.get(counter_key) or 0)
            if counter > 0:
                redis_client.decr(counter_key)
                continue
            else:
                redis_client.delete(counter_key)
                break

        logger.info(f"[{trigger_source}] 开始总结: {size} 条")
        await async_summary_msg_parallel(recent_msg_key, size, user_id, llm_id)

        # 重置定时器
        from app.service.chat.timer_scheduler import reset_timer
        reset_timer(user_id, llm_id)

        counter = int(redis_client.get(counter_key) or 0)
        if counter > 0:
            redis_client.decr(counter_key)
        else:
            redis_client.delete(counter_key)
            break