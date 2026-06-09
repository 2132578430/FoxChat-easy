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
from typing import List

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_chat_key
from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.common.constant.FileTypeConstant import FileTypeConstant
from app.core.db.redis_client import redis_client
from app.core.db.mysql_client import async_session_local
from app.core.prompts.prompt_manager import PromptManager
from app.service.chat.strategy.base_strategy import ExtractionInvokeStrategy, MemoryInvokeStrategy, SummaryInvokeStrategy
from app.util import loader_util, chroma_util
from app.util.template_util import escape_template, try_parse_json
from app.service.chat.profile.user_profile_service import update_user_profile_in_summary
from app.service.chat.common import safe_json_parse, calc_jaccard_similarity
from app.service.chat.memory.history_event_retrieval_service import IMPORTANCE_BY_TYPE

# 配置常量
MEMORY_BANK_MAX_SIZE = 50
MEMORY_BANK_COMPRESS_TARGET = 30
RECENT_MSG_KEEP_SIZE = 10
SUMMARY_TRIGGER_THRESHOLD = 18

# 去重配置
DEDUP_CHECK_WINDOW = 20  # 检查最近20条
DEDUP_SIMILARITY_THRESHOLD = 0.6  # 内容相似度阈值


# ============================================================
# 工具函数
# ============================================================

def _load_event_list(raw_text: str) -> List[dict]:
    """解析事件列表

    期望格式 {"events": [...]}，与 response_format=json_object 约束对齐。
    也兼容 LLM 将内层数组序列化为字符串的情况 {"events": "[...]"}。
    """
    data = try_parse_json(raw_text)

    # 解包 events 字段
    if isinstance(data, dict) and "events" in data:
        events = data["events"]
        if isinstance(events, str):
            events = try_parse_json(events)
    else:
        events = data

    if not isinstance(events, list):
        raise json.JSONDecodeError("事件列表格式错误", raw_text, 0)
    return events


def _get_memory_bank(user_id: str, llm_id: str) -> List[dict]:
    """获取 memory_bank"""
    key = build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.MEMORY_BANK)
    existing = redis_client.get(key)
    return safe_json_parse(existing, default=[], log_warning=False)


def _save_memory_bank(memory_bank: List[dict], user_id: str, llm_id: str) -> None:
    """保存 memory_bank"""
    key = build_chat_key(LLMChatConstant.CHAT_MEMORY, user_id, llm_id, LLMChatConstant.MEMORY_BANK)
    redis_client.set(key, json.dumps(memory_bank, ensure_ascii=False))


# ============================================================
# 公共辅助函数
# ============================================================

_SCENARIO_STRATEGY = {
    "extraction": ExtractionInvokeStrategy,
    "memory": MemoryInvokeStrategy,
    "summary": SummaryInvokeStrategy,
}


def _get_strategy(scenario: str):
    """根据场景获取 strategy 实例（替掉 _build_chain 的策略映射）"""
    cls = _SCENARIO_STRATEGY.get(scenario, ExtractionInvokeStrategy)
    return cls()


async def _get_llm_config(llm_id: str, db=None) -> dict:
    """获取 LLM 配置（提取 3 处重复的 config_map 获取逻辑）"""
    from app.service.llm_config_service import get_llm_configs_batch
    if not llm_id:
        return {}
    if db:
        return await get_llm_configs_batch(llm_id, db)
    async with async_session_local() as session:
        return await get_llm_configs_batch(llm_id, session)


async def _invoke_with_prompt(
    prompt_name: str,
    variables: list[str],
    user_content: str,
    strategy,
    config_map: dict,
) -> str:
    """
    统一的 prompt 获取 → escape → 拼 messages → invoke

    Args:
        prompt_name: Prompt 文件名称
        variables: 需要转义的变量列表
        user_content: Human 消息内容
        strategy: LLMInvokeStrategy 实例
        config_map: LLM 配置字典

    Returns:
        LLM 响应文本
    """
    prompt_text = await PromptManager.get_prompt(prompt_name)
    prompt_text = escape_template(prompt_text, variables)
    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": user_content},
    ]
    return await strategy.invoke(messages, config_map)


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
    strategy = _get_strategy("extraction")
    config_map = await _get_llm_config(llm_id, db)
    result = await _invoke_with_prompt(
        "memory_event_extractor.md",
        ["input_content"],
        f"Extract structured memory events from this conversation:\n{chat_history}",
        strategy,
        config_map,
    )

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
            # 统一分类器覆盖 event_type：消除 LLM 判断与检索 scope 的不一致
            content = event.get("content", "")
            if content:
                from app.service.chat.llm.intent_classifier import classify_event_type
                event["event_type"] = classify_event_type(content)
            # 覆盖 LLM 生成的 event_id，防止跨轮次 ID 碰撞导致 ChromaDB upsert 覆盖
            content_hash = hashlib.md5(event.get("content", "").encode()).hexdigest()[:12]
            event["event_id"] = f"evt_{ts}_{i}_{content_hash}"
        return events
    except json.JSONDecodeError as e:
        logger.warning(f"事件提取 JSON 解析失败: {e}; 原始输出: {result}")
        return []


