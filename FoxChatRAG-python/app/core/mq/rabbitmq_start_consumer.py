import aio_pika

from app.core import get_db
from app.core.mq.handler import rag_file_handler, chat_upload_handler


async def rag(queue: aio_pika.Queue):
    """
    # 开启rag消费者监控
    :return:
    """
    # 监控rag文件上传队列,手动ack
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with get_db() as db:
                await rag_file_handler(message, db)

async def chat(queue: aio_pika.Queue):
    """
    开启chat消费者监视
    """
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            await chat_upload_handler(message)