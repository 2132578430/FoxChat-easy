"""
gRPC AI 聊天服务端

基于 grpc.aio 的异步服务端，与 FastAPI 同进程运行。
负责：接收 Java 的 ChatRequest，调用流式 LLM + 标签解析器，逐个 ChatResponse 推回。

启动方式（在 main.py 中）：
    from app.grpc.ai_chat_server import start_grpc_server
    asyncio.create_task(start_grpc_server(50051))

依赖：需先生成 proto stub
    python -m grpc_tools.protoc -Iproto --python_out=app/grpc --grpc_python_out=app/grpc proto/ai_chat.proto
"""

import asyncio
import grpc
from concurrent import futures
from loguru import logger

# proto 生成的 stub —— 需先运行 protoc 编译
try:
    from app.grpc.foxchat.ai import ai_chat_pb2, ai_chat_pb2_grpc
except ImportError:
    # 提供占位，避免 import 时崩溃（实际运行前必须生成）
    ai_chat_pb2 = None
    ai_chat_pb2_grpc = None

from app.service.chat.streaming_tag_parser import StreamingTagParser, StreamToken
from app.service.chat.streaming_llm_service import stream_llm_response
from app.service.chat.chat_msg_service import clear_chat_memory


class AIChatServiceImpl(ai_chat_pb2_grpc.AIChatServiceServicer if ai_chat_pb2_grpc else object):
    """AI 聊天 gRPC 服务实现"""

    async def Chat(self, request, context):
        """
        服务端流式 RPC：接收 ChatRequest，逐个 yield ChatResponse。

        流程：
        1. stream_llm_response → 逐 token 产出
        2. StreamingTagParser → 检测 <action> 标签，标注 block_type
        3. 每个 StreamToken 转 ChatResponse → yield
        4. 流结束 → yield 带 is_final=True 的 ChatResponse（含 emotion）
        """
        user_id = request.user_id
        llm_id = request.llm_id
        msg_content = request.msg_content

        logger.info(f"[gRPC Chat] user={user_id[:8]}... llm={llm_id[:8]}... msg={msg_content[:30]}...")

        parser = StreamingTagParser()
        seq = 0

        try:
            async for token in stream_llm_response(user_id, llm_id, msg_content):
                for st in parser.feed(token):
                    seq += 1
                    yield self._to_response(st, seq, is_final=False)

            # 流结束，刷新缓冲区
            for st in parser.flush():
                seq += 1
                yield self._to_response(st, seq, is_final=False)

            # 获取情感标签
            emotion = getattr(stream_llm_response, '_last_emotion', 'neutral')

            # 最终包
            yield ai_chat_pb2.ChatResponse(
                content="",
                is_final=True,
                block_type="text",
                emotion=emotion,
                sequence=seq + 1,
            )

        except Exception as e:
            logger.error(f"[gRPC Chat] 流式错误: {e}")
            yield ai_chat_pb2.ChatResponse(
                content="",
                is_final=True,
                block_type="error",
                error_code=15000,
                error_msg=str(e),
                sequence=seq + 1,
            )

    async def DeleteMemory(self, request, context):
        """删除记忆（非流式）"""
        try:
            await clear_chat_memory(request.user_id, request.llm_id)
            return ai_chat_pb2.DeleteResponse(success=True, message="记忆已清除")
        except Exception as e:
            logger.error(f"[gRPC DeleteMemory] 错误: {e}")
            return ai_chat_pb2.DeleteResponse(success=False, message=str(e))

    # ── 内部 ──────────────────────────────────────

    @staticmethod
    def _to_response(st: StreamToken, seq: int, is_final: bool):
        return ai_chat_pb2.ChatResponse(
            content=st.content,
            is_final=is_final,
            block_type=st.block_type,
            is_block_start=st.is_block_start,
            is_block_end=st.is_block_end,
            sequence=seq,
        )


async def start_grpc_server(port: int = 50051):
    """启动 gRPC 异步服务器（与 FastAPI 同进程）"""
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 10 * 1024 * 1024),
            ('grpc.max_receive_message_length', 10 * 1024 * 1024),
            ('grpc.keepalive_time_ms', 30000),
            ('grpc.keepalive_timeout_ms', 10000),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.max_pings_without_data', 0),
        ],
    )

    ai_chat_pb2_grpc.add_AIChatServiceServicer_to_server(
        AIChatServiceImpl(), server
    )

    server.add_insecure_port(f'0.0.0.0:{port}')
    await server.start()
    logger.info(f"[gRPC] 服务已启动: 0.0.0.0:{port}")
    await server.wait_for_termination()
