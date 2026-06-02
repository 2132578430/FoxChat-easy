package com.bedfox.netty.publisher;

import com.bedfox.common.constant.RedisConstant;
import com.bedfox.common.util.ProtocolUtil;
import com.bedfox.pojo.dto.MsgDto;
import jakarta.annotation.Resource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * 消息发布器 —— 向 Redis Pub/Sub 频道发布消息，用于跨 Netty 节点广播
 *
 * @author bedFox
 */
@Component
public class MsgPublisher {

    @Resource(name = "stringRedisTemplate")
    private StringRedisTemplate redisTemplate;

    /**
     * 发布消息到 Redis 频道
     *
     * @param msgDto 消息体
     */
    public void publish(MsgDto msgDto) {
        redisTemplate.convertAndSend(RedisConstant.CHANNEL, ProtocolUtil.toProtocolBase64(msgDto));
    }
}
