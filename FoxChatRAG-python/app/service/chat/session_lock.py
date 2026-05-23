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
        - blocking=True: Wait until lock is available
    """
    key = f"session_lock:{user_id}:{llm_id}"

    lock = redis_lock.Lock(
        redis_client,
        key,
        expire=expire,
        auto_renewal=True,  # Watchdog auto-renewal
    )

    # blocking=True: wait until lock acquired
    lock.acquire(blocking=True)
    logger.debug(f"[SessionLock] Acquired: {key}")

    return lock


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