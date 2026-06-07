"""
gRPC AI 聊天服务端

基于 grpc.aio 的异步服务端，与 FastAPI 同进程运行。
负责：接收 Java 的 ChatRequest，通过 LangGraph 编排流式 LLM + 标签解析，逐个 ChatResponse 推回。

架构（2026-05-21 重构）：
  - 流式：graph.ainvoke (stream_queue) → 逐 token yield
  - 降级：graph.ainvoke (非流式) → 一次性返回完整结果
  两条路径共享同一张 LangGraph，只切换 LLM 调用模式。

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

from app.service.chat.parsing.streaming_tag_parser import StreamingTagParser, StreamToken
from app.service.chat.state.chat_msg_service import clear_chat_memory
from app.service.chat.state.session_lock import acquire_session_lock, release_session_lock
from app.service.chat.graph.graph import main_graph
from app.service.chat.graph.nodes import _stream_queue_ctx


class AIChatServiceImpl(ai_chat_pb2_grpc.AIChatServiceServicer if ai_chat_pb2_grpc else object):
    """AI 聊天 gRPC 服务实现"""

    async def Chat(self, request, context):
        """
        服务端流式 RPC：接收 ChatRequest，然后逐个 yield ChatResponse。

        流程：
        1. LangGraph 编排全流程
        2. invoke_llm 节点通过 stream_queue 逐 token 推送
        3. StreamingTagParser → 检测 <action> 标签，标注 block_type
        4. 每个 StreamToken 转 ChatResponse → yield
        5. Graph 后处理 4 路并行（save ∥ format ∥ emotion ∥ summary）
        6. 流结束 → yield 带 is_final=True 的 ChatResponse（含 emotion）

        降级：流式失败时，自动回退到 main_graph.ainvoke() 非流式模式
        """
        user_id = request.user_id
        llm_id = request.llm_id
        msg_content = request.msg_content

        logger.info(f"[gRPC Chat] user={user_id[:8]}... llm={llm_id[:8]}... msg={msg_content[:30]}...")

        # 初始化标签解析器
        parser = StreamingTagParser()
        # 初始化序列号
        seq = 0

        # 获取会话锁，同时上锁
        lock = await acquire_session_lock(user_id, llm_id)

        try:
            # 流式传输
            async for response in self._stream_chat(user_id, llm_id, msg_content, parser):
                seq += 1
                yield response

        except asyncio.CancelledError:
            logger.warning(f"[gRPC Chat] 流式被取消 (客户端断开或 deadline)，降级到非流式")
            # 清除取消标记，使后续 await 不会被 CancelledError 中断，确保 fallback 能够执行
            task = asyncio.current_task()
            if task:
                task.uncancel()
                
            async for response in self._do_fallback(user_id, llm_id, msg_content, parser, seq):
                yield response
        except Exception as e:
            logger.error(f"[gRPC Chat] 流式失败，降级到非流式: {e}")
            async for response in self._do_fallback(user_id, llm_id, msg_content, parser, seq):
                yield response
        finally:
            release_session_lock(lock)

    async def _stream_chat(self, user_id: str, llm_id: str, msg_content: str, parser: StreamingTagParser):
        """
        流式 Chat：graph + stream_queue
        """

        stream_queue = asyncio.Queue()
        FIRST_TOKEN_TIMEOUT = 60  # 首 token 超时（秒）
        INTER_TOKEN_TIMEOUT = 15  # token 间超时（秒）

        # graph中初始的State
        initial_state = {
            "user_id": user_id,
            "llm_id": llm_id,
            "msg_content": msg_content,
        }
        # 对State的配置
        config = {
            "configurable": {
                "thread_id": f"{user_id}:{llm_id}",
            }
        }

        # 通过 contextvars 传递 stream_queue
        token = _stream_queue_ctx.set(stream_queue)
        try:
            graph_task = asyncio.create_task(main_graph.ainvoke(initial_state, config))
        finally:
            _stream_queue_ctx.reset(token)

        # 读取流式 token，逐 token 喂给 parser 并 yield
        logger.info(f"[gRPC Chat] _stream_chat 开始等待 token ...")
        seq = 0
        first_token = True
        try:
            while True:
                # 带超时的 queue.get，防止 graph 挂掉后永久阻塞
                timeout = FIRST_TOKEN_TIMEOUT if first_token else INTER_TOKEN_TIMEOUT
                try:
                    token = await asyncio.wait_for(stream_queue.get(), timeout=timeout)
                    if first_token:
                        logger.info(f"[gRPC Chat] 收到首 token: len={len(token)}")
                except asyncio.TimeoutError:
                    # 超时：检查 graph 是否已失败
                    if graph_task.done():
                        exc = graph_task.exception()
                        if exc:
                            logger.error(f"[gRPC Chat] Graph 执行失败: {exc}")
                            raise exc
                        else:
                            raise RuntimeError("Graph未产生Token输出")
                    else:
                        logger.error(f"[gRPC Chat] 首 token 超时 ({timeout}s)，取消 graph")
                        graph_task.cancel()
                        raise TimeoutError(f"LLM streaming timed out waiting for {'first' if first_token else 'next'} token ({timeout}s)")

                first_token = False
                
                # 判断流是否结束
                if token is None:
                    logger.info(f"[gRPC Chat] 收到流结束 sentinel, 共 {seq} 个 gRPC 消息")
                    break

                # 开始解析token
                for st in parser.feed(token):
                    seq += 1
                    # logger.debug(f"[gRPC Chat] yield gRPC seq={seq} type={st.block_type}")
                    yield self._to_response(st, seq, is_final=False)

            # 刷新 parser 缓冲区（action 标签闭合）
            for st in parser.flush():
                seq += 1
                yield self._to_response(st, seq, is_final=False)

            # 等待 graph 完成（后处理 4 路并行）
            result = await graph_task
            emotion = result.get("emotion", "normal")

            # 最终包
            yield ai_chat_pb2.ChatResponse(
                content="",
                is_final=True,
                block_type="text",
                emotion=emotion,
                sequence=seq + 1,
            )

        except asyncio.CancelledError:
            # 任务主动取消,取消 graph task
            if not graph_task.done():
                graph_task.cancel()
            raise
        except Exception as e:
            # 其他异常导致task报错,取消 graph task
            if not graph_task.done():
                graph_task.cancel()
            raise

    async def _do_fallback(self, user_id: str, llm_id: str, msg_content: str,
                           parser: StreamingTagParser, seq: int):
        """降级到非流式 + 异常处理。seq 用于错误响应的序列号。"""
        try:
            async for response in self._fallback_chat(user_id, llm_id, msg_content, parser):
                seq += 1
                yield response
        except Exception as e:
            logger.error(f"[gRPC Chat] 降级也失败: {e}")
            yield ai_chat_pb2.ChatResponse(
                content="",
                is_final=True,
                block_type="error",
                error_code=15000,
                error_msg=str(e),
                sequence=seq + 1,
            )

    async def _fallback_chat(self, user_id: str, llm_id: str, msg_content: str, parser: StreamingTagParser):
        """
        降级 Chat：同一张图，非流式模式

        这里还用parse解析是因为py和java用的是gRPC通讯,已经用了stream建立连接
        一次性推送推送不过去,所以只能逐个token解析,也变相模仿了stream推送的样子
        """

        initial_state = {
            "user_id": user_id,
            "llm_id": llm_id,
            "msg_content": msg_content,
        }

        config = {
            "configurable": {
                "thread_id": f"{user_id}:{llm_id}",
            }
        }

        result = await main_graph.ainvoke(initial_state, config)

        blocks = result.get("blocks", [])
        emotion = result.get("emotion", "neutral")

        seq = 0

        if blocks:
            # 有结构化 blocks → 逐个输出
            for block in blocks:
                text = block.get("text", "")
                if text:
                    for st in parser.feed(text):
                        seq += 1
                        yield self._to_response(st, seq, is_final=False)
            for st in parser.flush():
                seq += 1
                yield self._to_response(st, seq, is_final=False)
        else:
            # 纯文本响应
            ai_text = result.get("ai_response", "")
            if ai_text:
                for st in parser.feed(ai_text):
                    seq += 1
                    yield self._to_response(st, seq, is_final=False)
                for st in parser.flush():
                    seq += 1
                    yield self._to_response(st, seq, is_final=False)

        # 最终包
        yield ai_chat_pb2.ChatResponse(
            content="",
            is_final=True,
            block_type="text",
            emotion=emotion,
            sequence=seq + 1,
        )

    async def DeleteMemory(self, request, context):
        """删除记忆"""
        try:
            await clear_chat_memory(request.user_id, request.llm_id)
            return ai_chat_pb2.DeleteResponse(success=True, message="记忆已清除")
        except Exception as e:
            logger.error(f"[gRPC DeleteMemory] 错误: {e}")
            return ai_chat_pb2.DeleteResponse(success=False, message=str(e))

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
