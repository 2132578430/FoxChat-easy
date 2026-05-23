import os
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from loguru import logger

from app.api import rag_router, chat_router, llm_config_router
from app.core.settings import global_settings
from app.core.mq import init_rabbitmq, close_rabbitmq
from app.exception import register_exception_handlers
from app.service.chat.timer_scheduler import timer_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 开启rabbitmq监听后台
    connection = await init_rabbitmq()

    # 启动定时总结调度器
    asyncio.create_task(timer_scheduler())
    logger.info("[Timer Scheduler] Timer summary scheduler started")

    yield

    # 关闭rabbitmq监听后台
    await close_rabbitmq(connection)

load_dotenv()

app = FastAPI(lifespan=lifespan)

# 注册全局异常处理器
register_exception_handlers(app)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "running", "timestamp": datetime.now().isoformat()}

# 注册路由
app.include_router(rag_router)
app.include_router(chat_router)
app.include_router(llm_config_router)

server_port = global_settings.server.port

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=server_port, reload=False)