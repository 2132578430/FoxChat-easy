package com.bedfox.service.service;

import com.bedfox.pojo.vo.LlmChatMsgVo;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
* @author 21325
* @description LLM聊天Service
* @createDate 2026-04-29
*/
public interface LlmChatService {

    // 模型聊天主逻辑
    LlmChatMsgVo llmChat(String llmId, String msgContent, String userId);

    // 流式聊天（SSE），内部使用 gRPC streaming
    SseEmitter llmChatStream(String llmId, String msgContent, String userId);
}