# ============================================================
# 去重判断
# ============================================================

def _check_duplicate(
    new_event: dict,
    existing_events: List[dict]
) -> bool:
    """
    检查新事件是否与已有事件重复（短窗口 Jaccard 相似度去重）

    Returns:
        True 如果判定为重复应丢弃，False 否则
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
        similarity = calc_jaccard_similarity(new_content, existing_content)
        if similarity >= DEDUP_SIMILARITY_THRESHOLD:
            logger.debug(f"【事件去重】跳过（相似度 {similarity:.2f}): {new_content[:30]}...")
            return True

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
    for new_event in new_events:
        if _check_duplicate(new_event, memory_bank):
            continue
        deduplicated.append(new_event)

    if not deduplicated:
        return

    # 更新 Redis
    memory_bank.extend(deduplicated)
    _save_memory_bank(memory_bank, user_id, llm_id)
    logger.info(f"【历史事件入库】新增 {len(deduplicated)} 条")

    # 同步新增事件到 Chroma（批量上传优化）
    await chroma_util.upload_history_events_batch(deduplicated, user_id, llm_id)


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

    # 补全 importance 字段：如果事件没有 importance，根据 event_type 映射
    for event in memory_bank:
        if "importance" not in event or event["importance"] is None:
            event_type = event.get("event_type", "other")
            event["importance"] = IMPORTANCE_BY_TYPE.get(event_type, 0.30)

    # 提取高重要性事件（importance >= 0.7），必须在压缩结果中原样保留
    pinned_events = [e for e in memory_bank if e.get("importance", 0) >= 0.70]
    pinned_json = json.dumps(pinned_events, ensure_ascii=False, indent=2) if pinned_events else "（无高重要性事件）"
    if pinned_events:
        logger.info(f"memory_bank 压缩: 锚定 {len(pinned_events)} 条高重要性事件 (importance>=0.7)")

    prompt_str = await PromptManager.get_prompt("memory_bank_compress")
    prompt_str = escape_template(prompt_str, ["target_size", "memory_bank_json", "pinned_events_json"])

    # 构建 messages
    messages = [
        {"role": "user", "content": prompt_str.format(
            target_size=MEMORY_BANK_COMPRESS_TARGET,
            memory_bank_json=json.dumps(memory_bank, ensure_ascii=False, indent=2),
            pinned_events_json=pinned_json,
        )}
    ]

    # 使用 Memory 策略
    strategy = _get_strategy("memory")
    config_map = await _get_llm_config(llm_id, db)
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
    chat_history = "\n".join(recent_msg_list)
    strategy = _get_strategy("summary")
    config_map = await _get_llm_config(llm_id, db)
    summary = await _invoke_with_prompt(
        "memory_summary",
        ["recent_msg_list"],
        f"The chat history between the user and the role currently played by the AI is:\n{chat_history}",
        strategy,
        config_map,
    )

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
    lock_key = build_chat_key(LLMChatConstant.SUMMARY_LOCK, user_id, llm_id)

    # 尝试获取锁（60s超时）
    if not redis_client.set(lock_key, "1", nx=True, ex=60):
        # 锁被占用 → 队列计数
        counter_key = build_chat_key(LLMChatConstant.SUMMARY_COUNTER, user_id, llm_id)
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
    counter_key = build_chat_key(LLMChatConstant.SUMMARY_COUNTER, user_id, llm_id)

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
        from app.service.chat.memory.timer_scheduler import reset_timer
        reset_timer(user_id, llm_id)

        counter = int(redis_client.get(counter_key) or 0)
        if counter > 0:
            redis_client.decr(counter_key)
        else:
            redis_client.delete(counter_key)
            break