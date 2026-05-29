package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.LlmConfig;
import com.bedfox.pojo.dto.LlmConfigDto;
import com.bedfox.pojo.dto.TestConnectionDto;

import java.util.List;
import java.util.Map;

/**
 * LLM 配置服务接口
 */
public interface LlmConfigService extends IService<LlmConfig> {

    /**
     * 批量保存配置（5 个场景）
     *
     * @param dto 配置 DTO
     * @return 配置 ID 列表
     */
    Map<String, String> saveConfigsBatch(LlmConfigDto dto);

    /**
     * 获取所有配置
     *
     * @param llmId AI 朋友 ID
     * @return 配置列表
     */
    List<LlmConfig> getConfigsByLlmId(String llmId);

    /**
     * 删除配置
     *
     * @param llmId AI 朋友 ID
     * @param scenario 场景名称
     * @return 是否成功
     */
    boolean deleteConfig(String llmId, String scenario);

    /**
     * 根据 llmId 删除所有配置
     *
     * @param llmId AI 朋友 ID
     * @return 删除的记录数
     */
    int deleteByLlmId(String llmId);

    /**
     * 测试连接（转发到 Python）
     *
     * @param dto 测试连接 DTO
     * @return 测试结果
     */
    Map<String, Object> testConnection(TestConnectionDto dto);

    /**
     * 验证配置完整性（数量是否为 5）
     *
     * @param llmId AI 朋友 ID
     * @return 是否完整
     */
    boolean validateConfigCount(String llmId);

    /**
     * 获取缺失的场景列表
     *
     * @param llmId AI 朋友 ID
     * @return 缺失场景列表
     */
    List<String> getMissingScenarios(String llmId);
}