package com.bedfox.web.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * @author bedFox
 */
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        // 对所有路径生效
        registry.addMapping("/**")
                // 允许所有来源（比 allowedOrigins 更灵活，支持 Cookie）
                .allowedOriginPatterns("*")
                // 允许的方法，必须包含 OPTIONS
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                // 允许所有 Header
                .allowedHeaders("*")
                // 允许携带 Cookie/凭证
                .allowCredentials(true)
                // 预检请求缓存时间（秒）
                .maxAge(3600);
    }
}
