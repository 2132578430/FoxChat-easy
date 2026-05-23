from loguru import logger

from app.service import chat_init
from app.core.db.mysql_client import get_db


async def chat_upload_handler(message):
    try:
        # TODO:检查幂等性
        logger.info("接收到消费者队列消息，开始处理消息")
        async with get_db() as db:
            await chat_init(message.body, db)
        await message.ack()
    except Exception as e:
        logger.error(f"rag文件处理错误: {e}", exc_info=True)
        await message.nack(requeue=True)