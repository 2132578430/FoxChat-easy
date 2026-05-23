package com.bedfox.pojo.dto;

import lombok.Data;

/**
 * 测试连接请求 DTO
 */
@Data
public class TestConnectionDto {
    /**
     * 模型名称
     */
    private String modelName;

    /**
     * API 密钥
     */
    private String apiKey;

    /**
     * 服务地址
     */
    private String baseUrl;

    /**
     * 场景类型（可选）
     */
    private String scenario;
}