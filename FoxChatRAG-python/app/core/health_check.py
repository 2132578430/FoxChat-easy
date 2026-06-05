"""
Health Check Module — 中间件启动健康检查 & 指数退避重试

在应用启动时主动验证 MySQL / Redis / RabbitMQ 连接存活，
避免"懒加载"导致运行时第一个请求才炸雷。

Key behaviors:
- 指数退避重试（1s → 2s → 4s），最多 3 次重试（共 4 次尝试）
- 每次重试打 WARNING，最终失败打 ERROR 并抛出 ConnectionError
- 成功打 INFO，统一日志前缀 [HealthCheck]
"""

import asyncio
from typing import Any, Awaitable, Callable

from loguru import logger


async def retry_connect(
    name: str,
    connect_fn: Callable[[], Awaitable[Any]],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """
    尝试连接中间件，失败则指数退避重试。

    Args:
        name: 中间件名称（日志用，如 "Redis" / "MySQL" / "RabbitMQ"）
        connect_fn: 无参 async callable，成功返回任意值，失败抛异常
        max_retries: 最大重试次数（默认 3，含首次共 4 次尝试）
        base_delay: 首次重试前的等待秒数（之后每次翻倍）

    Returns:
        connect_fn 的返回值（通常是连接对象或 True）

    Raises:
        ConnectionError: 所有重试耗尽后仍失败
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            result = await connect_fn()
            logger.info(f"[HealthCheck] {name} 连接成功 ✅")
            return result
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
                logger.warning(
                    f"[HealthCheck] {name} 连接失败 "
                    f"(第 {attempt + 1}/{max_retries} 次重试，{delay:.0f}s 后重试): {e}"
                )
                await asyncio.sleep(delay)

    logger.error(
        f"[HealthCheck] {name} 不可用，{max_retries} 次重试后仍失败。"
        f"最后错误: {last_exception}"
    )
    raise ConnectionError(
        f"{name} 连接失败（{max_retries} 次重试后仍不可用）"
    ) from last_exception


async def check_redis():
    """PING Redis 验证连接存活。"""
    from app.core.db.redis_client import redis_client
    # redis_client.ping() 是同步调用，通过 to_thread 桥接到异步上下文
    result = await asyncio.to_thread(redis_client.ping)
    if not result:
        raise ConnectionError("Redis PING 返回非预期值")


async def check_mysql():
    """执行 SELECT 1 验证 MySQL 连接池可用。"""
    from sqlalchemy import text
    from app.core.db.mysql_client import async_session_local
    async with async_session_local() as session:
        await session.execute(text("SELECT 1"))
