package com.bedfox.service.service.impl;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.bedfox.common.constant.ResultStatusConstant;
import com.bedfox.common.exception.BusinessException;
import com.bedfox.common.util.M;
import com.bedfox.pojo.domain.LlmChatMsg;
import com.bedfox.pojo.to.ChatMsgTo;
import com.bedfox.pojo.vo.LlmChatMsgVo;
import com.bedfox.service.remote.ChatClient;
import com.bedfox.service.client.grpc.GrpcChatClient;
import com.bedfox.service.service.LlmChatMsgService;
import com.bedfox.service.service.LlmChatService;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ForkJoinPool;

/**
 * @author 21325
 * @description LLM聊天Service实现
 * @createDate 2026-04-29
 */
@Slf4j
@Service
public class LlmChatServiceImpl implements LlmChatService {

    @Resource
    ChatClient chatClient;

    @Resource
    GrpcChatClient grpcChatClient;

    @Resource
    LlmChatMsgService llmChatMsgService;

    /**
     * 聊天主逻辑
     */
    @Override
    public LlmChatMsgVo llmChat(String llmId, String msgContent, String userId) {
        // 1. 保存用户消息 status=SENT(0)
        LlmChatMsg llmChatMsgHuman = buildLlmChatMsg(msgContent, llmId, userId, true, 0);
        llmChatMsgService.save(llmChatMsgHuman);
        log.debug("用户消息已保存，status=SENT(0)");

        // 2. 创建并保存AI占位消息 status=PROCESSING(3)
        LlmChatMsg aiPlaceholder = buildLlmChatMsg("思考中...", llmId, userId, false, 3);
        llmChatMsgService.save(aiPlaceholder);
        log.debug("AI占位消息已保存，status=PROCESSING(3)");

        ChatMsgTo chatMsg = new ChatMsgTo();
        chatMsg.setLlmId(llmId);
        chatMsg.setMsgContent(msgContent);
        chatMsg.setUserId(userId);

        try {
            // 3. 调用Python服务
            String resultJson = chatClient.chatMsg(chatMsg);
            log.info("接收到消息：{}", resultJson);

            resultJson = resultJson.replaceAll("</?[a-zA-Z_]+>", "");

            M<String> msg = JSON.parseObject(resultJson, new TypeReference<>() {});
            String data = msg.getData();

            // 4. 更新占位消息为 SAVED(1)，填入真实AI回复
            aiPlaceholder.setStatus(1);
            aiPlaceholder.setMsgContent(data);
            llmChatMsgService.updateById(aiPlaceholder);
            log.info("AI回复已更新，status=SAVED(1)");

            // 5. 返回成功VO
            LlmChatMsgVo chatMsgVo = new LlmChatMsgVo();
            chatMsgVo.setMsg(data);
            return chatMsgVo;

        } catch (Exception e) {
            log.error("Python调用失败", e);

            // 6. 更新占位消息为 FAILED(4)
            aiPlaceholder.setStatus(4);
            aiPlaceholder.setMsgContent("回复失败，请重试");
            llmChatMsgService.updateById(aiPlaceholder);
            log.warn("AI占位消息已标记为 FAILED(4)");

            // 7. 抛出异常让Controller返回错误给前端
            throw new BusinessException(ResultStatusConstant.LLM_FAILED);
        }
    }

