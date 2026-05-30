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
}
