package com.bedfox.web.interceptor;

import com.bedfox.common.constant.AuthConstant;
import com.bedfox.pojo.domain.CurrentUser;
import com.bedfox.common.util.CookieUtil;
import com.bedfox.common.util.JwtUtil;
import com.bedfox.common.util.LoginUserHolder;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
/**
 * @author bedFox
 */
@Slf4j
@Component
public class LoginInterceptor implements HandlerInterceptor {

    public static ThreadLocal<CurrentUser> userThreadLocal = new ThreadLocal<>();

    @Resource
    JwtUtil jwtUtil;

    @Resource(name = "stringRedisTemplate")
    StringRedisTemplate redisTemplate;

    /**
     * 登录校验器
     * @param request
     * @param response
     * @param handler
     * @return
     * @throws Exception
     */
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 预检请求全部通过
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        CurrentUser currentUser = new CurrentUser();
        // 从 Cookie 获取 token
        String token = CookieUtil.getTokenFromCookie(request);
        String authKey = AuthConstant.PRE_LOGIN_AUTH + token;

        String username = redisTemplate.opsForValue().get(authKey);
        // 校验token是否有效
        if (StringUtils.isEmpty(token)
                || !jwtUtil.validateToken(token)
                || username == null)
        {
            response.setStatus(401);
            return false;
        }

        String userId = jwtUtil.getUserIdFromToken(token);

        currentUser.setUserId(userId);
        currentUser.setUserName(username);

        LoginUserHolder.setCurrent(currentUser);

        // ── Token 滑动刷新 ──
        tryRefreshToken(token, userId, username, response);

        return true;
    }

    // ── Token 滑动刷新配置 ──
    private static final long REFRESH_THRESHOLD_MS = 5 * 60 * 1000; // 剩余5分钟时刷新
    private static final long REFRESH_LOCK_TTL_SEC = 5;             // 刷新锁TTL
    private static final long REDIS_AUTH_TTL_HOURS = 24;            // 新token的Redis TTL

    /**
     * Token 滑动刷新：检测即将过期 → 防并发锁 → 签发新token → Redis原子替换 → 写Cookie
     */
    private void tryRefreshToken(String oldToken, String userId, String username,
                                  HttpServletResponse response) {
        if (!jwtUtil.isTokenAboutToExpire(oldToken, REFRESH_THRESHOLD_MS)) {
            return;
        }

        // 防并发：同一用户5秒内只允许一次刷新
        String lockKey = "auth:refresh_lock:" + userId;
        Boolean locked = redisTemplate.opsForValue()
                .setIfAbsent(lockKey, "1", REFRESH_LOCK_TTL_SEC, TimeUnit.SECONDS);
        if (!Boolean.TRUE.equals(locked)) {
            return;
        }

        try {
            String newToken = jwtUtil.generateToken(userId);
            String newAuthKey = AuthConstant.PRE_LOGIN_AUTH + newToken;
            String oldAuthKey = AuthConstant.PRE_LOGIN_AUTH + oldToken;

            // Redis pipeline 原子：写新 key + 删旧 key
            redisTemplate.executePipelined((RedisCallback<Object>) connection -> {
                byte[] nk = newAuthKey.getBytes(StandardCharsets.UTF_8);
                byte[] ok = oldAuthKey.getBytes(StandardCharsets.UTF_8);
                byte[] un = username.getBytes(StandardCharsets.UTF_8);
                connection.stringCommands().setEx(nk, REDIS_AUTH_TTL_HOURS * 3600, un);
                connection.keyCommands().del(ok);
                return null;
            });

            CookieUtil.setTokenCookie(response, newToken);
            log.info("Token 滑动刷新成功: userId={}", userId);
        } catch (Exception e) {
            log.warn("Token 滑动刷新失败: userId={}, error={}", userId, e.getMessage());
        } finally {
            redisTemplate.delete(lockKey);
        }
    }

    /**
     * 逻辑结束去除身份信息
     * @param request
     * @param response
     * @param handler
     * @param ex
     * @throws Exception
     */
    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) throws Exception {
        LoginUserHolder.clear();
    }


}
