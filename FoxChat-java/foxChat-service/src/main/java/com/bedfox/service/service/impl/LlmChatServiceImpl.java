package com.bedfox.service.service.impl;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.bedfox.common.util.M;
import com.bedfox.pojo.domain.LlmChatMsg;
import com.bedfox.pojo.to.ChatMsgTo;
import com.bedfox.pojo.vo.LlmChatMsgVo;
import com.bedfox.service.remote.ChatClient;
import com.bedfox.service.service.LlmChatMsgService;
import com.bedfox.service.service.LlmChatService;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

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
    LlmChatMsgService llmChatMsgService;

    /**
     * 聊天主逻辑
     */
    @Override
    public LlmChatMsgVo llmChat(String llmId, String msgContent, String userId) {
        // 保存用户消息
        LlmChatMsg llmChatMsgHuman = buildLlmChatMsg(msgContent, llmId, userId, true);
        llmChatMsgService.save(llmChatMsgHuman);

        ChatMsgTo chatMsg = new ChatMsgTo();
        chatMsg.setLlmId(llmId);
        chatMsg.setMsgContent(msgContent);
        chatMsg.setUserId(userId);

        String resultJson = chatClient.chatMsg(chatMsg);

        log.info("接收到消息：{}", resultJson);

        resultJson = resultJson.replaceAll("</?[a-zA-Z_]+>", "");

        M<String> msg = JSON.parseObject(resultJson, new TypeReference<>() {});
        String data = msg.getData();

        // 保存模型消息
        LlmChatMsg llmChatMsgAi = buildLlmChatMsg(data, llmId, userId, false);
        llmChatMsgService.save(llmChatMsgAi);

        LlmChatMsgVo chatMsgVo = new LlmChatMsgVo();
        chatMsgVo.setMsg(data);

        return chatMsgVo;
    }

    /**
     * 导演模式聊天
     */
    @Override
    public LlmChatMsgVo llmSuperChat(String llmId, String msgContent, String userId) {
        log.info("【导演模式】聊天请求：userId={}, llmId={}, msgContent={}", userId, llmId, msgContent);

        // 保存用户消息
        LlmChatMsg llmChatMsgHuman = buildLlmChatMsg(msgContent, llmId, userId, true);
        llmChatMsgService.save(llmChatMsgHuman);
        log.debug("【导演模式】用户消息已保存到数据库");

        // 构建请求对象
        ChatMsgTo chatMsg = new ChatMsgTo();
        chatMsg.setLlmId(llmId);
        chatMsg.setMsgContent(msgContent);
        chatMsg.setUserId(userId);

        // 调用导演模式专用接口
        log.info("【导演模式】开始调用 Python superChatMsg 接口...");
        String resultJson = chatClient.superChatMsg(chatMsg);
        log.info("【导演模式】收到 Python 响应：{}", resultJson);

        // 解析响应
        M<String> msg = JSON.parseObject(resultJson, new TypeReference<M<String>>() {});
        String data = msg.getData();

        if (data == null || data.isEmpty()) {
            log.warn("【导演模式】Python 返回数据为空");
            data = "抱歉，导演模式暂时无法回应...";
        }

        // 保存模型消息
        LlmChatMsg llmChatMsgAi = buildLlmChatMsg(data, llmId, userId, false);
        llmChatMsgService.save(llmChatMsgAi);
        log.debug("【导演模式】AI 回复已保存到数据库");

        LlmChatMsgVo chatMsgVo = new LlmChatMsgVo();
        chatMsgVo.setMsg(data);

        log.info("【导演模式】聊天完成：userId={}, llmId={}", userId, llmId);
        return chatMsgVo;
    }

    private LlmChatMsg buildLlmChatMsg(String msgContent, String llmId, String userId, Boolean isHuman) {
        LlmChatMsg chatMsg = new LlmChatMsg();
        chatMsg.setMsgContent(msgContent);
        chatMsg.setLlmId(llmId);
        chatMsg.setSendUserId(userId);
        chatMsg.setIsHuman(isHuman);
        chatMsg.setCreateTime(LocalDateTime.now());
        return chatMsg;
    }
}