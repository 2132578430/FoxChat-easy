package com.bedfox.netty.listener;

import com.bedfox.common.constant.MsgTargetTypeConstant;
import com.bedfox.pojo.domain.ChatProtocol;
import com.bedfox.netty.netty.ChatWebSocketHandler;
import com.bedfox.netty.netty.GroupChannelRelation;
import com.bedfox.netty.netty.UserChannelRelation;
import com.google.protobuf.InvalidProtocolBufferException;
import io.netty.channel.Channel;
import io.netty.channel.group.ChannelGroup;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.stereotype.Component;

import java.util.Base64;

/**
 * 监听redis分配来的数据
 *
 * @author bedFox
 */
@Slf4j
@Component
public class RedisMessageListener implements MessageListener {
    @Override
    public void onMessage(Message message, byte[] pattern) {
        String base64Msg = new String(message.getBody());
        try {
            byte[] msgDecode = Base64.getDecoder().decode(base64Msg);
            ChatProtocol.Message msgProtocol = ChatProtocol.Message.parseFrom(msgDecode);

            int targetType = msgProtocol.getTargetType();

            // 判断redis广播类型
            if (MsgTargetTypeConstant.GROUP_CHAT.equals(targetType)) {
                // 群聊信息
                ChatProtocol.GroupMsg groupMsg = msgProtocol.getGroupMsg();
                String groupId = groupMsg.getGroupId();

                ChannelGroup group = GroupChannelRelation.get(groupId);

                if (group != null) {
                    for (Channel channel : group) {
                        log.info("发送信息给：{}",channel.attr(ChatWebSocketHandler.USER_ID_KEY).get());
                    }
                    group.writeAndFlush(msgProtocol);
                }
            } else {
                // 私人信息
                ChatProtocol.ChatMsg chatMsg = msgProtocol.getChatMsg();
                String acceptUserId = chatMsg.getAcceptUserId();

                Channel channel = UserChannelRelation.get(acceptUserId);
                if (channel != null && channel.isOpen()) {
                    channel.writeAndFlush(msgProtocol);
                }
            }
        } catch (InvalidProtocolBufferException e) {
            log.error("redis解码失败:{}",e.getMessage());
        }
    }
}