    /**
     * 流式聊天（SSE）
     * 内部使用 gRPC streaming 调用 Python，逐 token 推给前端。
     * gRPC 失败时自动降级到 Feign REST 非流式调用。
     */
    @Override
    public SseEmitter llmChatStream(String llmId, String msgContent, String userId) {
        SseEmitter emitter = new SseEmitter(120_000L); // 120秒超时

        // 1. 保存用户消息
        LlmChatMsg llmChatMsgHuman = buildLlmChatMsg(msgContent, llmId, userId, true, 0);
        llmChatMsgService.save(llmChatMsgHuman);

        // 2. 保存AI占位消息
        LlmChatMsg aiPlaceholder = buildLlmChatMsg("", llmId, userId, false, 3);
        llmChatMsgService.save(aiPlaceholder);

        // Block 增量构建器：用 is_block_start / is_block_end 拼装结构化 blocks
        java.util.List<java.util.Map<String, String>> blocks = new java.util.ArrayList<>();
        StringBuilder currentBlockContent = new StringBuilder();
        String[] currentBlockType = {null};  // 数组绕过 lambda effectively-final 限制

        // 3. 尝试 gRPC 流式调用
        // [DIAG] 检查 ForkJoinPool 并行度 + 当前线程
        int parallelism = ForkJoinPool.commonPool().getParallelism();
        int poolSize = ForkJoinPool.commonPool().getPoolSize();
        int activeThreads = ForkJoinPool.commonPool().getActiveThreadCount();
        long queuedTasks = ForkJoinPool.commonPool().getQueuedTaskCount();
        log.info("[SSE DIAG] ForkJoinPool: parallelism={}, poolSize={}, active={}, queued={}, thread={}",
            parallelism, poolSize, activeThreads, queuedTasks, Thread.currentThread().getName());

        CompletableFuture.runAsync(() -> {
            log.info("[SSE DIAG] 进入 runAsync: thread={}", Thread.currentThread().getName());
            try {
                grpcChatClient.streamChat(
                    userId, llmId, msgContent,

                    // onToken: 每个 ChatResponse → 增量构建 blocks → SSE event
                    response -> {
                        try {
                            if (response.getIsFinal()) {
                                // 收尾当前 block
                                flushCurrentBlock(blocks, currentBlockContent, currentBlockType);

                                // 构建最终 JSON：{"blocks":[...],"emotion":"..."}
                                java.util.Map<String, Object> result = new java.util.LinkedHashMap<>();
                                result.put("blocks", blocks);
                                result.put("emotion", response.getEmotion().isEmpty() ? "neutral" : response.getEmotion());
                                String resultJson = JSON.toJSONString(result);

                                // 存入 MySQL（与 REST 路径格式一致）
                                aiPlaceholder.setMsgContent(resultJson);
                                aiPlaceholder.setStatus(1);
                                llmChatMsgService.updateById(aiPlaceholder);

                                // 通知前端
                                emitter.send(SseEmitter.event().name("done").data(resultJson));
                                emitter.complete();
                            } else {
                                // 流式 token — 增量构建 block
                                // 不用 is_block_start（parser 对 text 块设 false 有 bug），直接比较 block_type 判变
                                if (currentBlockType[0] == null
                                    || !response.getBlockType().equals(currentBlockType[0])) {
                                    flushCurrentBlock(blocks, currentBlockContent, currentBlockType);
                                    currentBlockType[0] = response.getBlockType();
                                }

                                String content = response.getContent();
                                if (content != null && !content.isEmpty()) {
                                    currentBlockContent.append(content);
                                }

                                // 实时推送当前 blocks 状态给前端
                                java.util.List<java.util.Map<String, String>> snapshot = buildBlockSnapshot(
                                    blocks, currentBlockContent, currentBlockType);
                                emitter.send(SseEmitter.event()
                                    .name("blocks")
                                    .data(JSON.toJSONString(snapshot)));
                            }
                        } catch (IOException e) {
                            log.error("[SSE] 发送失败: {}", e.getMessage());
                        }
                    },

                    // onComplete
                    () -> log.debug("[SSE] 流完成"),

                    // onError: 降级到 Feign REST
                    error -> {
                        log.warn("[SSE] gRPC 失败，降级 REST: {}", error.getMessage());
                        fallbackToRest(llmId, msgContent, userId, aiPlaceholder, emitter);
                    }
                );
            } catch (Throwable e) {
                log.error("[SSE] gRPC 异常({})，降级 REST: {}", e.getClass().getName(), e.getMessage(), e);
                fallbackToRest(llmId, msgContent, userId, aiPlaceholder, emitter);
            }
        });

        return emitter;
    }

    /**
     * 降级：使用旧 Feign REST 非流式调用
     */
    private void fallbackToRest(String llmId, String msgContent, String userId,
                                 LlmChatMsg aiPlaceholder, SseEmitter emitter) {
        try {
            ChatMsgTo chatMsg = new ChatMsgTo();
            chatMsg.setLlmId(llmId);
            chatMsg.setMsgContent(msgContent);
            chatMsg.setUserId(userId);

            String resultJson = chatClient.chatMsg(chatMsg);
            // REST 路径返回的是结构化 JSON（含 blocks + emotion），不需要 strip XML 标签
            M<String> msg = JSON.parseObject(resultJson, new TypeReference<>() {});
            String data = msg.getData();

            aiPlaceholder.setMsgContent(data);
            aiPlaceholder.setStatus(1);
            llmChatMsgService.updateById(aiPlaceholder);

            // SSE 整段推
            emitter.send(SseEmitter.event().name("full").data(data));
            emitter.send(SseEmitter.event().name("done").data(""));
            emitter.complete();
        } catch (Exception ex) {
            log.error("[SSE] REST 降级也失败: {}", ex.getMessage());
            aiPlaceholder.setStatus(4);
            aiPlaceholder.setMsgContent("回复失败，请重试");
            llmChatMsgService.updateById(aiPlaceholder);
            emitter.completeWithError(ex);
        }
    }

    private LlmChatMsg buildLlmChatMsg(String msgContent, String llmId, String userId, Boolean isHuman, Integer status) {
        LlmChatMsg chatMsg = new LlmChatMsg();
        chatMsg.setMsgContent(msgContent);
        chatMsg.setLlmId(llmId);
        chatMsg.setSendUserId(userId);
        chatMsg.setIsHuman(isHuman);
        chatMsg.setStatus(status);
        chatMsg.setCreateTime(LocalDateTime.now());
        return chatMsg;
    }

    /**
     * 将当前正在构建的 block 收入 blocks 列表并清空 buffer
     */
    private static void flushCurrentBlock(
        java.util.List<java.util.Map<String, String>> blocks,
        StringBuilder currentBlockContent,
        String[] currentBlockType
    ) {
        if (currentBlockType[0] != null && currentBlockContent.length() > 0) {
            java.util.Map<String, String> block = new java.util.LinkedHashMap<>();
            block.put("type", currentBlockType[0]);
            block.put("content", currentBlockContent.toString());
            blocks.add(block);
            currentBlockContent.setLength(0);
        }
    }

    /**
     * 构建当前 blocks 快照（含尚未 flush 的 current block）
     */
    private static java.util.List<java.util.Map<String, String>> buildBlockSnapshot(
        java.util.List<java.util.Map<String, String>> blocks,
        StringBuilder currentBlockContent,
        String[] currentBlockType
    ) {
        java.util.List<java.util.Map<String, String>> snapshot = new java.util.ArrayList<>(blocks);
        if (currentBlockType[0] != null && currentBlockContent.length() > 0) {
            java.util.Map<String, String> current = new java.util.LinkedHashMap<>();
            current.put("type", currentBlockType[0]);
            current.put("content", currentBlockContent.toString());
            snapshot.add(current);
        }
        return snapshot;
    }
}
