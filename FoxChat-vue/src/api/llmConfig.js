import request from '@/utils/request';

/**
 * LLM 配置 API
 * 提供创造物的模型配置接口
 */

// 批量保存配置（5 个场景）
export function saveConfigsBatch(llmId, configs) {
  return request.post('/llm/config/batch', {
    llmId,
    configs
  });
}

// 获取所有配置
export function getConfigs(llmId) {
  return request.get(`/llm/config/${llmId}`);
}

// 删除配置
export function deleteConfig(llmId, scenario) {
  return request.delete(`/llm/config/${llmId}/${scenario}`);
}

// 测试连接
export function testConnection(config) {
  return request.post('/llm/config/testConnection', {
    modelName: config.modelName,
    apiKey: config.apiKey,
    baseUrl: config.baseUrl,
    scenario: config.scenario
  });
}

// 验证配置完整性
export function validateConfig(llmId) {
  return request.get(`/llm/config/validate/${llmId}`);
}