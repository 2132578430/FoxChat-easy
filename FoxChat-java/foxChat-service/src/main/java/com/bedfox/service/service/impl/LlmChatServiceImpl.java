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

    /**
     * 导演模式聊天
     */
    @Override
    public LlmChatMsgVo llmSuperChat(String llmId, String msgContent, String userId) {
        log.info("【导演模式】聊天请求：userId={}, llmId={}, msgContent={}", userId, llmId, msgContent);

        // 1. 保存用户消息 status=SENT(0)
        LlmChatMsg llmChatMsgHuman = buildLlmChatMsg(msgContent, llmId, userId, true, 0);
        llmChatMsgService.save(llmChatMsgHuman);
        log.debug("【导演模式】用户消息已保存，status=SENT(0)");

        // 2. 创建并保存AI占位消息 status=PROCESSING(3)
        LlmChatMsg aiPlaceholder = buildLlmChatMsg("思考中...", llmId, userId, false, 3);
        llmChatMsgService.save(aiPlaceholder);
        log.debug("【导演模式】AI占位消息已保存，status=PROCESSING(3)");

        // 构建请求对象
        ChatMsgTo chatMsg = new ChatMsgTo();
        chatMsg.setLlmId(llmId);
        chatMsg.setMsgContent(msgContent);
        chatMsg.setUserId(userId);

        try {
            // 3. 调用导演模式专用接口
            log.info("【导演模式】开始调用 Python superChatMsg 接口...");
            String resultJson = chatClient.superChatMsg(chatMsg);
            log.info("【导演模式】收到 Python 响应：{}", resultJson);

            // 4. 解析响应
            M<String> msg = JSON.parseObject(resultJson, new TypeReference<M<String>>() {});
            String data = msg.getData();

            if (data == null || data.isEmpty()) {
                log.warn("【导演模式】Python 返回数据为空");
                throw new BusinessException(ResultStatusConstant.LLM_FAILED);
            }

            // 5. 更新占位消息为 SAVED(1)，填入真实AI回复
            aiPlaceholder.setStatus(1);
            aiPlaceholder.setMsgContent(data);
            llmChatMsgService.updateById(aiPlaceholder);
            log.info("【导演模式】AI回复已更新，status=SAVED(1)");

            // 6. 返回成功VO
            LlmChatMsgVo chatMsgVo = new LlmChatMsgVo();
            chatMsgVo.setMsg(data);
            log.info("【导演模式】聊天完成：userId={}, llmId={}", userId, llmId);
            return chatMsgVo;

        } catch (Exception e) {
            log.error("【导演模式】Python调用失败", e);

            // 7. 更新占位消息为 FAILED(4)
            aiPlaceholder.setStatus(4);
            aiPlaceholder.setMsgContent("回复失败，请重试");
            llmChatMsgService.updateById(aiPlaceholder);
            log.warn("【导演模式】AI占位消息已标记为 FAILED(4)");

            // 8. 抛出异常让Controller返回错误给前端
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
