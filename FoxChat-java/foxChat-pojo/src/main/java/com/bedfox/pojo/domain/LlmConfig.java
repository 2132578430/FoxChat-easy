package com.bedfox.pojo.domain;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * LLM 配置表
 * @TableName llm_config
 */
@TableName(value = "llm_config")
@Data
public class LlmConfig implements Serializable {
    /**
     * 配置 ID
     */
    @TableId
    private String id;

    /**
     * AI 朋友 ID
     */
    private String llmId;

    /**
     * 场景类型 (chat/memory/summary/extraction/emotion)
     */
    private String scenario;

    /**
     * 模型名称
     */
    private String modelName;

    /**
     * API 密钥
     */
    private String modelApiKey;

    /**
     * 服务地址
     */
    private String modelBaseUrl;

    /**
     * 温度参数
     */
    private Double modelTemperature;

    /**
     * 最大输出长度
     */
    private Integer modelMaxTokens;

    /**
     * 输出格式 (json)
     */
    private String modelResponseFormat;

    /**
     * 是否默认配置
     */
    private Boolean isDefault;

    /**
     * 创建时间
     */
    private LocalDateTime createdAt;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;
}