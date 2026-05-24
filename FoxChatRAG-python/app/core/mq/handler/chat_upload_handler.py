from loguru import logger

from app.service import chat_init


async def chat_upload_handler(message):
    try:
        logger.info("接收到消费者队列消息，开始处理消息")
        await chat_init(message.body)
        await message.ack()
    except Exception as e:
        logger.error(f"rag文件处理错误: {e}", exc_info=True)
        await message.nack(requeue=True)