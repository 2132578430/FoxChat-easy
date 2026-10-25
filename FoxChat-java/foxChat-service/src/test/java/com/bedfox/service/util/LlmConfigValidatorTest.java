package com.bedfox.service.util;

import com.bedfox.pojo.dto.LlmConfigDto;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LlmConfigValidatorTest {

    private static LlmConfigDto.LlmConfigItem item(
            String scenario, String modelName, String apiKey, String baseUrl) {
        LlmConfigDto.LlmConfigItem item = new LlmConfigDto.LlmConfigItem();
        item.setScenario(scenario);
        item.setModelName(modelName);
        item.setModelApiKey(apiKey);
        item.setModelBaseUrl(baseUrl);
        item.setModelTemperature(0.5);
        item.setModelMaxTokens(2048);
        item.setModelResponseFormat("text");
        return item;
    }

    private static LlmConfigDto dto(String llmId, LlmConfigDto.LlmConfigItem... items) {
        LlmConfigDto dto = new LlmConfigDto();
        dto.setLlmId(llmId);
        dto.setConfigs(new ArrayList<>(List.of(items)));
        return dto;
    }

    @Test
    void validBatchPasses() {
        LlmConfigDto dto = dto("llm-1",
                item("chat", "gpt-4", "sk-1", "https://api.openai.com/v1"),
                item("memory", "gpt-4", "sk-1", "https://api.openai.com/v1"),
                item("summary", "gpt-4", "sk-1", "https://api.openai.com/v1"),
                item("extraction", "gpt-4", "sk-1", "https://api.openai.com/v1"),
                item("emotion", "gpt-4", "sk-1", "https://api.openai.com/v1"));
        assertTrue(LlmConfigValidator.validateBatch(dto).isEmpty());
    }

    @Test
    void llmIdAndConfigsAreRequired() {
        assertEquals(List.of("llmId 不能为空"), LlmConfigValidator.validateBatch(null));
        assertEquals(List.of("llmId 不能为空"),
                LlmConfigValidator.validateBatch(dto("  ")));

        LlmConfigDto empty = new LlmConfigDto();
        empty.setLlmId("llm-1");
        assertEquals(List.of("配置列表不能为空"), LlmConfigValidator.validateBatch(empty));

        empty.setConfigs(new ArrayList<>());
        assertEquals(List.of("配置列表不能为空"), LlmConfigValidator.validateBatch(empty));
    }

    @Test
    void scenarioMustBeKnownAndUnique() {
        List<String> errors = LlmConfigValidator.validateBatch(dto("llm-1",
                item("unknown", "m", "k", "https://api.example.com/v1"),
                item("chat", "m", "k", "https://api.example.com/v1"),
                item("chat", "m", "k", "https://api.example.com/v1")));

        assertTrue(errors.contains("场景不合法: unknown"));
        assertTrue(errors.contains("场景重复: chat"));
    }

    @Test
    void modelNameApiKeyAndBaseUrlAreRequired() {
        List<String> errors = LlmConfigValidator.validateBatch(dto("llm-1",
                item("chat", "  ", "", "   ")));

        assertTrue(errors.contains("chat 场景：模型名称不能为空"));
        assertTrue(errors.contains("chat 场景：API Key 不能为空"));
        assertTrue(errors.contains("chat 场景：Base URL 不能为空"));
    }

    @Test
    void baseUrlMustBeHttpWithHost() {
        assertNull(LlmConfigValidator.validateBaseUrl("https://api.openai.com/v1"));
        assertNull(LlmConfigValidator.validateBaseUrl("HTTP://api.example.com:8080/v1"));
        assertEquals("Base URL 不能为空", LlmConfigValidator.validateBaseUrl(null));
        assertEquals("Base URL 不能为空", LlmConfigValidator.validateBaseUrl(" "));
        assertEquals("Base URL 只支持 http:// 或 https://",
                LlmConfigValidator.validateBaseUrl("ftp://api.example.com"));
        assertEquals("Base URL 只支持 http:// 或 https://",
                LlmConfigValidator.validateBaseUrl("abc"));
        assertEquals("Base URL 格式不正确，示例：https://api.openai.com/v1",
                LlmConfigValidator.validateBaseUrl("http://"));
        assertEquals("Base URL 缺少主机名",
                LlmConfigValidator.validateBaseUrl("https:///v1"));
        assertEquals("Base URL 不能包含用户名/密码",
                LlmConfigValidator.validateBaseUrl("https://user:pass@api.example.com/v1"));
        assertEquals("Base URL 格式不正确，示例：https://api.openai.com/v1",
                LlmConfigValidator.validateBaseUrl("https://api example.com"));
    }

    @Test
    void temperatureAndMaxTokensAreBounded() {
        LlmConfigDto.LlmConfigItem low = item("chat", "m", "k", "https://api.example.com/v1");
        low.setModelTemperature(-0.1);
        LlmConfigDto.LlmConfigItem high = item("memory", "m", "k", "https://api.example.com/v1");
        high.setModelTemperature(2.1);
        LlmConfigDto.LlmConfigItem zeroTokens = item("summary", "m", "k", "https://api.example.com/v1");
        zeroTokens.setModelMaxTokens(0);

        List<String> errors = LlmConfigValidator.validateBatch(
                dto("llm-1", low, high, zeroTokens));

        assertTrue(errors.contains("chat 场景：Temperature 必须在 0~2 之间"));
        assertTrue(errors.contains("memory 场景：Temperature 必须在 0~2 之间"));
        assertTrue(errors.contains("summary 场景：最大 Token 数必须大于 0"));
    }

    @Test
    void responseFormatMustBeKnown() {
        LlmConfigDto.LlmConfigItem invalid = item("extraction", "m", "k", "https://api.example.com/v1");
        invalid.setModelResponseFormat("xml");

        List<String> errors = LlmConfigValidator.validateBatch(dto("llm-1", invalid));

        assertTrue(errors.contains("extraction 场景：响应格式不合法"));
    }

    @Test
    void normalizeBaseUrlTrimsAndStripsTrailingSlashes() {
        assertEquals("https://api.example.com/v1",
                LlmConfigValidator.normalizeBaseUrl("  https://api.example.com/v1///  "));
        assertEquals("https://api.example.com",
                LlmConfigValidator.normalizeBaseUrl("https://api.example.com/"));
        assertNull(LlmConfigValidator.normalizeBaseUrl(null));
    }
}
