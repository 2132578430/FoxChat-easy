package com.bedfox.web.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

/**
 * @author bedFox
 */
@Configuration
public class SecurityConfig {
    /**
     * 配置过滤器链：放行所有请求，关闭 CSRF，关闭默认登录页
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        // 1. 关闭 CSRF (开发 API 时通常关闭，否则 POST 请求会被拦截)
        http.csrf(csrf -> csrf.disable())
                // 2. 授权配置：允许所有请求 (permitAll)
                .authorizeHttpRequests(auth -> auth
                        .anyRequest().permitAll()
                )
                // 3. 关闭默认的表单登录 (FormLogin) 和 HTTP Basic 认证
                .formLogin(form -> form.disable())
                .httpBasic(basic -> basic.disable());
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
