package com.bedfox.common.util;

import com.alibaba.fastjson2.JSON;
import com.bedfox.common.constant.MqConstant;
import jakarta.annotation.Resource;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

/**
 * 向mq发送信息，并进行自动封装信息
 * 发送类型为M
 *
 * @author bedFox
 * @date 2026/3/15 12:13
 */
@Component
public class MqUtil {
    public final static String RAG_KEY_UPLOAD = "rag.key.upload";

    public final static String CHAT_KEY_UPLOAD = "chat.key.upload";

    @Resource
    public RabbitTemplate rabbitTemplate;

    public <T> void sendRagUploadMsg(T data) {
        sendMsg(
                MqConstant.RagRabbitMqConstant.RAG_EXCHANGE,
                RAG_KEY_UPLOAD,
                data
        );
    }

    public <T> void sendChatMsg(T data) {
        sendMsg(
                MqConstant.RagRabbitMqConstant.RAG_EXCHANGE,
                CHAT_KEY_UPLOAD,
                data
        );
    }

    private <T> void sendMsg(String exchange, String key, T data) {
        // 将数据包装成M对象
        M<T> msg = M.getMsg(data);

        String msgJson = JSON.toJSONString(msg);

        rabbitTemplate.convertAndSend(
                exchange,
                key,
                msgJson
        );
    }


}
