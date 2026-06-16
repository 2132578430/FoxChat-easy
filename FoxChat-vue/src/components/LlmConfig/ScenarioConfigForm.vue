<template>
  <div class="scenario-config-form">
    <!-- Provider Presets -->
    <div class="form-item">
      <label class="form-label">服务商</label>
      <FoxSelect
        v-model="selectedProvider"
        :options="providerOptions"
        placeholder="选择服务商预设"
        @change="handleProviderChange"
      />
    </div>

    <!-- Model Name -->
    <div class="form-item">
      <label class="form-label">模型名称</label>
      <FoxInput v-model="config.modelName" placeholder="例如: gpt-4, deepseek-chat" />
    </div>

    <!-- API Key -->
    <div class="form-item">
      <label class="form-label">API Key</label>
      <FoxInput v-model="config.apiKey" type="password" placeholder="输入您的 API Key" />
    </div>

    <!-- Base URL -->
    <div class="form-item">
      <label class="form-label">Base URL</label>
      <FoxInput v-model="config.baseUrl" placeholder="例如: https://api.openai.com/v1" />
    </div>

    <!-- Temperature -->
    <div class="form-item">
      <label class="form-label">Temperature: {{ config.temperature }}</label>
      <input type="range" v-model.number="config.temperature" min="0" max="2" step="0.1" class="fox-slider" />
      <div class="param-hint">值越低输出越确定性，值越高输出越随机</div>
    </div>

    <!-- Max Tokens -->
    <div class="form-item">
      <label class="form-label">最大 Token 数</label>
      <input type="number" v-model.number="config.maxTokens" min="1" max="128000" step="256" class="fox-number-input" />
      <div class="param-hint">模型生成的最大长度限制</div>
    </div>

    <!-- Response Format -->
    <div class="form-item" v-if="showResponseFormat">
      <label class="form-label">响应格式</label>
      <div class="radio-group">
        <label class="radio-item" :class="{ active: config.responseFormat === 'text' }">
          <input type="radio" v-model="config.responseFormat" value="text" />
          文本
        </label>
        <label class="radio-item" :class="{ active: config.responseFormat === 'json_object' }">
          <input type="radio" v-model="config.responseFormat" value="json_object" />
          JSON 对象
        </label>
      </div>
    </div>

    <!-- Test Connection -->
    <div class="form-item">
      <FoxButton
        type="primary"
        :loading="isTesting"
        :disabled="!config.modelName || !config.apiKey || !config.baseUrl"
        @click="handleTestConnection"
      >
        {{ isTesting ? '测试中...' : '测试连接' }}
      </FoxButton>

      <transition name="fade">
        <div v-if="testResult.show" class="test-result" :class="testResult.success ? 'success' : 'error'">
          <span>{{ testResult.success ? '✓' : '✗' }}</span>
          <span>{{ testResult.message }}</span>
        </div>
      </transition>
    </div>

    <!-- Save -->
    <div class="form-item">
      <FoxButton type="primary" :disabled="!testResult.success" @click="handleSave">保存配置</FoxButton>
      <span class="save-hint" v-if="!testResult.success">请先测试连接通过后再保存</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue';
import { FoxToast, FoxInput, FoxButton, FoxSelect } from '@/components/FoxUI';
import { testConnection } from '@/api/llmConfig';

const props = defineProps({
  scenario: { type: String, required: true },
  initialConfig: {
    type: Object,
    default: () => ({ modelName: '', apiKey: '', baseUrl: '', temperature: 0.5, maxTokens: 2048, responseFormat: 'text' })
  }
});

const emit = defineEmits(['save', 'test']);

const providerPresets = {
  openai: { baseUrl: 'https://api.openai.com/v1', defaultModel: 'gpt-4', defaultTemperature: 0.8, defaultMaxTokens: 4096 },
  deepseek: { baseUrl: 'https://api.deepseek.com/v1', defaultModel: 'deepseek-chat', defaultTemperature: 0.7, defaultMaxTokens: 4096 },
  claude: { baseUrl: 'https://api.anthropic.com/v1', defaultModel: 'claude-3-opus-20240229', defaultTemperature: 0.5, defaultMaxTokens: 4096 },
  gemini: { baseUrl: 'https://generativelanguage.googleapis.com/v1beta', defaultModel: 'gemini-pro', defaultTemperature: 0.7, defaultMaxTokens: 2048 },
  kimi: { baseUrl: 'https://api.moonshot.cn/v1', defaultModel: 'moonshot-v1-8k', defaultTemperature: 0.3, defaultMaxTokens: 8192 },
  ollama: { baseUrl: 'http://localhost:11434/v1', defaultModel: 'llama2', defaultTemperature: 0.8, defaultMaxTokens: 2048 }
};

const scenarioDefaults = {
  chat: { temperature: 0.8, maxTokens: 4096, responseFormat: 'text' },
  memory: { temperature: 0.3, maxTokens: 2048, responseFormat: 'text' },
  summary: { temperature: 0.5, maxTokens: 2048, responseFormat: 'text' },
  extraction: { temperature: 0.0, maxTokens: 2048, responseFormat: 'json_object' },
  emotion: { temperature: 0.0, maxTokens: 50, responseFormat: 'text' }
};

