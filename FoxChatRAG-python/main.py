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
from app.service.chat.memory.timer_scheduler import timer_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ═══════════════════════════════════════════════
    # 启动时并行健康检查所有中间件（带重试）
    # 任一中间件不可用 → 启动失败，不进入服务状态
    # ═══════════════════════════════════════════════
    from app.core.health_check import retry_connect, check_redis, check_mysql

    results = await asyncio.gather(
        retry_connect("MySQL", check_mysql),
        retry_connect("Redis", check_redis),
        init_rabbitmq(),  # RabbitMQ 内部自带重试
    )
    connection = results[2]

    # 启动定时总结调度器
    asyncio.create_task(timer_scheduler())
    logger.info("[定时任务] 记忆总结定时调度器开启")

    # 启动 gRPC 流式服务（端口 50051）
    grpc_port = int(os.getenv("GRPC_PORT", "50051"))
    try:
        from app.grpc.ai_chat_server import start_grpc_server
        grpc_task = asyncio.create_task(start_grpc_server(grpc_port))
        logger.info(f"[gRPC] 启动中: 0.0.0.0:{grpc_port}")
    except ImportError as e:
        logger.warning(f"[gRPC] 跳过启动（未生成 stub 或缺少 grpcio）: {e}")

    # 校验 ChromaDB 集合维度（切换 embedding 模型时自动迁移）
    try:
        from app.chroma.chroma import ensure_collection_dimensions
        ensure_collection_dimensions()
    except Exception as e:
        logger.warning(f"[ChromaDB] 维度校验失败（非致命）: {e}")

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