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
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
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
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        CurrentUser currentUser = new CurrentUser();
        // 从 Cookie 获取 token (HTTPOnly cookie)
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

        return true;
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
