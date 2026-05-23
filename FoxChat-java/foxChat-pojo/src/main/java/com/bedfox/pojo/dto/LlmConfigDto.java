package com.bedfox.pojo.dto;

import lombok.Data;

import java.util.List;

/**
 * LLM 配置批量保存 DTO
 */
@Data
public class LlmConfigDto {
    /**
     * AI 朋友 ID
     */
    private String llmId;

    /**
     * 配置列表（5 个场景）
     */
    private List<LlmConfigItem> configs;

    /**
     * 单个场景配置
     */
    @Data
    public static class LlmConfigItem {
        private String scenario;
        private String modelName;
        private String modelApiKey;
        private String modelBaseUrl;
        private Double modelTemperature;
        private Integer modelMaxTokens;
        private String modelResponseFormat;
    }
}