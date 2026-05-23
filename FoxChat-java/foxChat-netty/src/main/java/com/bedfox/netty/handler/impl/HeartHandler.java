package com.bedfox.netty.handler.impl;

import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.netty.handler.MsgHandler;
import io.netty.channel.ChannelHandlerContext;
import org.springframework.stereotype.Component;

/**
 * @author bedFox
 */
@Component
public class HeartHandler implements MsgHandler {
    @Override
    public MsgTypeConstant getMsgType() {
        return MsgTypeConstant.HEART;
    }

    @Override
    public void handler(ChannelHandlerContext ctx, MsgDto msgDto) {

    }
}
