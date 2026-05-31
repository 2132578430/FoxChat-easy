package com.bedfox.service.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * RabbitMQ 配置：死信队列
 * <p>
 * 正常队列 (rag.queue / chat.queue) 绑定死信交换机，消费者处理失败且重试超过
 * {@value #MAX_RETRY_COUNT} 次后，消息自动路由到死信队列。
 * <p>
 * 重试次数由消费者端读取 {@code x-death} header 判定，此处 MAX_RETRY_COUNT 仅作文档说明。
 *
 * @author bedFox
 * @date 2026/3/14 21:42
 */
@Configuration
public class RagRabbitMqConfig {
    /**
     * rag交换机
     */
    public final static String RAG_EXCHANGE = "rag.exchange";

    /**
     * rag队列
     */
    public final static String RAG_QUEUE = "rag.queue";

    /**
     * 聊天队列
     */
    public final static String CHAT_QUEUE = "chat.queue";

    /**
     * rag绑定路径
     */
    public final static String RAG_KEY = "rag.key.#";

    /**
     * 聊天记忆
     */
    public final static String CHAT_KEY = "chat.key.#";

    // ================= 死信队列常量 =================

    /** RAG 死信交换机 */
    public final static String RAG_DLX_EXCHANGE = "rag.dlx.exchange";

    /** RAG 死信队列 */
    public final static String RAG_DLX_QUEUE = "rag.dlx.queue";

    /** RAG 死信路由键 */
    public final static String RAG_DLX_KEY = "rag.dlx.key";

    /** 聊天死信交换机 */
    public final static String CHAT_DLX_EXCHANGE = "chat.dlx.exchange";

    /** 聊天死信队列 */
    public final static String CHAT_DLX_QUEUE = "chat.dlx.queue";

    /** 聊天死信路由键 */
    public final static String CHAT_DLX_KEY = "chat.dlx.key";

    /** 最大重试次数（消费者端读取 x-death header 判定） */
    public final static int MAX_RETRY_COUNT = 3;

    // ================= 正常交换机 =================

    @Bean
    public TopicExchange topicExchange() {
        return new TopicExchange(RAG_EXCHANGE);
    }

    // ================= 正常队列（绑定死信） =================

    @Bean
    public Queue ragQueue() {
        return QueueBuilder.durable(RAG_QUEUE)
                .deadLetterExchange(RAG_DLX_EXCHANGE)
                .deadLetterRoutingKey(RAG_DLX_KEY)
                .build();
    }

    @Bean
    public Queue chatQueue() {
        return QueueBuilder.durable(CHAT_QUEUE)
                .deadLetterExchange(CHAT_DLX_EXCHANGE)
                .deadLetterRoutingKey(CHAT_DLX_KEY)
                .build();
    }

    @Bean
    public Binding binding(TopicExchange topicExchange, Queue ragQueue) {
        return BindingBuilder.bind(ragQueue).to(topicExchange).with(RAG_KEY);
    }

    @Bean
    public Binding chatBinding(TopicExchange topicExchange, Queue chatQueue) {
        return BindingBuilder.bind(chatQueue).to(topicExchange).with(CHAT_KEY);
    }

    // ================= 死信交换机 =================

    @Bean
    public TopicExchange ragDlxExchange() {
        return new TopicExchange(RAG_DLX_EXCHANGE);
    }

    @Bean
    public TopicExchange chatDlxExchange() {
        return new TopicExchange(CHAT_DLX_EXCHANGE);
    }

    // ================= 死信队列 =================

    @Bean
    public Queue ragDlxQueue() {
        return QueueBuilder.durable(RAG_DLX_QUEUE).build();
    }

    @Bean
    public Queue chatDlxQueue() {
        return QueueBuilder.durable(CHAT_DLX_QUEUE).build();
    }

    // ================= 死信绑定 =================

    @Bean
    public Binding ragDlxBinding(TopicExchange ragDlxExchange, Queue ragDlxQueue) {
        return BindingBuilder.bind(ragDlxQueue).to(ragDlxExchange).with(RAG_DLX_KEY);
    }

    @Bean
    public Binding chatDlxBinding(TopicExchange chatDlxExchange, Queue chatDlxQueue) {
        return BindingBuilder.bind(chatDlxQueue).to(chatDlxExchange).with(CHAT_DLX_KEY);
    }
}
