import aio_pika
from loguru import logger

from app.core.settings import global_settings

# 与 Java 侧 RagRabbitMqConfig 的队列声明保持一致
RAG_DLX_EXCHANGE = "rag.dlx.exchange"
RAG_DLX_ROUTING_KEY = "rag.dlx.key"
CHAT_DLX_EXCHANGE = "chat.dlx.exchange"
CHAT_DLX_ROUTING_KEY = "chat.dlx.key"


async def rag_setup_queue(channel: aio_pika.Channel):
    queue = await channel.declare_queue(
        name=global_settings.rabbitmq.rag_queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": RAG_DLX_EXCHANGE,
            "x-dead-letter-routing-key": RAG_DLX_ROUTING_KEY,
        },
    )
    logger.info("开始监听Rag队列")
    return queue

async def chat_setup_queue(channel: aio_pika.Channel):
    queue = await channel.declare_queue(
        name = global_settings.rabbitmq.chat_queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": CHAT_DLX_EXCHANGE,
            "x-dead-letter-routing-key": CHAT_DLX_ROUTING_KEY,
        },
    )
    logger.info("开始监听Chat队列")
    return queue