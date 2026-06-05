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

    lock = acquire_session_lock(user_id, llm_id)
    try:
        # Process request sequentially
        ...
    finally:
        release_session_lock(lock)
"""

import redis
import redis_lock
from typing import Optional

from app.core.db.redis_client import redis_client
from loguru import logger


def acquire_session_lock(user_id: str, llm_id: str, expire: int = 60) -> redis_lock.Lock:
    """
    Acquire a distributed lock for the specified session.

    Args:
        user_id: User identifier
        llm_id: LLM/character identifier
        expire: Lock timeout in seconds (prevents deadlock if process crashes)

    Returns:
        redis_lock.Lock object (already acquired)

    Note:
        - expire=60: Lock auto-releases after 60s if process crashes
        - auto_renewal=True: Watchdog keeps renewing lock while process is alive
        - blocking=True with timeout=5: fast-fail for concurrent requests, avoids
          BLPOP hogging a Redis connection and triggering socket timeout
    """
    key = f"session_lock:{user_id}:{llm_id}"

    lock = redis_lock.Lock(
        redis_client,
        key,
        expire=expire,
        auto_renewal=True,  # Watchdog auto-renewal
    )

    try:
        # blocking=True + timeout=5:
        # - 正常情况：立刻拿到锁（上个请求已释放）
        # - 并发情况：等最多5s，拿不到则快速失败，避免 BLPOP 长时间占用连接导致 socket 超时
        acquired = lock.acquire(blocking=True, timeout=5)
        if not acquired:
            logger.warning(f"[SessionLock] 锁等待超时(5s)，可能存在并发请求: {key}")
            raise RuntimeError("会话正忙，请稍后再试")
        logger.debug(f"[SessionLock] Acquired: {key}")
        return lock
    except redis.exceptions.TimeoutError as e:
        logger.error(f"[SessionLock] Redis 连接超时: {key} — {e}")
        raise RuntimeError("服务暂时不可用，请稍后重试") from e
    except Exception as e:
        logger.error(f"[SessionLock] 获取锁失败: {key} — {e}")
        raise RuntimeError(f"会话锁获取失败，请稍后重试") from e


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
