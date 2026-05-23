package com.bedfox.common.config;

import io.minio.MinioClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * minio配置信息
 *
 * @author bedFox
 */
@Configuration
public class MinioConfig {

    @Value("${minio.endpoint}")
    public String endpoint;
    @Value("${minio.username}")
    public String username;
    @Value("${minio.password}")
    public String password;

    /**
     * 初始化minio客户端
     * @return
     */
    @Bean
    public MinioClient minioClient() {
        return MinioClient.builder()
                .endpoint(endpoint)
                .credentials(username, password)
                .build();
    }
}
