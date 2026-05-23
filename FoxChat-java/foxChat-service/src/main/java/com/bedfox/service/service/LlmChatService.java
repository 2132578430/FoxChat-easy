package com.bedfox.service.service;

import com.bedfox.pojo.vo.LlmChatMsgVo;

/**
* @author 21325
* @description LLM聊天Service
* @createDate 2026-04-29
*/
public interface LlmChatService {

    // 模型聊天主逻辑
    LlmChatMsgVo llmChat(String llmId, String msgContent, String userId);

    // 导演模式聊天
    LlmChatMsgVo llmSuperChat(String llmId, String msgContent, String userId);
}