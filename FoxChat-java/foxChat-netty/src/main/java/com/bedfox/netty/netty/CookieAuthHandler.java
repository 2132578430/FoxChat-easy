package com.bedfox.netty.netty;

import com.bedfox.common.constant.AuthConstant;
import com.bedfox.common.util.JwtUtil;
import com.bedfox.common.util.SpringUtil;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;
import io.netty.handler.codec.http.FullHttpRequest;
import io.netty.handler.codec.http.HttpHeaders;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;

/**
 * WebSocket 握手 Cookie 认证 Handler
 * 在握手阶段从 HTTP headers 解析 Cookie 验证 token
 *
 * @author bedFox
 */
@Slf4j
public class CookieAuthHandler extends ChannelInboundHandlerAdapter {

    private static final String TOKEN_COOKIE_NAME = "token";

    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) throws Exception {
        if (msg instanceof FullHttpRequest) {
            FullHttpRequest request = (FullHttpRequest) msg;

            // 从 HTTP headers 获取 Cookie 中的 token
            String token = getTokenFromCookie(request.headers());

            if (token != null && !token.isEmpty()) {
                try {
                    JwtUtil jwtUtil = (JwtUtil) SpringUtil.getBean(JwtUtil.class);
                    StringRedisTemplate redisTemplate = (StringRedisTemplate) SpringUtil.getBean("stringRedisTemplate");

                    // 验证 JWT
                    if (jwtUtil.validateToken(token)) {
                        String authKey = AuthConstant.PRE_LOGIN_AUTH + token;
                        String username = redisTemplate.opsForValue().get(authKey);

                        // 验证 Redis 中 token 存在
                        if (username != null) {
                            String userId = jwtUtil.getUserIdFromToken(token);
                            ctx.channel().attr(ChatWebSocketHandler.USER_ID_KEY).set(userId);
                            log.info("WebSocket 握手 Cookie 验证成功: userId={}", userId);
                        }
                    }
                } catch (Exception e) {
                    log.warn("WebSocket 握手 Cookie 验证失败: {}", e.getMessage());
                }
            }
        }

        // 继续传递请求到下一个 handler
        super.channelRead(ctx, msg);
    }

    /**
     * 从 Netty HttpHeaders 的 Cookie 中解析 token
     */
    private static String getTokenFromCookie(HttpHeaders headers) {
        String cookieHeader = headers.get("Cookie");
        if (cookieHeader == null || cookieHeader.isEmpty()) {
            return null;
        }
        String[] cookies = cookieHeader.split(";");
        for (String cookie : cookies) {
            String[] parts = cookie.trim().split("=");
            if (parts.length == 2 && TOKEN_COOKIE_NAME.equals(parts[0])) {
                return parts[1];
            }
        }
        return null;
    }
}