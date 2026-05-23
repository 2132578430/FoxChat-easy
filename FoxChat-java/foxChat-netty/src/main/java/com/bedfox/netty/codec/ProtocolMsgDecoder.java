package com.bedfox.netty.codec;

import com.bedfox.common.constant.ProtocolConstant;
import com.bedfox.pojo.domain.ChatProtocol;
import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.MessageToMessageDecoder;
import io.netty.handler.codec.http.websocketx.BinaryWebSocketFrame;
import lombok.extern.slf4j.Slf4j;

import java.util.List;

/**
 * 4b - Magic Number
 * 1b - Version
 * 1b - Serialization
 * 2b - MsgType
 * 4b - Data Length
 * 4b - Reserved
 *
 * @author bedFox
 */
@Slf4j
public class ProtocolMsgDecoder extends MessageToMessageDecoder<BinaryWebSocketFrame> {
    @Override
    protected void decode(ChannelHandlerContext channelHandlerContext, BinaryWebSocketFrame frame, List<Object> list) throws Exception {
        ByteBuf byteBuf = frame.content();
        // 如果数据小于16字节直接拦截
        if (byteBuf.readableBytes() < 16) {
            return ;
        }

        // 标记数据游标开始的位置
        byteBuf.markReaderIndex();

        int magicNumber = byteBuf.readInt();

        // 非法包
        if (!ProtocolConstant.MAGIC_NUMBER.equals(magicNumber)) {
            channelHandlerContext.close();
             return ;
        }

        byte version = byteBuf.readByte();
        byte serialization = byteBuf.readByte();
        short type = byteBuf.readShort();
        int dataLength = byteBuf.readInt();
        int reserved = byteBuf.readInt();

        // 判断数据长度是否足够
        if (byteBuf.readableBytes() < dataLength) {
            // 将二进制游标回退到标记位置
            byteBuf.resetReaderIndex();
            return ;
        }

        // 将chatMsg读入到数组中
        byte[] arr = new byte[dataLength];
        byteBuf.readBytes(arr);

        // 将数组中的数据转化为protocol对象
        ChatProtocol.Message msgDto = ChatProtocol.Message.parseFrom(arr);
        list.add(msgDto);
    }
}
