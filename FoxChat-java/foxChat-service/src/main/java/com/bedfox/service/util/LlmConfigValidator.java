package com.bedfox.service.util;

import com.bedfox.pojo.dto.LlmConfigDto;

import java.net.URI;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * LLM 配置参数校验器。
 */
public final class LlmConfigValidator {

    private static final Set<String> SCENARIOS =
            Set.of("chat", "memory", "summary", "extraction", "emotion");
    private static final Set<String> RESPONSE_FORMATS =
            Set.of("text", "json", "json_object");

    private LlmConfigValidator() {
    }

    public static List<String> validateBatch(LlmConfigDto dto) {
        List<String> errors = new ArrayList<>();
        if (dto == null || isBlank(dto.getLlmId())) {
            errors.add("llmId 不能为空");
            return errors;
        }
        if (dto.getConfigs() == null || dto.getConfigs().isEmpty()) {
            errors.add("配置列表不能为空");
            return errors;
        }
        Set<String> seen = new HashSet<>();
        for (LlmConfigDto.LlmConfigItem item : dto.getConfigs()) {
            String scenario = item.getScenario();
            if (isBlank(scenario) || !SCENARIOS.contains(scenario)) {
                errors.add("场景不合法: " + scenario);
                continue;
            }
            if (!seen.add(scenario)) {
                errors.add("场景重复: " + scenario);
            }
            if (isBlank(item.getModelName())) {
                errors.add(scenario + " 场景：模型名称不能为空");
            }
            if (isBlank(item.getModelApiKey())) {
                errors.add(scenario + " 场景：API Key 不能为空");
            }
            String urlError = validateBaseUrl(item.getModelBaseUrl());
            if (urlError != null) {
                errors.add(scenario + " 场景：" + urlError);
            }
            if (item.getModelTemperature() != null
                    && (item.getModelTemperature() < 0 || item.getModelTemperature() > 2)) {
                errors.add(scenario + " 场景：Temperature 必须在 0~2 之间");
            }
            if (item.getModelMaxTokens() != null && item.getModelMaxTokens() <= 0) {
                errors.add(scenario + " 场景：最大 Token 数必须大于 0");
            }
            if (item.getModelResponseFormat() != null
                    && !RESPONSE_FORMATS.contains(item.getModelResponseFormat())) {
                errors.add(scenario + " 场景：响应格式不合法");
            }
        }
        return errors;
    }

    public static String validateBaseUrl(String raw) {
        if (isBlank(raw)) return "Base URL 不能为空";
        String value = raw.trim();
        try {
            URI uri = URI.create(value);
            String scheme = uri.getScheme();
            if (scheme == null
                    || !(scheme.equalsIgnoreCase("http") || scheme.equalsIgnoreCase("https"))) {
                return "Base URL 只支持 http:// 或 https://";
            }
            if (uri.getHost() == null || uri.getHost().isBlank()) {
                return "Base URL 缺少主机名";
            }
            if (uri.getUserInfo() != null) {
                return "Base URL 不能包含用户名/密码";
            }
        } catch (IllegalArgumentException e) {
            return "Base URL 格式不正确，示例：https://api.openai.com/v1";
        }
        return null;
    }

    public static String normalizeBaseUrl(String raw) {
        return raw == null ? null : raw.trim().replaceAll("/+$", "");
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
