"""
Session Lock Module (Distributed)

Provides distributed locking mechanism using Redis with watchdog auto-renewal.
Each session (user_id + llm_id combination) gets its own Redis lock,
guaranteeing that concurrent requests to the same session are processed in order
across multiple server instances.

Features:
- Distributed lock via Redis (works across multiple instances)
- Watchdog auto-renewal (lock won't expire while processing)
- Prevents deadlock with expire timeout

Usage:
    from app.service.chat.session_lock import acquire_session_lock, release_session_lock

    lock = await acquire_session_lock(user_id, llm_id)
    try:
        # Process request sequentially
        ...
    finally:
        release_session_lock(lock)
"""

import asyncio
import redis
import redis_lock
from typing import Optional

from app.core.db.redis_client import redis_client
from loguru import logger

# 单次 BLPOP 超时：10s（短轮询，避免长时间阻塞线程池中的线程）
# BLPOP 本身在线程池中执行，不阻塞事件循环
_POLL_INTERVAL = 10  # 秒


async def acquire_session_lock(user_id: str, llm_id: str, expire: int = 60) -> redis_lock.Lock:
    """
    Acquire a distributed lock for the specified session.

    This is an **async** function — the underlying Redis BLPOP is executed in a
    thread pool via asyncio.to_thread(), so it never blocks the asyncio event loop.

    Args:
        user_id: User identifier
        llm_id: LLM/character identifier
        expire: Lock timeout in seconds (prevents deadlock if process crashes)

    Returns:
        redis_lock.Lock object (already acquired)

    Note:
        - expire=60: Lock auto-releases after 60s if process crashes
        - auto_renewal=True: Watchdog keeps renewing lock while process is alive
        - BLPOP is run in a thread pool: acquire() blocks a thread, not the event loop
        - Short BLPOP poll interval (10s) prevents a single BLPOP from hogging a
          thread-pool thread when the lock holder takes a long time
    """
    key = f"session_lock:{user_id}:{llm_id}"

    lock = redis_lock.Lock(
        redis_client,
        key,
        expire=expire,
        auto_renewal=True,
    )

    waited = 0
    max_wait = 300  # 最多等 5 分钟

    while waited < max_wait:
        try:
            # 在线程池中执行同步 BLPOP，事件循环不受影响
            acquired = await asyncio.to_thread(
                lock.acquire, blocking=True, timeout=_POLL_INTERVAL
            )
            if acquired:
                if waited > 0:
                    logger.info(f"[SessionLock] Acquired after waiting {waited}s: {key}")
                else:
                    logger.debug(f"[SessionLock] Acquired: {key}")
                return lock
            waited += _POLL_INTERVAL
            logger.debug(f"[SessionLock] Still waiting ({waited}s): {key}")
        except redis.exceptions.TimeoutError:
            # BLPOP 在 thread 里被 Redis/TCP 层 timeout 中断 → 重试
            waited += _POLL_INTERVAL
            logger.warning(f"[SessionLock] Redis timeout after {waited}s, retrying: {key}")
            continue

    # 等了 5 分钟还拿不到 → 前一个请求大概率卡死了
    logger.error(f"[SessionLock] 等待超时({max_wait}s)，锁持有者可能已卡死: {key}")
    raise RuntimeError("会话正忙，请稍后再试")


def release_session_lock(lock: redis_lock.Lock) -> None:
    """
    Release the session lock.

    Args:
        lock: The lock object to release
    """
    try:
        lock.release()
        logger.debug(f"[SessionLock] Released")
    except Exception as e:
        logger.warning(f"[SessionLock] Release failed: {e}")
