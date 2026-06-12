package com.bedfox.netty.handler.impl;

import com.alibaba.fastjson2.JSON;
import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.netty.netty.ChatWebSocketHandler;
import com.bedfox.pojo.domain.ChatProtocol;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.service.client.grpc.GrpcChatClient;
import io.netty.channel.ChannelHandlerContext;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * LLM 流式聊天 Handler（WebSocket 路径）
 *
 * 流程：
 *   前端 WS 发送 type=1108 → ChatWebSocketHandler 分发至此
 *   → 解析 extend 中的 {llmId, msgContent}
 *   → 调用 GrpcChatClient.streamChat() 流式 gRPC
 *   → 每个 ChatResponse 编码为 ChatProtocol.Message(type=1108) → ctx.writeAndFlush 推回前端
 *
 * 不涉及：
 *   - 消息持久化（Python 侧 graph.save_message 节点负责）
 *   - 标签解析（Python 侧 StreamingTagParser 负责）
 *
 * @author bedFox
 */
@Slf4j
@Component
public class LlmStreamHandler implements MsgHandler {

    @Resource
    GrpcChatClient grpcChatClient;

    @Override
    public MsgTypeConstant getMsgType() {
        return MsgTypeConstant.STREAM_TOKEN;
    }

    @Override
    public void handler(ChannelHandlerContext ctx, MsgDto msgDto) {
        String userId = ctx.channel().attr(ChatWebSocketHandler.USER_ID_KEY).get();
        String extend = msgDto.getExtend();

        // 1. 解析请求参数
        Map<String, String> req;
        try {
            req = JSON.parseObject(extend, Map.class);
        } catch (Exception e) {
            log.error("[LlmStream] JSON 解析失败: extend={}", extend, e);
            sendError(ctx, "请求格式错误");
            return;
        }

        String llmId = req.get("llmId");
        String msgContent = req.get("msgContent");

        if (llmId == null || msgContent == null) {
            log.error("[LlmStream] 缺少必要参数: llmId={}, msgContent={}", llmId, msgContent);
            sendError(ctx, "缺少llmId或msgContent");
            return;
        }

        log.info("[LlmStream] 发起流式: user={}, llm={}, msg={}",
                trim(userId, 8), trim(llmId, 8), trim(msgContent, 30));

        // 2. 调用 gRPC 流式（与 SSE 路径复用同一个 GrpcChatClient）
        grpcChatClient.streamChat(userId, llmId, msgContent,
                // onToken: 每个 ChatResponse → WS 二进制帧推回前端
                response -> {
                    Map<String, Object> token = new LinkedHashMap<>();
                    token.put("content", response.getContent());
                    token.put("blockType", response.getBlockType());
                    token.put("isBlockStart", response.getIsBlockStart());
                    token.put("isBlockEnd", response.getIsBlockEnd());
                    token.put("sequence", response.getSequence());
                    token.put("isFinal", response.getIsFinal());
                    if (response.getIsFinal()) {
                        token.put("emotion",
                                response.getEmotion().isEmpty() ? "neutral" : response.getEmotion());
                    }

                    ChatProtocol.Message msg = ChatProtocol.Message.newBuilder()
                            .setType(MsgTypeConstant.STREAM_TOKEN.getCode())
                            .setExtend(JSON.toJSONString(token))
                            .build();
                    ctx.writeAndFlush(msg);
                },
                // onComplete
                () -> log.debug("[LlmStream] 流完成: user={}", trim(userId, 8)),
                // onError
                error -> {
                    log.error("[LlmStream] 流错误: user={}, msg={}", trim(userId, 8), error.getMessage());
                    sendError(ctx, error.getMessage());
                }
        );
    }

    private void sendError(ChannelHandlerContext ctx, String errorMsg) {
        Map<String, Object> err = new LinkedHashMap<>();
        err.put("error", errorMsg);
        err.put("isFinal", true);

        ChatProtocol.Message msg = ChatProtocol.Message.newBuilder()
                .setType(MsgTypeConstant.STREAM_TOKEN.getCode())
                .setExtend(JSON.toJSONString(err))
                .build();
        ctx.writeAndFlush(msg);
    }

    private static String trim(String s, int maxLen) {
        if (s == null) return "null";
        return s.length() <= maxLen ? s : s.substring(0, maxLen) + "...";
    }
}