const config = reactive({
  modelName: props.initialConfig.modelName || '',
  apiKey: props.initialConfig.apiKey || '',
  baseUrl: props.initialConfig.baseUrl || '',
  temperature: props.initialConfig.temperature || scenarioDefaults[props.scenario]?.temperature || 0.5,
  maxTokens: props.initialConfig.maxTokens || scenarioDefaults[props.scenario]?.maxTokens || 2048,
  responseFormat: props.initialConfig.responseFormat || scenarioDefaults[props.scenario]?.responseFormat || 'text'
});

const selectedProvider = ref('');
const isTesting = ref(false);
const testResult = reactive({ show: false, success: false, message: '' });
const showResponseFormat = computed(() => props.scenario === 'extraction');

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Claude (Anthropic)', value: 'claude' },
  { label: 'Gemini (Google)', value: 'gemini' },
  { label: 'Kimi (Moonshot)', value: 'kimi' },
  { label: 'Ollama (Local)', value: 'ollama' },
  { label: '自定义', value: 'custom' },
];

const handleProviderChange = () => {
  const preset = providerPresets[selectedProvider.value];
  if (!preset) return;
  config.baseUrl = preset.baseUrl;
  config.modelName = preset.defaultModel;
  if (!props.initialConfig.temperature) config.temperature = preset.defaultTemperature;
  if (!props.initialConfig.maxTokens) config.maxTokens = preset.defaultMaxTokens;
};

const handleTestConnection = async () => {
  if (!config.modelName || !config.apiKey || !config.baseUrl) {
    FoxToast.warning('请填写模型名称、API Key 和 Base URL');
    return;
  }
  isTesting.value = true; testResult.show = false;
  try {
    const response = await testConnection({ modelName: config.modelName, apiKey: config.apiKey, baseUrl: config.baseUrl, scenario: props.scenario });
    if (response.code === 1000 && response.data?.success) {
      testResult.success = true; testResult.message = '连接成功';
      emit('test', { scenario: props.scenario, success: true });
    } else {
      testResult.success = false; testResult.message = response.data?.message || response.msg || '连接失败';
      emit('test', { scenario: props.scenario, success: false, error: testResult.message });
    }
  } catch (error) {
    testResult.success = false; testResult.message = '连接失败: ' + (error.message || '网络错误');
    emit('test', { scenario: props.scenario, success: false, error: error.message });
  } finally { isTesting.value = false; testResult.show = true; }
};

const handleSave = () => {
  if (!testResult.success) { FoxToast.warning('请先测试连接通过后再保存'); return; }
  emit('save', { scenario: props.scenario, config: { ...config } });
};

watch(() => props.initialConfig, (newConfig) => {
  if (!newConfig) return;
  config.modelName = newConfig.modelName || '';
  config.apiKey = newConfig.apiKey || '';
  config.baseUrl = newConfig.baseUrl || '';
  config.temperature = newConfig.temperature || scenarioDefaults[props.scenario]?.temperature || 0.5;
  config.maxTokens = newConfig.maxTokens || scenarioDefaults[props.scenario]?.maxTokens || 2048;
  config.responseFormat = newConfig.responseFormat || scenarioDefaults[props.scenario]?.responseFormat || 'text';
  testResult.show = false; testResult.success = false;
}, { deep: true });

const setConfig = (newConfig) => {
  config.modelName = newConfig.modelName || ''; config.apiKey = newConfig.apiKey || ''; config.baseUrl = newConfig.baseUrl || '';
  testResult.show = false; testResult.success = false;
};
const getConfig = () => ({ ...config });
defineExpose({ setConfig, getConfig });
</script>

<style scoped>
.scenario-config-form { padding: 20px; background: rgba(255,255,255,0.6); border-radius: 10px; }
.form-item { margin-bottom: 20px; }
.form-label { display: block; font-size: 13px; font-weight: 500; color: #555; margin-bottom: 6px; }

/* Native Range Slider */
.fox-slider {
  width: 100%; height: 6px; -webkit-appearance: none; appearance: none;
  background: #e0e0e0; border-radius: 3px; outline: none; margin: 8px 0;
}
.fox-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 18px; height: 18px; border-radius: 50%;
  background: #4a90d9; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.15);
}

/* Native Number Input */
.fox-number-input {
  width: 140px; height: 36px; padding: 0 12px; border-radius: 8px;
  border: 1px solid rgba(0,0,0,0.12); background: rgba(255,255,255,0.85);
  font-size: 14px; outline: none;
}
.fox-number-input:focus { border-color: #4a90d9; box-shadow: 0 0 0 3px rgba(74,144,217,0.1); }

/* Radio Group */
.radio-group { display: flex; gap: 12px; }
.radio-item {
  display: flex; align-items: center; gap: 6px; padding: 6px 14px;
  border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); cursor: pointer;
  font-size: 13px; color: #666; transition: all 0.15s;
}
.radio-item:hover { border-color: #4a90d9; }
.radio-item.active { background: rgba(74,144,217,0.08); border-color: #4a90d9; color: #4a90d9; }
.radio-item input { display: none; }

/* Hints */
.param-hint { font-size: 13px; color: #888; margin-top: 6px; }
.save-hint { font-size: 13px; color: #888; margin-left: 10px; }

/* Test Result */
.test-result { display: inline-flex; align-items: center; gap: 6px; margin-left: 10px; padding: 5px 12px; border-radius: 6px; font-size: 13px; }
.test-result.success { background: rgba(103,194,58,0.1); color: #67c23a; }
.test-result.error { background: rgba(245,108,108,0.1); color: #f56c6c; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
