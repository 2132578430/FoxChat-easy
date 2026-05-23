package com.bedfox.netty.handler.impl;

import com.alibaba.fastjson2.JSON;
import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.common.constant.RedisConstant;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.netty.netty.ChatWebSocketHandler;
import com.bedfox.netty.netty.UserChannelRelation;
import com.bedfox.service.service.ChatMsgService;
import com.bedfox.common.util.ProtocolUtil;
import com.bedfox.common.util.SpringUtil;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * @author bedFox
 */
@Slf4j
@Component
public class ChatHandler implements MsgHandler {

    @Resource(name = "stringRedisTemplate")
    StringRedisTemplate redisTemplate;

    @Override
    public MsgTypeConstant getMsgType() {
        return MsgTypeConstant.CHAT;
    }

    @Override
    public void handler(ChannelHandlerContext ctx, MsgDto msgDto) {
        ChatMsg chatMsg = msgDto.getChatMsg();
        String acceptUserId = chatMsg.getAcceptUserId();
        String sendUserId = chatMsg.getSendUserId();

        log.info("用户ID{}：发送信息：{}", ctx.channel().attr(ChatWebSocketHandler.USER_ID_KEY).get(), chatMsg.getMsg());
        // 构建并保存ChatMsg（createTime，signFlag自动赋值）
        ChatMsgService chatMsgService = (ChatMsgService) SpringUtil.getBean(ChatMsgService.class);
        // 保存信息数据到数据库中
        String msgId = chatMsgService.saveMsg(chatMsg);

        // 构建MsgDto
        msgDto.setExtend(msgId);

        // 检查接收用户是否在线
        Channel acceptChannel = UserChannelRelation.get(acceptUserId);
        if (isOnline(acceptChannel)) {
            // 通过通道发送信息给用户
            log.info("发送信息：{}", JSON.toJSONString(msgDto));

            // 校验用户是否已经发过该信息
            String msgKey = RedisConstant.MSG_PRE + sendUserId;

            if (redisTemplate.opsForSet().add(msgKey, msgId) == 0) {
                return;
            }

            // 将该信息储存到redis中
            redisTemplate.opsForSet().add(msgKey, msgId);

            redisTemplate.convertAndSend(RedisConstant.CHANNEL, ProtocolUtil.toProtocolBase64(msgDto));
        }
    }

    /**
     * 判断通道对应的用户是否在线
     * @param acceptChannel
     * @return
     */
    private static boolean isOnline(Channel acceptChannel) {
        return acceptChannel != null && acceptChannel.isOpen();
    }
}
