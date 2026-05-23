package com.bedfox.common.constant;

/**
 * @author bedFox
 * @date 2026/3/29 22:35
 */
public class MqConstant {
    public static class RagRabbitMqConstant {
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
    }
}
