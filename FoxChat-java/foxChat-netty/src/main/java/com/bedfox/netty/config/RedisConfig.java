package com.bedfox.netty.config;

import com.bedfox.common.constant.RedisConstant;
import com.bedfox.netty.listener.RedisMessageListener;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;

/**
 * @author bedFox
 */
@Configuration
public class RedisConfig {
    /**
     * redis消息订阅器，所有websocket会自动订阅redis的CHAT频道
     * @param connectionFactory
     * @param listener
     * @return
     */
    @Bean
    public RedisMessageListenerContainer container(RedisConnectionFactory connectionFactory, RedisMessageListener listener) {
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);

        // 订阅名为 "CHAT_CHANNEL" 的频道
        container.addMessageListener(listener, new ChannelTopic(RedisConstant.CHANNEL));
        return container;
    }
}
