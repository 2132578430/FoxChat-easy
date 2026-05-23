package com.bedfox.netty.netty;

import com.bedfox.netty.codec.ProtocolMsgDecoder;
import com.bedfox.netty.codec.ProtocolMsgEncoder;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelPipeline;
import io.netty.channel.socket.SocketChannel;
import io.netty.handler.codec.http.HttpObjectAggregator;
import io.netty.handler.codec.http.HttpServerCodec;
import io.netty.handler.codec.http.websocketx.WebSocketServerProtocolHandler;
import io.netty.handler.stream.ChunkedWriteHandler;
import io.netty.handler.timeout.IdleStateHandler;

/**
 * @author bedFox
 */
public class WebSocketSeverInitializer extends ChannelInitializer<SocketChannel> {
    @Override
    protected void initChannel(SocketChannel socketChannel) throws Exception {
        ChannelPipeline pipeline = socketChannel.pipeline();

        /*
          对http请求的处理器
         */
        // websocket基于http协议,需要http编码和解码工具
        pipeline.addLast("HttpServerCodec",new HttpServerCodec());
        // 对于大数据流的支持
        pipeline.addLast(new ChunkedWriteHandler());
        // 对于http的消息进行聚合,聚合成FullHttpRequest或者FullHttpResponse,几乎所有netty都需要此handler
        pipeline.addLast(new HttpObjectAggregator(1024*64));

        // WebSocket 握手 Cookie 认证 (在 WebSocketServerProtocolHandler 之前)
        pipeline.addLast("CookieAuthHandler", new CookieAuthHandler());

        /*
          心跳机制设置
         */
        pipeline.addLast(new IdleStateHandler(40, 50, 2*60));
        pipeline.addLast(new HeartBeatHandler());

        /*
          webSocket协议
           websocket服务器处理协议,用于指定给客户端访问的路由:/ws
           同时该handler会自动处理一些复杂的事情,如握手动作,handshaking ( close + ping + pong )
           ping+pong组合成心跳
         */
        pipeline.addLast(new WebSocketServerProtocolHandler("/chat"));
        pipeline.addLast(new ProtocolMsgDecoder());
        pipeline.addLast(new ProtocolMsgEncoder());
        pipeline.addLast(new ChatWebSocketHandler());

    }
}
