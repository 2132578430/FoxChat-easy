package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.pojo.domain.LlmConfig;
import com.bedfox.pojo.dto.LlmConfigDto;
import com.bedfox.pojo.dto.TestConnectionDto;
import com.bedfox.service.mapper.LlmConfigMapper;
import com.bedfox.service.service.LlmConfigService;
import com.bedfox.service.service.LlmUserService;
import com.bedfox.service.remote.ChatClient;
import feign.FeignException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * LLM 配置服务实现
 */
@Slf4j
@Service
public class LlmConfigServiceImpl extends ServiceImpl<LlmConfigMapper, LlmConfig> implements LlmConfigService {

    @Autowired
    private LlmConfigMapper llmConfigMapper;

    @Autowired
    private ChatClient chatClient;

    @Lazy
    @Autowired
    private LlmUserService llmUserService;

    private static final List<String> REQUIRED_SCENARIOS = Arrays.asList(
            "chat", "memory", "summary", "extraction", "emotion"
    );

    @Override
    public Map<String, String> saveConfigsBatch(LlmConfigDto dto) {
        String llmId = dto.getLlmId();
        List<LlmConfigDto.LlmConfigItem> configs = dto.getConfigs();

        Map<String, String> configIds = new HashMap<>();

        for (LlmConfigDto.LlmConfigItem item : configs) {
            String scenario = item.getScenario();

            // 检查是否已存在配置
            LlmConfig existing = llmConfigMapper.selectByLlmIdAndScenario(llmId, scenario);

            if (existing != null) {
                // 更新现有配置
                existing.setModelName(item.getModelName());
                existing.setModelApiKey(item.getModelApiKey());
                existing.setModelBaseUrl(item.getModelBaseUrl());
                existing.setModelTemperature(item.getModelTemperature());
                existing.setModelMaxTokens(item.getModelMaxTokens());
                existing.setModelResponseFormat(item.getModelResponseFormat());

                llmConfigMapper.updateByLlmIdAndScenario(existing);
                configIds.put(scenario, existing.getId());

                log.info("【更新配置】llmId={}, scenario={}", llmId, scenario);
            } else {
                // 创建新配置
                LlmConfig newConfig = new LlmConfig();
                newConfig.setId(UUID.randomUUID().toString());
                newConfig.setLlmId(llmId);
                newConfig.setScenario(scenario);
                newConfig.setModelName(item.getModelName());
                newConfig.setModelApiKey(item.getModelApiKey());
                newConfig.setModelBaseUrl(item.getModelBaseUrl());
                newConfig.setModelTemperature(item.getModelTemperature());
                newConfig.setModelMaxTokens(item.getModelMaxTokens());
                newConfig.setModelResponseFormat(item.getModelResponseFormat());
                newConfig.setIsDefault(false);
                newConfig.setCreatedAt(LocalDateTime.now());

                llmConfigMapper.insert(newConfig);
                configIds.put(scenario, newConfig.getId());

                log.info("【创建配置】llmId={}, scenario={}, id={}", llmId, scenario, newConfig.getId());
            }
        }

        log.info("【批量保存】llmId={}, 保存 {} 个配置", llmId, configIds.size());

        Map<String, Object> activateResult = llmUserService.activateLlm(llmId);
        log.info("【批量保存后激活】llmId={}, result={}", llmId, activateResult);

        return configIds;
    }

    @Override
    public List<LlmConfig> getConfigsByLlmId(String llmId) {
        return llmConfigMapper.selectByLlmId(llmId);
    }

    @Override
    public boolean deleteConfig(String llmId, String scenario) {
        int result = llmConfigMapper.deleteByLlmIdAndScenario(llmId, scenario);
        if (result > 0) {
            log.info("【删除配置】llmId={}, scenario={}", llmId, scenario);
            return true;
        } else {
            log.warn("【删除配置】配置不存在: llmId={}, scenario={}", llmId, scenario);
            return false;
        }
    }

@Override
    public Map<String, Object> testConnection(TestConnectionDto dto) {
        try {
            log.info("【测试连接】modelName={}, baseUrl={}", dto.getModelName(), dto.getBaseUrl());

            Map<String, String> request = new HashMap<>();
            request.put("model_name", dto.getModelName());
            request.put("api_key", dto.getApiKey());
            request.put("base_url", dto.getBaseUrl());

            Map<String, Object> result = chatClient.testConnection(request);
            log.info("【测试连接】Python 返回: {}", result);
            return result;
        } catch (FeignException e) {
            String responseBody = e.contentUTF8();
            log.error("【测试连接】Feign 异常: status={}, body={}", e.status(), responseBody);

            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("message", responseBody);
            return response;
        } catch (Exception e) {
            log.error("【测试连接】失败: {}", e.getMessage());
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("message", "测试连接失败: " + e.getMessage());
            return response;
        }
    }


    @Override
    public boolean validateConfigCount(String llmId) {
        int count = llmConfigMapper.countByLlmId(llmId);
        boolean isValid = count == 5;

        if (isValid) {
            log.debug("【配置验证】llmId={}, 配置完整 ({}/5)", llmId, count);
        } else {
            log.warn("【配置验证】llmId={}, 配置不完整 ({}/5)", llmId, count);
        }

        return isValid;
    }

    @Override
    public List<String> getMissingScenarios(String llmId) {
        List<LlmConfig> configs = llmConfigMapper.selectByLlmId(llmId);
        Set<String> existingScenarios = configs.stream()
                .map(LlmConfig::getScenario)
                .collect(Collectors.toSet());

        List<String> missing = REQUIRED_SCENARIOS.stream()
                .filter(s -> !existingScenarios.contains(s))
                .collect(Collectors.toList());

        log.info("【缺失场景】llmId={}, missing={}", llmId, missing);
        return missing;
    }
}