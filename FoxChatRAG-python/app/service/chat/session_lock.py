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

# BLPOP 等待锁期间，每隔 POLL_INTERVAL 秒检查一次连接健康
# 避免单次 BLPOP 长时间占用连接导致 Redis 服务端/代理层关闭空闲连接
_POLL_INTERVAL = 10  # 秒


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
        - 采用短 BLPOP 轮询代替单次长 BLPOP，避免 Redis 连接在等待期间
          被服务端/代理层（如 Nginx stream、AWS NLB）因 idle timeout 断开
    """
    key = f"session_lock:{user_id}:{llm_id}"

    lock = redis_lock.Lock(
        redis_client,
        key,
        expire=expire,
        auto_renewal=True,
    )

    waited = 0
    max_wait = 300  # 最多等 5 分钟（正常 LLM 调用不可能超过这个时间）

    while waited < max_wait:
        try:
            acquired = lock.acquire(blocking=True, timeout=_POLL_INTERVAL)
            if acquired:
                if waited > 0:
                    logger.info(f"[SessionLock] Acquired after waiting {waited}s: {key}")
                else:
                    logger.debug(f"[SessionLock] Acquired: {key}")
                return lock
            waited += _POLL_INTERVAL
            logger.debug(f"[SessionLock] Still waiting ({waited}s): {key}")
        except redis.exceptions.TimeoutError:
            # BLPOP 被 Redis/TCP 层 timeout 打断 — 重新尝试
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
