package com.bedfox.netty.netty;

import com.bedfox.common.constant.AuthConstant;
import com.bedfox.common.constant.FriendConstant;
import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.common.constant.RedisConstant;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.domain.ChatProtocol;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.netty.handler.ChatHandlerFactory;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.common.util.ProtocolUtil;
import com.bedfox.common.util.SpringUtil;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.SimpleChannelInboundHandler;
import io.netty.channel.group.ChannelGroup;
import io.netty.channel.group.DefaultChannelGroup;
import io.netty.util.AttributeKey;
import io.netty.util.concurrent.GlobalEventExecutor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.Set;

/**
 * @author bedFox
 */
@Slf4j
@Component
public class ChatWebSocketHandler extends SimpleChannelInboundHandler<ChatProtocol.Message> {

    public static ChannelGroup userChannel = new DefaultChannelGroup(GlobalEventExecutor.INSTANCE);

    public static final AttributeKey<String> USER_ID_KEY = AttributeKey.valueOf("userId");

    @Transactional
    @Override
    protected void channelRead0(ChannelHandlerContext ctx, ChatProtocol.Message text) throws Exception {
        MsgDto msgDto = ProtocolUtil.protocolToMsgDto(text);

        // 信息类型分发
        MsgHandler handler = ChatHandlerFactory.getHandler(msgDto.getType());

        if (handler != null) {
            handler.handler(ctx, msgDto);
        }
    }
    /**
     * 建立连接就将通道加入到通道管理器
     * @param ctx
     * @throws Exception
     */
    @Override
    public void handlerAdded(ChannelHandlerContext ctx) throws Exception {
        userChannel.add(ctx.channel());
    }


    /**
     * 移除Channel
     * @param ctx
     * @throws Exception
     */
    @Override
    public void handlerRemoved(ChannelHandlerContext ctx) throws Exception {
        // 清除channelGroup中的连接
        onlineClear(ctx);
    }

    @Override
    public void channelInactive(ChannelHandlerContext ctx) throws Exception {
        // 广播用户下线通知
        boardLogOut(ctx.channel());
        super.channelInactive(ctx);
    }

    private void boardLogOut(Channel channel) {
        try {
            StringRedisTemplate redisTemplate = (StringRedisTemplate) SpringUtil.getBean(StringRedisTemplate.class);
            String userKey = FriendConstant.USER_FRIEND_PRE + channel.attr(USER_ID_KEY).get();

            // 检索到所有好友的Id
            Set<String> friendSet = redisTemplate.opsForSet().members(userKey);

            MsgDto msgDto = new MsgDto();
            ChatMsg chatMsg = new ChatMsg();

            msgDto.setType(MsgTypeConstant.USER_LOGOUT.getCode());
            chatMsg.setSendUserId(channel.attr(USER_ID_KEY).get());

            if (friendSet != null && !friendSet.isEmpty()) {
                for (String friendId : friendSet) {
                    chatMsg.setAcceptUserId(friendId);
                    msgDto.setChatMsg(chatMsg);

                    redisTemplate.convertAndSend(RedisConstant.CHANNEL, ProtocolUtil.toProtocolBase64(msgDto));
                }
            }
        } catch (IllegalStateException e) {
            // Redis连接工厂已停止（应用关闭时），忽略此异常
            log.warn("Redis连接已关闭，跳过广播下线通知: {}", e.getMessage());
        }
    }

    /**
     * websocket连接异常
     * @param ctx
     * @param cause
     * @throws Exception
     */
    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) throws Exception {
        log.error("Netty服务器核心组件错误！");
        log.error("netty核心组件异常：{}:{}", cause.toString(), cause.getMessage());
        onlineClear(ctx);
    }

    private void onlineClear(ChannelHandlerContext ctx) {
        userChannel.remove(ctx.channel());

        String userId = ctx.channel().attr(USER_ID_KEY).get();
        if (userId != null) {
            UserChannelRelation.remove(userId, ctx.channel());

            // 清除 Redis 中的在线状态
            try {
                StringRedisTemplate redisTemplate = (StringRedisTemplate) SpringUtil.getBean(StringRedisTemplate.class);
                redisTemplate.delete(AuthConstant.PRE_ONLINE + userId);
            } catch (IllegalStateException e) {
                // Redis连接工厂已停止（应用关闭时），忽略此异常
                log.warn("Redis连接已关闭，跳过清除在线状态: {}", e.getMessage());
            }
        }
    }
}
