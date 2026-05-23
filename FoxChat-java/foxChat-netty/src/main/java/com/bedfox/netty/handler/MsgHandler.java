package com.bedfox.netty.handler;

import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.pojo.dto.MsgDto;
import io.netty.channel.ChannelHandlerContext;

/**
 * @author bedFox
 */
public interface MsgHandler {
    // 获取处理器对应的消息种类
    MsgTypeConstant getMsgType();

    // 消息处理
    void handler(ChannelHandlerContext ctx, MsgDto msgDto);
}
