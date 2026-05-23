import aio_pika
from loguru import logger

from app.core.settings import global_settings


async def rabbitmq_connect():
    connection = await aio_pika.connect_robust(
        host=global_settings.rabbitmq.host,
        port=global_settings.rabbitmq.port,
        login=global_settings.rabbitmq.user,
        password=global_settings.rabbitmq.password,
    )

    logger.info("成功连接到RabbitMq")

    return connection