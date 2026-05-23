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
     * 延长原token有效期
     * @param token
     * @return
     */
    public String refreshToken(String token) {
        String userId = getUserIdFromToken(token);

        // 判断两次间隔是否超过1分钟
        long expiration = getClaimsFromToken(token).getExpiration().getTime();
        long temp = System.currentTimeMillis() - expiration;

        if (temp < MIN_TEMP) {
            return token;
        }
        return generateToken(userId);
    }
}
