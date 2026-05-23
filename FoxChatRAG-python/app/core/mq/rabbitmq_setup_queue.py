import aio_pika
from loguru import logger

from app.core.settings import global_settings


async def rag_setup_queue(channel: aio_pika.Channel):
    queue = await channel.declare_queue(
        name=global_settings.rabbitmq.rag_queue,
        durable=True,
    )
    logger.info("开始监听Rag队列")
    return queue

async def chat_setup_queue(channel: aio_pika.Channel):
    queue = await channel.declare_queue(
        name = global_settings.rabbitmq.chat_queue,
        durable=True
    )
    logger.info("开始监听Chat队列")
    return queue