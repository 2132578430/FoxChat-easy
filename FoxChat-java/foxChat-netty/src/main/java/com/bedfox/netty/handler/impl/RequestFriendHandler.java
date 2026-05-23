package com.bedfox.netty.handler.impl;

import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.common.constant.RedisConstant;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.domain.FriendsRequest;
import com.bedfox.pojo.domain.Users;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.netty.netty.UserChannelRelation;
import com.bedfox.service.service.FriendsRequestService;
import com.bedfox.common.util.ProtocolUtil;
import com.bedfox.common.util.SpringUtil;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * @author bedFox
 */
@Component
@Slf4j
public class RequestFriendHandler implements MsgHandler {

    @Autowired
    StringRedisTemplate redisTemplate;

    @Override
    public MsgTypeConstant getMsgType() {
        return MsgTypeConstant.REQUEST_FRIEND;
    }

    @Override
    public void handler(ChannelHandlerContext ctx, MsgDto msgDto) {
        ChatMsg chatMsg = msgDto.getChatMsg();

        String acceptUserId = chatMsg.getAcceptUserId();
        String sendUserId = chatMsg.getSendUserId();

        Users sender = new Users();

        sender.setId(sendUserId);

        msgDto.setSender(sender);

        log.info("捕获到发送好友");
        UserChannelRelation.output();
        // 记录请求好友记录
        sendFriendRequest(sendUserId, acceptUserId);

        // 向客户端响应信息
        Channel acceptChannel = UserChannelRelation.get(acceptUserId);

        // 判断是否在线
        if (isOnline(acceptChannel)) {
            msgDto.setType(MsgTypeConstant.PULL_FRIEND.getCode());
            redisTemplate.convertAndSend(RedisConstant.CHANNEL, ProtocolUtil.toProtocolBase64(msgDto));
        }
    }

    /**
     * 发送好友请求
     *
     * @param sendUserId
     * @param acceptUserId
     */
    private void sendFriendRequest(String sendUserId, String acceptUserId) {
        // 构建并保存请求好友信息
        FriendsRequestService friendsRequestService = (FriendsRequestService) SpringUtil.getBean(FriendsRequestService.class);

        FriendsRequest friendsRequest = new FriendsRequest();
        friendsRequest.setSendUserId(sendUserId);
        friendsRequest.setAcceptUserId(acceptUserId);
        friendsRequest.setRequestDataTime(LocalDateTime.now());

        friendsRequestService.save(friendsRequest);
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
