package com.bedfox.netty.handler.impl;

import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.common.constant.RedisConstant;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.netty.handler.MsgHandler;
import com.bedfox.service.service.ChatMsgService;
import com.bedfox.common.util.SpringUtil;
import io.netty.channel.ChannelHandlerContext;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * @author bedFox
 */
@Slf4j
@Component
public class SignMsgHandler implements MsgHandler {

    @Autowired
    StringRedisTemplate redisTemplate;

    @Override
    public MsgTypeConstant getMsgType() {
        return MsgTypeConstant.SIGNED;
    }

    @Override
    public void handler(ChannelHandlerContext ctx, MsgDto msgDto) {
        String extend = msgDto.getExtend();
        ChatMsg chatMsg = msgDto.getChatMsg();
        String sendUserId = chatMsg.getSendUserId();

        log.info("签收信息：{}", chatMsg.getMsg());

        ChatMsgService chatMsgService = (ChatMsgService) SpringUtil.getBean(ChatMsgService.class);

        String[] msgIds = extend.split(",", -1);

        List<String> msgIdList = new ArrayList<>();
        String msgKey = RedisConstant.MSG_PRE + sendUserId;

        for (String msgId : msgIds) {
            if (!StringUtils.isEmpty(msgId)) {
                msgIdList.add(msgId);

                redisTemplate.opsForSet().remove(msgKey, msgId);
            }
        }

        if (!msgIdList.isEmpty()) {
            chatMsgService.signMsg(msgIdList);
        }
    }
}
