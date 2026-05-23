import aio_pika
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.service.rag import upload_file


async def rag_file_handler(message, db: AsyncSession):
    """
    # rag消息处理体
    :return:
    """
    try :
        # TODO:检查幂等性

        await upload_file(message.body, db)
        await message.ack()
    except Exception as e:
        logger.exception(f"rag文件处理错误")
        await message.nack(requeue=True)