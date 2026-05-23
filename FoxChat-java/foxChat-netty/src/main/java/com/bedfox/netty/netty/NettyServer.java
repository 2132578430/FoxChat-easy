package com.bedfox.netty.netty;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.Channel;
import io.netty.channel.ChannelOption;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

/**
 * @author bedFox
 */
@Configuration
@Slf4j
public class NettyServer {

    @Value("${FoxNetty.config.port}")
    private int port;

    private Channel syncChannel;

    // 配置bossGroup组和workGroup组
    private final NioEventLoopGroup bossGroup = new NioEventLoopGroup(1);
    private final NioEventLoopGroup workGroup = new NioEventLoopGroup();

    @PostConstruct
    public void initNetty() {
        ServerBootstrap bootstrap = new ServerBootstrap();

        bootstrap.group(bossGroup, workGroup)
                .channel(NioServerSocketChannel.class)
                .option(ChannelOption.SO_BACKLOG, 128)
                .childOption(ChannelOption.SO_KEEPALIVE, true)
                .childHandler(new WebSocketSeverInitializer());

        log.info("Netty服务器核心组件启动成功......");

        try {
            syncChannel = bootstrap.bind(port).sync().channel();
            log.info("Netty服务器绑定端口{}成功", port);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Netty服务器启动被中断", e);
        }
    }

    @PreDestroy
    public void nettyClose() {
        if (syncChannel != null) {
            syncChannel.closeFuture();
        }

        bossGroup.shutdownGracefully();
        workGroup.shutdownGracefully();
    }
}
