import asyncio

from loguru import logger

from app.core.mq import rabbitmq_start_consumer
from app.core.mq.rabbitmq_connnect import rabbitmq_connect
from app.core.mq.rabbitmq_setup_queue import rag_setup_queue, chat_setup_queue


async def init_rabbitmq():
    # 开启rabbitmq连接
    connection = await rabbitmq_connect()
    channel_rag = await connection.channel()
    channel_chat = await connection.channel()

    # 保证rabbitmq中所需队列存在
    rag_queue = await rag_setup_queue(channel_rag)
    chat_queue = await chat_setup_queue(channel_chat)


    # 开启rabbitmq消费者线程，防止阻塞主线程
    asyncio.create_task(rabbitmq_start_consumer.rag(rag_queue))
    asyncio.create_task(rabbitmq_start_consumer.chat(chat_queue))

    return connection

async def close_rabbitmq(connection):
    if connection:
        await connection.close()
        logger.info("rabbitmq关闭")