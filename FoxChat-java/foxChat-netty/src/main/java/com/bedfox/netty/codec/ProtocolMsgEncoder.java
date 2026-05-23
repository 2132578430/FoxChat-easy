package com.bedfox.netty.codec;

import com.bedfox.common.constant.ProtocolConstant;
import com.bedfox.pojo.domain.ChatProtocol;
import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.MessageToMessageEncoder;
import io.netty.handler.codec.http.websocketx.BinaryWebSocketFrame;

import java.util.List;

/**
 *  * 4b - Magic Number
 *  * 1b - Version
 *  * 1b - Serialization
 *  * 2b - MsgType
 *  * 4b - Data Length
 *  * 4b - Reserved
 *
 * @author bedFox
 */
public class ProtocolMsgEncoder extends MessageToMessageEncoder<ChatProtocol.Message> {
    @Override
    protected void encode(ChannelHandlerContext ctx, ChatProtocol.Message chatMsg, List<Object> list) throws Exception {
        ByteBuf buffer = null;
        try {
            byte[] bytes = chatMsg.toByteArray();
            int length = bytes.length;

            // 申请内存空间，协议头+消息本体
            buffer = ctx.alloc().buffer(16 + length);

            // 写入数据体
            buffer.writeInt(ProtocolConstant.MAGIC_NUMBER);
            buffer.writeByte(ProtocolConstant.VERSION);
            buffer.writeByte(ProtocolConstant.SERIAL);
            buffer.writeShort(chatMsg.getType());
            buffer.writeInt(length);
            buffer.writeInt(0);

            buffer.writeBytes(bytes);

            // 包装成websocket二进制帧发送到前端
            list.add(new BinaryWebSocketFrame(buffer));

            buffer = null;
        } finally {
            if (buffer != null) {
                buffer = null;
            }
        }
    }
}
