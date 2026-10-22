import aio_pika
from loguru import logger

from app.service import chat_init


async def chat_upload_handler(message: aio_pika.IncomingMessage):
    """
    模型初始化消息消费端。

    成功 → ack；失败 → nack 进入死信队列，仅供排查。
    失败状态由 chat_init 写入 isApply=3，用户可通过 /llm/activate 手动重试。
    """
    try:
        logger.info("接收到模型初始化消息，开始处理")
        await chat_init(message.body)
        await message.ack()
    except Exception as e:
        logger.opt(exception=e).error("模型初始化失败，消息送入死信队列")
        await message.nack(requeue=False)
