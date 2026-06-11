package com.bedfox.common.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Date;
import java.util.HashMap;
import java.util.Map;

/**
 * @author bedFox
 */
@Component
public class JwtUtil {

    // 密钥
    @Value("${FoxJwt.Secret}")
    private String secret;
    // 过期时间 (ms)
    @Value("${FoxJwt.Expiration}")
    private long expiration;

    private final static long MIN_TEMP = 1000 * 60 * 24;

    /**
     * 生成 Token
     * @param claims 数据声明（例如 userId, username）
     * @return Token 字符串
     */
    public String generateToken(Map<String, Object> claims) {
        return Jwts.builder()
                .setClaims(claims)
                .setIssuedAt(new Date())
                .setExpiration(new Date(System.currentTimeMillis() + expiration))
                .signWith(SignatureAlgorithm.HS256, secret)
                .compact();
    }

    /**
     * 生成 Token (重载：仅传入用户ID)
     */
    public String generateToken(String userId) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", userId);
        return generateToken(claims);
    }

    /**
     * 从 Token 中获取 Claims
     */
    public Claims getClaimsFromToken(String token) {
        try {
            return Jwts.parser()
                    .setSigningKey(secret)
                    .parseClaimsJws(token)
                    .getBody();
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 从 Token 中获取用户ID
     */
    public String getUserIdFromToken(String token) {
        Claims claims = getClaimsFromToken(token);
        return claims != null ? (String) claims.get("userId") : null;
    }

    /**
     * 验证 Token 是否有效
     */
    public boolean validateToken(String token) {
        String userId = getUserIdFromToken(token);
        return (!StringUtils.isEmpty(userId) && !isTokenExpired(token));
    }

    /**
     * 判断 Token 是否过期
     */
    private boolean isTokenExpired(String token) {
        Claims claims = getClaimsFromToken(token);
        return claims != null && claims.getExpiration().before(new Date());
    }

    /**
     * 判断 Token 是否即将过期（剩余有效期 < thresholdMs）
     *
     * @param token       JWT token
     * @param thresholdMs 阈值（毫秒），剩余有效期小于此值视为即将过期
     * @return true 如果即将过期或已过期/无法解析
     */
    public boolean isTokenAboutToExpire(String token, long thresholdMs) {
        Claims claims = getClaimsFromToken(token);
        if (claims == null) {
            return true;
        }
        long remaining = claims.getExpiration().getTime() - System.currentTimeMillis();
        return remaining < thresholdMs;
    }

    /**
     * 刷新 Token：基于旧 token 中的用户信息签发新 token。
     * 仅当旧 token 未过期，或过期未超过 MIN_TEMP（24分钟）才允许刷新。
     *
     * @param token 旧 token
     * @return 新 token；如果过期太久或解析失败返回 null
     */
    public String refreshToken(String token) {
        Claims claims = getClaimsFromToken(token);
        if (claims == null) {
            return null;
        }

        String userId = (String) claims.get("userId");
        if (StringUtils.isEmpty(userId)) {
            return null;
        }

        // 过期超过宽限期则拒绝
        long sinceExpired = System.currentTimeMillis() - claims.getExpiration().getTime();
        if (sinceExpired > MIN_TEMP) {
            return null;
        }

        return generateToken(userId);
    }
}
