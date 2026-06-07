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
    lock_key = f"session_lock:{user_id}:{llm_id}"

    lock = redis_lock.Lock(
        redis_client,
        lock_key,
        expire=expire,
        auto_renewal=True,
    )

    waited = 0
    max_wait = 300  # 最多等 5 分钟

    # 等待锁被释放
    while waited < max_wait:
        try:
            # 在线程池中执行 BLPOP
            acquired = await asyncio.to_thread(
                lock.acquire, blocking=True, timeout=_POLL_INTERVAL
            )

            if acquired:
                return lock
                
            waited += _POLL_INTERVAL
        except redis.exceptions.TimeoutError:
            # BLPOP 在 thread 里被 Redis/TCP 层 timeout 中断 → 重试
            waited += _POLL_INTERVAL
            logger.warning(f"[SessionLock] Redis timeout after {waited}s, retrying: {lock_key}")
            continue

    # 等了 5 分钟还拿不到 → 前一个请求大概率卡死了
    logger.error(f"[SessionLock] 等待超时({max_wait}s) 锁卡死: {lock_key}")
    raise RuntimeError("会话正忙，请稍后再试")


def release_session_lock(lock: redis_lock.Lock) -> None:
    """
    释放会话锁
    """
    try:
        lock.release()
        logger.debug(f"[SessionLock] Released")
    except Exception as e:
        logger.warning(f"[SessionLock] Release failed: {e}")
