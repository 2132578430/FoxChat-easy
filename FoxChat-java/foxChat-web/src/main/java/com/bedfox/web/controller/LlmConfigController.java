package com.bedfox.web.controller;

import com.bedfox.pojo.domain.LlmConfig;
import com.bedfox.pojo.dto.LlmConfigDto;
import com.bedfox.pojo.dto.TestConnectionDto;
import com.bedfox.service.service.LlmConfigService;
import com.bedfox.common.util.R;
import com.bedfox.common.constant.ResultStatusConstant;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * LLM 配置控制器
 * 提供 AI 朋友的模型配置接口
 *
 * @author bedFox
 */
@Slf4j
@RestController
@RequestMapping("/llm/config")
public class LlmConfigController {

    @Resource
    LlmConfigService llmConfigService;

    /**
     * 批量保存配置（5 个场景）
     *
     * @param dto 配置 DTO
     * @return 配置 ID 列表
     */
    @PostMapping("/batch")
    public R<Map<String, String>> saveConfigsBatch(@RequestBody LlmConfigDto dto) {
        try {
            Map<String, String> configIds = llmConfigService.saveConfigsBatch(dto);
            log.info("【批量保存配置】成功，llmId={}, 保存数量={}", dto.getLlmId(), configIds.size());
            return R.ok(configIds);
        } catch (Exception e) {
            log.error("【批量保存配置】失败: {}", e.getMessage());
            return R.error(ResultStatusConstant.LLM_CONFIG_SAVE_ERROR_EXCEPTION);
        }
    }

    /**
     * 获取所有配置
     *
     * @param llmId AI 朋友 ID
     * @return 配置列表
     */
    @GetMapping("/{llmId}")
    public R<List<LlmConfig>> getConfigsByLlmId(@PathVariable("llmId") String llmId) {
        List<LlmConfig> configs = llmConfigService.getConfigsByLlmId(llmId);
        log.info("【获取配置】llmId={}, 配置数量={}", llmId, configs.size());
        return R.ok(configs);
    }

    /**
     * 删除配置
     *
     * @param llmId AI 朋友 ID
     * @param scenario 场景名称
     * @return 删除结果
     */
    @DeleteMapping("/{llmId}/{scenario}")
    public R<Void> deleteConfig(
            @PathVariable("llmId") String llmId,
            @PathVariable("scenario") String scenario
    ) {
        boolean success = llmConfigService.deleteConfig(llmId, scenario);
        if (success) {
            log.info("【删除配置】成功，llmId={}, scenario={}", llmId, scenario);
            return R.ok();
        } else {
            log.warn("【删除配置】失败，配置不存在，llmId={}, scenario={}", llmId, scenario);
            return R.error(ResultStatusConstant.UNKNOWN_ERROR);
        }
    }

    /**
     * 测试连接（转发到 Python RAG 服务）
     *
     * @param dto 测试连接 DTO
     * @return 测试结果
     */
    @PostMapping("/testConnection")
    public R<Map<String, Object>> testConnection(@RequestBody TestConnectionDto dto) {
        Map<String, Object> result = llmConfigService.testConnection(dto);

        // Python 返回的数据包裹在 data 字段中 (M.get_msg 格式)
        Map<String, Object> data = (Map<String, Object>) result.get("data");
        if (data == null) {
            data = result; // 兼容 Feign 异常时的直接返回格式
        }

        Boolean success = (Boolean) data.get("success");
        log.info("【测试连接】modelName={}, baseUrl={}, success={}",
                dto.getModelName(), dto.getBaseUrl(), success);

        if (Boolean.TRUE.equals(success)) {
            return R.ok(data);
        } else {
            String errorMsg = (String) data.get("message");
            return R.error(ResultStatusConstant.LLM_API_KEY_INVALID_EXCEPTION.getCode(), errorMsg);
        }
    }

    /**
     * 验证配置完整性
     *
     * @param llmId AI 朋友 ID
     * @return 验证结果
     */
    @GetMapping("/validate/{llmId}")
    public R<Map<String, Object>> validateConfig(@PathVariable("llmId") String llmId) {
        boolean isValid = llmConfigService.validateConfigCount(llmId);
        List<String> missingScenarios = llmConfigService.getMissingScenarios(llmId);

        Map<String, Object> result = new java.util.HashMap<>();
        result.put("isValid", isValid);
        result.put("missingScenarios", missingScenarios);
        result.put("total", 5);
        result.put("configured", 5 - missingScenarios.size());

        log.info("【配置验证】llmId={}, isValid={}, missing={}", llmId, isValid, missingScenarios);

        if (isValid) {
            return R.ok(result);
        } else {
            return R.error(ResultStatusConstant.LLM_CONFIG_INCOMPLETE_EXCEPTION, result);
        }
    }
}