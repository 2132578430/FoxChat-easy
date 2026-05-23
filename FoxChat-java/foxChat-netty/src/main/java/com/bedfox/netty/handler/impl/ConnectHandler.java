package com.bedfox.netty.handler.impl;

import com.alibaba.fastjson2.JSON;
import com.bedfox.common.constant.*;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.netty.netty.ChatWebSocketHandler;
import com.bedfox.netty.netty.GroupChannelRelation;
import com.bedfox.netty.netty.UserChannelRelation;
import com.bedfox.service.service.GroupMemberService;
import com.bedfox.common.util.JwtUtil;
import com.bedfox.common.util.ProtocolUtil;
import com.bedfox.common.util.SpringUtil;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.Set;

/**
 * 连接处理器
 *
 * @author bedFox
 */
@Slf4j
@Component
public class ConnectHandler implements MsgHandler {

    @Resource(name = "stringRedisTemplate")
    StringRedisTemplate redisTemplate;

    @Resource
    GroupMemberService groupMemberService;

    @Override
    public MsgTypeConstant getMsgType() {
        return MsgTypeConstant.CONNECT;
    }

    @Override
    public void handler(ChannelHandlerContext ctx, MsgDto msgDto) {
        // 先检查是否已通过 Cookie 验证（握手时已设置 userId）
        String userId = ctx.channel().attr(ChatWebSocketHandler.USER_ID_KEY).get();

        if (userId == null) {
            // 未通过 Cookie 验证，使用 auth message 验证
            JwtUtil jwtUtil = (JwtUtil) SpringUtil.getBean(JwtUtil.class);
            String extend = msgDto.getExtend();
            userId = jwtUtil.getUserIdFromToken(extend);
            ctx.channel().attr(ChatWebSocketHandler.USER_ID_KEY).set(userId);
            log.info("用户{}通过auth message连接websocket服务器", userId);
        } else {
            log.info("用户{}已通过Cookie验证，跳过auth message", userId);
        }

        UserChannelRelation.put(userId, ctx.channel());

        // 设置登录状态
        redisTemplate.opsForValue().set(AuthConstant.PRE_ONLINE + userId, "1");

        // 向所有在线好友发送登录信息
        broadLoginToFriend(userId);

        // 将该用户通道加入到所有加入的群聊中
        addChannelGroup(ctx.channel());
    }

    private void addChannelGroup(Channel channel) {
        String userId = channel.attr(ChatWebSocketHandler.USER_ID_KEY).get();
        String groupKey = GroupConstant.GROUP_KEY + userId;
        // 从redis中取出列表
        Set<String> groupSet = redisTemplate.opsForSet().members(groupKey);

        if (groupSet != null && !groupKey.isEmpty()) {
            for (String groupId : groupSet) {
                GroupChannelRelation.addUser(groupId, channel);
            }
        }
    }

    /**
     * 向userId的所有好友广播登录信息
     * @param userId
     */
    private void broadLoginToFriend(String userId) {
        String userKey = FriendConstant.USER_FRIEND_PRE + userId;

        // 从redis获取好友列表
        Set<String> friendSet = redisTemplate.opsForSet().members(userKey);

        if (friendSet != null && !friendSet.isEmpty()) {
            // 构建信息
            MsgDto msgDto = new MsgDto();
            ChatMsg chatMsg = new ChatMsg();

            msgDto.setType(MsgTypeConstant.FRIEND_ONLINE.getCode());
            chatMsg.setSendUserId(userId);

            // 向好友发信息
            for (String friendId : friendSet) {
                chatMsg.setAcceptUserId(friendId);
                msgDto.setChatMsg(chatMsg);

                // 通过redis广播
                redisTemplate.convertAndSend(RedisConstant.CHANNEL, ProtocolUtil.toProtocolBase64(msgDto));
                log.info("为好友：{}发送上线信息:{}",friendId, JSON.toJSONString(msgDto));
            }
        }
    }
}
