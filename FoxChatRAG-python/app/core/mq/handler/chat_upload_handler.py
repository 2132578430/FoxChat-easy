import aio_pika
from loguru import logger

from app.service import chat_init

MAX_RETRY_COUNT = 3


def _get_retry_count(message: aio_pika.IncomingMessage) -> int:
    """
    从消息的 x-death header 中读取当前已重试次数。
    若 header 不存在或格式异常，返回 0（首次投递）。
    """
    headers = message.headers or {}
    x_death = headers.get("x-death")
    if not x_death or not isinstance(x_death, list):
        return 0
    # x-death[0]["count"] 表示该消息在最近一次死亡事件前的投递总次数
    first_death = x_death[0]
    if isinstance(first_death, dict):
        return int(first_death.get("count", 0))
    return 0


async def chat_upload_handler(message: aio_pika.IncomingMessage):
    """
    聊天记忆上传消费端。
    处理失败时根据 x-death 重试计数决定：
      - 重试 < 3 次 → nack(requeue=True) 重回队列
      - 重试 >= 3 次 → nack(requeue=False) 路由到死信队列
    """
    try:
        logger.info("接收到消费者队列消息，开始处理消息")
        await chat_init(message.body)
        await message.ack()
    except Exception as e:
        retry_count = _get_retry_count(message)
        logger.error(f"聊天记忆处理错误 (重试次数: {retry_count}/{MAX_RETRY_COUNT}): {e}", exc_info=True)

        if retry_count < MAX_RETRY_COUNT:
            await message.nack(requeue=True)
        else:
            logger.error(f"聊天记忆处理失败，已达最大重试次数，送入死信队列")
            await message.nack(requeue=False)