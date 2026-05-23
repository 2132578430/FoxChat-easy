"""
FoxAssistant Python 服务主入口

功能：
- FastAPI HTTP API
- /command 命令处理端点
- 30秒无请求自动退出
- Named Pipe 与 C# Orb UI 通信
"""

import sys
import os
import asyncio
import threading
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from loguru import logger

from schemas.request import VoiceRequest, WakeupRequest
from schemas.response import Response
from service.command_classifier import classify_command, CommandType
from config.keyword_rules import IntentType
from service.command_executor import CommandExecutor
from service.pipe_client import init_pipe_client, get_pipe_client, send_orb_state, notify_idle_timeout


# ============================================================
# 配置
# ============================================================

PORT = 11000
# IDLE_TIMEOUT 设置为 0 表示禁用自动关闭（Banner 模式下 Python 常驻运行）
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", "0"))
PIPE_NAME = os.getenv("PIPE_NAME", "FoxAssistant")

# ============================================================
# 自动关闭机制
# ============================================================

idle_timer: Optional[threading.Timer] = None
start_time = datetime.now()


def shutdown_service():
    """优雅关闭服务"""
    uptime = (datetime.now() - start_time).total_seconds()

    # 发送静息超时通知给 C# Orb
    send_orb_state("jump")  # 播放退出动画
    notify_idle_timeout()   # 等待 C# 确认

    logger.info(f"【自动关闭】服务超时退出 (IDLE_TIMEOUT={IDLE_TIMEOUT}s, uptime={uptime:.1f}s)")
    os._exit(0)  # 强制退出进程


def reset_idle_timer():
    """重置空闲计时器（如果 IDLE_TIMEOUT=0 则禁用自动关闭）"""
    global idle_timer
    if idle_timer:
        idle_timer.cancel()

    # IDLE_TIMEOUT=0 表示禁用自动关闭（Banner 模式）
    if IDLE_TIMEOUT <= 0:
        logger.debug("【计时器】自动关闭已禁用 (IDLE_TIMEOUT=0)")
        return

    # 检查 Pipe 健康状态，如果应该退出则关闭服务
    client = get_pipe_client()
    if client and client.should_exit():
        logger.warning("【Pipe】连接断开多次，服务退出")
        os._exit(0)

    idle_timer = threading.Timer(IDLE_TIMEOUT, shutdown_service)
    idle_timer.daemon = True
    idle_timer.start()
    logger.debug(f"【计时器】重置为 {IDLE_TIMEOUT}s")


# ============================================================
# FastAPI 生命周期
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期管理"""
    import sys
    logger.info(f"【启动】FoxAssistant Python 服务启动 (port={PORT})")
    logger.info(f"【Python】{sys.executable}")
    logger.info(f"【配置】IDLE_TIMEOUT={IDLE_TIMEOUT}s")

    # 初始化 Pipe 客户端
    pipe_client = init_pipe_client(PIPE_NAME)
    if pipe_client:
        logger.info("【Pipe】已连接 C# Orb UI")
        send_orb_state("idle")  # 初始状态
    else:
        logger.warn("【Pipe】Pipe 连接失败，无 UI 状态同步")

    # 注意：向量模型延迟加载，只在需要语义匹配时才加载
    # 这样可以快速启动，高频命令通过关键词匹配即可

    reset_idle_timer()

    yield

    logger.info("【关闭】服务关闭")
    if idle_timer:
        idle_timer.cancel()

    # 断开 Pipe
    client = get_pipe_client()
    if client:
        client.disconnect()


app = FastAPI(
    title="FoxAssistant",
    description="语音命令执行服务",
    version="1.0.0",
    lifespan=lifespan
)

executor = CommandExecutor()


# ============================================================
# API 端点
# ============================================================

@app.post("/command", response_model=Response)
async def handle_command(request: VoiceRequest):
    """
    处理语音命令

    请求格式: {"text": "放一首歌", "source": "voice"}
    响应格式: {"code": 200, "msg": "success", "data": {...}}
              {"code": 100, "msg": "无法识别的命令", "data": None}  # 无法识别的命令
              {"code": 101, "msg": "聊天意图", "data": None}  # 聊天意图
    """
    reset_idle_timer()

    if not request.text:
        return Response.error(code=400, msg="missing required field: text")

    logger.info(f"【请求】收到命令: {request.text} (source={request.source})")

    # 先显示 thinking（不论是否有效命令）
    send_orb_state("thinking")

    # 分类命令（两层意图判断）
    intent, description = classify_command(request.text)

    # 聊天意图：打日志，返回 code=101
    if intent == IntentType.CHAT_INTENT:
        logger.info(f"【聊天意图】用户输入: \"{request.text}\"")
        await asyncio.sleep(0.6)  # 等待 thinking 动画播放
        send_orb_state("no")
        return Response.error(code=101, msg="聊天意图（暂不处理）")

    # 无法识别的命令，等待 thinking 动画后返回 code=100
    if intent == CommandType.UNKNOWN:
        logger.info(f"【命令】无法识别: {request.text}")
        await asyncio.sleep(0.6)  # 等待 thinking 动画播放
        send_orb_state("no")
        return Response.error(code=100, msg="无法识别的命令")

    # 执行命令
    result = executor.execute(intent, request.text)

    # 发送状态：成功或失败
    if result.get("success"):
        send_orb_state("yes")
    else:
        send_orb_state("no")

    return Response.ok(data=result, msg=description)


@app.post("/wakeup", response_model=Response)
async def handle_wakeup(request: WakeupRequest):
    """
    处理唤醒信号

    当C#唤醒服务检测到口令后发送
    """
    reset_idle_timer()
    logger.info("【唤醒】收到唤醒信号")

    # 发送唤醒成功状态
    send_orb_state("alert")

    # 短暂延迟后切换到 idle
    threading.Timer(2.0, lambda: send_orb_state("idle")).start()

    return Response.ok(data={"status": "ready"}, msg="服务已唤醒")


@app.get("/health", response_model=Response)
async def health_check():
    """健康检查"""
    reset_idle_timer()
    uptime = (datetime.now() - start_time).total_seconds()
    return Response.ok(data={"uptime": uptime, "timeout": IDLE_TIMEOUT})


@app.post("/preload", response_model=Response)
async def preload_models():
    """
    预加载向量模型

    C# 唤醒时调用，避免唤醒后等待模型加载
    """
    from service.intent_classifier import init_embedding_model, init_intent_embeddings

    logger.info("【预加载】开始加载向量模型...")

    # 加载 sentence-transformers 模型
    if init_embedding_model():
        # 预计算意图向量缓存
        init_intent_embeddings()
        logger.info("【预加载】向量模型已就绪")
        return Response.ok(data={"status": "loaded"}, msg="向量模型已预加载")

    logger.warning("【预加载】向量模型加载失败")
    return Response.error(code=500, msg="向量模型加载失败")


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)