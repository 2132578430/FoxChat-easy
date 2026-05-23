package com.bedfox.service.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
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

    @Bean
    public TopicExchange topicExchange() {
        return new TopicExchange(RAG_EXCHANGE);
    }

    @Bean
    public Queue ragQueue() {
        return new Queue(RAG_QUEUE, true);
    }

    @Bean
    public Queue chatQueue() {
        return new Queue(CHAT_QUEUE, true);
    }

    @Bean
    public Binding binding(TopicExchange topicExchange, Queue ragQueue) {
        return BindingBuilder.bind(ragQueue).to(topicExchange).with(RAG_KEY);
    }

    @Bean
    public Binding chatBinding(TopicExchange topicExchange, Queue chatQueue) {
        return BindingBuilder.bind(chatQueue).to(topicExchange).with(CHAT_KEY);
    }
}
