package com.bedfox.netty.handler.impl;

import com.bedfox.common.constant.MsgTargetTypeConstant;
import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.common.constant.RedisConstant;
import com.bedfox.pojo.domain.GroupMsg;
import com.bedfox.pojo.domain.Users;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.netty.netty.ChatWebSocketHandler;
import com.bedfox.netty.netty.GroupChannelRelation;
import com.bedfox.service.service.GroupMsgService;
import com.bedfox.service.service.UsersService;
import com.bedfox.common.util.ProtocolUtil;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.group.ChannelGroup;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * @author bedFox
 */
@Slf4j
@Component
public class GroupChatHandler implements MsgHandler {

    @Autowired
    GroupMsgService groupMsgService;

    @Autowired
    StringRedisTemplate redisTemplate;

    @Autowired
    UsersService usersService;

    @Override
    public MsgTypeConstant getMsgType() {
        return MsgTypeConstant.GROUP_CHAT;
    }

    @Override
    public void handler(ChannelHandlerContext ctx, MsgDto msgDto) {
        GroupMsg groupMsg = msgDto.getGroupMsg();
        String sendUserId = ctx.channel().attr(ChatWebSocketHandler.USER_ID_KEY).get();
        String groupId = groupMsg.getGroupId();

        // 保存群聊信息记录
        groupMsg.setSendUserId(sendUserId);
        groupMsg.setCreateTime(LocalDateTime.now());

        groupMsgService.save(groupMsg);

        // 构建msgDto
        msgDto.setTargetType(MsgTargetTypeConstant.GROUP_CHAT);

        // 构建发送人信息
        Users users = usersService.buildSender(sendUserId);

        msgDto.setSender(users);

        // 发送信息
        ChannelGroup channelGroup = GroupChannelRelation.get(groupId);

        redisTemplate.convertAndSend(RedisConstant.CHANNEL, ProtocolUtil.toProtocolBase64(msgDto));
    }
}
