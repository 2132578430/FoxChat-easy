package com.bedfox.netty.handler.impl;

import com.alibaba.fastjson2.JSON;
import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.netty.netty.ChatWebSocketHandler;
import com.bedfox.pojo.domain.ChatProtocol;
import com.bedfox.pojo.domain.LlmChatMsg;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.pojo.proto.ai.AiChatProto;
import com.bedfox.service.client.grpc.GrpcChatClient;
import com.bedfox.service.service.LlmChatMsgService;
import io.netty.channel.ChannelHandlerContext;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * LLM 流式聊天 Handler（WebSocket 路径）
 *
 * 流程：
 *   前端 WS 发送 type=1108 → ChatWebSocketHandler 分发至此
 *   → 解析 extend 中的 {llmId, msgContent}
 *   → 调用 GrpcChatClient.streamChat() 流式 gRPC
 *   → 每个 ChatResponse 编码为 ChatProtocol.Message(type=1108) → ctx.writeAndFlush 推回前端
 *   → 收到最终包时把 human + AI 两条消息写入 llm_chat_msg
 *
 * 标签解析由 Python 侧 StreamingTagParser 完成，这里只按 blockType 聚合后落库。
 *
 * @author bedFox
 */
@Slf4j
@Component
public class LlmStreamHandler implements MsgHandler {

    @Resource
    GrpcChatClient grpcChatClient;

    @Resource
    LlmChatMsgService llmChatMsgService;

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
        LocalDateTime requestTime = LocalDateTime.now();
        List<Map<String, String>> blocks = new ArrayList<>();
        StringBuilder currentBlockContent = new StringBuilder();
        String[] currentBlockType = {null};
        AtomicBoolean persisted = new AtomicBoolean(false);

        try {
            grpcChatClient.streamChat(userId, llmId, msgContent,
                    // onToken: 每个 ChatResponse → WS 二进制帧推回前端
                    response -> {
                        try {
                            if (response.getIsFinal()) {
                                flushCurrentBlock(blocks, currentBlockContent, currentBlockType);
                                String emotion = response.getEmotion().isEmpty() ? "neutral" : response.getEmotion();

                                if (persisted.compareAndSet(false, true)) {
                                    persistChatRound(userId, llmId, msgContent, requestTime, blocks, emotion);
                                }

                                Map<String, Object> token = buildToken(response);
                                token.put("emotion", emotion);
                                sendToken(ctx, token);
                                return;
                            }

                            if (currentBlockType[0] == null
                                    || !response.getBlockType().equals(currentBlockType[0])) {
                                flushCurrentBlock(blocks, currentBlockContent, currentBlockType);
                                currentBlockType[0] = response.getBlockType();
                            }
                            if (response.getContent() != null && !response.getContent().isEmpty()) {
                                currentBlockContent.append(response.getContent());
                            }

                            sendToken(ctx, buildToken(response));
                        } catch (Exception e) {
                            log.error("[LlmStream] 处理 token 失败: user={}, msg={}", trim(userId, 8), e.getMessage(), e);
                        }
                    },
                    // onComplete
                    () -> log.debug("[LlmStream] 流完成: user={}", trim(userId, 8)),
                    // onError: 前端收到 error 后会降级 REST（REST 路径自行落库，避免重复写入）
                    error -> {
                        log.error("[LlmStream] 流错误: user={}, msg={}", trim(userId, 8), error.getMessage());
                        sendError(ctx, error.getMessage());
                    }
            );
        } catch (Exception e) {
            log.error("[LlmStream] gRPC 调用失败: user={}, msg={}", trim(userId, 8), e.getMessage(), e);
            sendError(ctx, e.getMessage());
        }
    }

    /**
     * 最终包到达后落库：human 使用请求时间，AI 内容为 {"blocks":[...],"emotion":"..."}
     * 与 REST/SSE 路径的格式保持一致，历史接口才能按同一格式解析。
     */
    private void persistChatRound(String userId, String llmId, String msgContent,
                                  LocalDateTime requestTime, List<Map<String, String>> blocks, String emotion) {
        try {
            llmChatMsgService.save(buildLlmChatMsg(msgContent, llmId, userId, true, 0, requestTime));

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("blocks", blocks);
            result.put("emotion", emotion);
            llmChatMsgService.save(buildLlmChatMsg(JSON.toJSONString(result), llmId, userId, false, 1, LocalDateTime.now()));

            log.info("[LlmStream] 对话已落库: user={}, llm={}, blocks={}", trim(userId, 8), trim(llmId, 8), blocks.size());
        } catch (Exception e) {
            log.error("[LlmStream] 落库失败: user={}, llm={}, msg={}", trim(userId, 8), trim(llmId, 8), e.getMessage(), e);
        }
    }

    private static LlmChatMsg buildLlmChatMsg(String msgContent, String llmId, String userId,
                                              boolean isHuman, int status, LocalDateTime createTime) {
        LlmChatMsg chatMsg = new LlmChatMsg();
        chatMsg.setMsgContent(msgContent);
        chatMsg.setLlmId(llmId);
        chatMsg.setSendUserId(userId);
        chatMsg.setIsHuman(isHuman);
        chatMsg.setStatus(status);
        chatMsg.setCreateTime(createTime);
        return chatMsg;
    }

    private static void flushCurrentBlock(List<Map<String, String>> blocks,
                                          StringBuilder currentBlockContent,
                                          String[] currentBlockType) {
        if (currentBlockType[0] != null && currentBlockContent.length() > 0) {
            Map<String, String> block = new LinkedHashMap<>();
            block.put("type", currentBlockType[0]);
            block.put("content", currentBlockContent.toString());
            blocks.add(block);
            currentBlockContent.setLength(0);
        }
    }

    private static Map<String, Object> buildToken(AiChatProto.ChatResponse response) {
        Map<String, Object> token = new LinkedHashMap<>();
        token.put("content", response.getContent());
        token.put("blockType", response.getBlockType());
        token.put("isBlockStart", response.getIsBlockStart());
        token.put("isBlockEnd", response.getIsBlockEnd());
        token.put("sequence", response.getSequence());
        token.put("isFinal", response.getIsFinal());
        return token;
    }

    private static void sendToken(ChannelHandlerContext ctx, Map<String, Object> token) {
        ChatProtocol.Message msg = ChatProtocol.Message.newBuilder()
                .setType(MsgTypeConstant.STREAM_TOKEN.getCode())
                .setExtend(JSON.toJSONString(token))
                .build();
        ctx.writeAndFlush(msg);
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
