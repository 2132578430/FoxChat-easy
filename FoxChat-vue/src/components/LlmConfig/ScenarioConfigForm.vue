<template>
  <div class="scenario-config-form">
    <el-form :model="config" label-width="120px" label-position="top">
      <!-- Provider Presets -->
      <el-form-item label="服务商">
        <el-select v-model="selectedProvider" placeholder="选择服务商预设" @change="handleProviderChange">
          <el-option label="OpenAI" value="openai" />
          <el-option label="DeepSeek" value="deepseek" />
          <el-option label="Claude (Anthropic)" value="claude" />
          <el-option label="Gemini (Google)" value="gemini" />
          <el-option label="Kimi (Moonshot)" value="kimi" />
          <el-option label="Ollama (Local)" value="ollama" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>

      <!-- Model Name -->
      <el-form-item label="模型名称" required>
        <el-input v-model="config.modelName" placeholder="例如: gpt-4, deepseek-chat, claude-3-opus">
          <template #prepend>
            <el-icon><Document /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <!-- API Key -->
      <el-form-item label="API Key" required>
        <el-input
          v-model="config.apiKey"
          type="password"
          placeholder="输入您的 API Key"
          show-password
        >
          <template #prepend>
            <el-icon><Key /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <!-- Base URL -->
      <el-form-item label="Base URL" required>
        <el-input v-model="config.baseUrl" placeholder="例如: https://api.openai.com/v1">
          <template #prepend>
            <el-icon><Link /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <!-- Temperature -->
      <el-form-item label="Temperature">
        <el-slider v-model="config.temperature" :min="0" :max="2" :step="0.1" show-input />
        <span class="param-hint">值越低输出越确定性，值越高输出越随机</span>
      </el-form-item>

      <!-- Max Tokens -->
      <el-form-item label="最大 Token 数">
        <el-input-number v-model="config.maxTokens" :min="1" :max="128000" :step="256" />
        <span class="param-hint">模型生成的最大长度限制</span>
      </el-form-item>

      <!-- Response Format -->
      <el-form-item label="响应格式" v-if="showResponseFormat">
        <el-radio-group v-model="config.responseFormat">
          <el-radio label="text">文本</el-radio>
          <el-radio label="json_object">JSON 对象</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- Test Connection Button -->
      <el-form-item>
        <el-button
          type="primary"
          :icon="isTesting ? null : Connection"
          :loading="isTesting"
          @click="handleTestConnection"
          :disabled="!config.modelName || !config.apiKey || !config.baseUrl"
        >
          {{ isTesting ? '测试中...' : '测试连接' }}
        </el-button>

        <!-- Test Result Message -->
        <transition name="fade">
          <div v-if="testResult.show" class="test-result" :class="testResult.success ? 'success' : 'error'">
            <el-icon :size="16">
              <SuccessFilled v-if="testResult.success" />
              <CircleCloseFilled v-else />
            </el-icon>
            <span>{{ testResult.message }}</span>
          </div>
        </transition>
      </el-form-item>

      <!-- Save Button -->
      <el-form-item>
        <el-button
          type="primary"
          :icon="Check"
          @click="handleSave"
          :disabled="!testResult.success"
        >
          保存配置
        </el-button>
        <span class="save-hint" v-if="!testResult.success">请先测试连接通过后再保存</span>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Document,
  Key,
  Link,
  Connection,
  Check,
  SuccessFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue';
import { testConnection } from '@/api/llmConfig';

const props = defineProps({
  scenario: {
    type: String,
    required: true
  },
  initialConfig: {
    type: Object,
    default: () => ({
      modelName: '',
      apiKey: '',
      baseUrl: '',
      temperature: 0.5,
      maxTokens: 2048,
      responseFormat: 'text'
    })
  }
});

const emit = defineEmits(['save', 'test']);

// Provider presets base URLs
const providerPresets = {
  openai: {
    baseUrl: 'https://api.openai.com/v1',
    defaultModel: 'gpt-4',
    defaultTemperature: 0.8,
    defaultMaxTokens: 4096
  },
  deepseek: {
    baseUrl: 'https://api.deepseek.com/v1',
    defaultModel: 'deepseek-chat',
    defaultTemperature: 0.7,
    defaultMaxTokens: 4096
  },
  claude: {
    baseUrl: 'https://api.anthropic.com/v1',
    defaultModel: 'claude-3-opus-20240229',
    defaultTemperature: 0.5,
    defaultMaxTokens: 4096
  },
  gemini: {
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    defaultModel: 'gemini-pro',
    defaultTemperature: 0.7,
    defaultMaxTokens: 2048
  },
  kimi: {
    baseUrl: 'https://api.moonshot.cn/v1',
    defaultModel: 'moonshot-v1-8k',
    defaultTemperature: 0.3,
    defaultMaxTokens: 8192
  },
  ollama: {
    baseUrl: 'http://localhost:11434/v1',
    defaultModel: 'llama2',
    defaultTemperature: 0.8,
    defaultMaxTokens: 2048
  }
};

// Scenario default parameters
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
const testResult = reactive({
  show: false,
  success: false,
  message: ''
});

// Show response format for extraction scenario only
const showResponseFormat = computed(() => {
  return props.scenario === 'extraction';
});

// Handle provider preset selection
const handleProviderChange = (provider) => {
  if (provider === 'custom') {
    return; // Keep current values
  }

  const preset = providerPresets[provider];
  if (preset) {
    config.baseUrl = preset.baseUrl;
    config.modelName = preset.defaultModel;

    // Apply provider-specific defaults only if not already set by user
    if (!props.initialConfig.temperature) {
      config.temperature = preset.defaultTemperature;
    }
    if (!props.initialConfig.maxTokens) {
      config.maxTokens = preset.defaultMaxTokens;
    }
  }
};

// Test connection
const handleTestConnection = async () => {
  if (!config.modelName || !config.apiKey || !config.baseUrl) {
    ElMessage.warning('请填写模型名称、API Key 和 Base URL');
    return;
  }

  isTesting.value = true;
  testResult.show = false;

  try {
    const response = await testConnection({
      modelName: config.modelName,
      apiKey: config.apiKey,
      baseUrl: config.baseUrl,
      scenario: props.scenario
    });

    // 拦截器返回完整响应结构 {code, msg, data}
    if (response.code === 1000 && response.data?.success) {
      testResult.success = true;
      testResult.message = '连接成功 ✓';
      emit('test', { scenario: props.scenario, success: true });
    } else {
      testResult.success = false;
      testResult.message = response.data?.message || response.msg || '连接失败';
      emit('test', { scenario: props.scenario, success: false, error: testResult.message });
    }
  } catch (error) {
    testResult.success = false;
    testResult.message = '连接失败: ' + (error.message || '网络错误');
    emit('test', { scenario: props.scenario, success: false, error: error.message });
  } finally {
    isTesting.value = false;
    testResult.show = true;
  }
};

// Save configuration
const handleSave = () => {
  if (!testResult.success) {
    ElMessage.warning('请先测试连接通过后再保存');
    return;
  }

  emit('save', {
    scenario: props.scenario,
    config: {
      modelName: config.modelName,
      apiKey: config.apiKey,
      baseUrl: config.baseUrl,
      temperature: config.temperature,
      maxTokens: config.maxTokens,
      responseFormat: config.responseFormat
    }
  });
};

// Watch initialConfig changes
watch(() => props.initialConfig, (newConfig) => {
  if (newConfig) {
    config.modelName = newConfig.modelName || '';
    config.apiKey = newConfig.apiKey || '';
    config.baseUrl = newConfig.baseUrl || '';
    config.temperature = newConfig.temperature || scenarioDefaults[props.scenario]?.temperature || 0.5;
    config.maxTokens = newConfig.maxTokens || scenarioDefaults[props.scenario]?.maxTokens || 2048;
    config.responseFormat = newConfig.responseFormat || scenarioDefaults[props.scenario]?.responseFormat || 'text';
    testResult.show = false;
    testResult.success = false;
  }
}, { deep: true });

// 暴露方法供父组件调用（一键配置）
const setConfig = (newConfig) => {
  config.modelName = newConfig.modelName || '';
  config.apiKey = newConfig.apiKey || '';
  config.baseUrl = newConfig.baseUrl || '';
  // 保留场景特定的参数，只同步基础配置
  // temperature, maxTokens, responseFormat 保留场景默认值
  testResult.show = false;
  testResult.success = false;
};

// 获取当前配置（供父组件读取）
const getConfig = () => {
  return {
    modelName: config.modelName,
    apiKey: config.apiKey,
    baseUrl: config.baseUrl,
    temperature: config.temperature,
    maxTokens: config.maxTokens,
    responseFormat: config.responseFormat
  };
};

defineExpose({ setConfig, getConfig });
</script>

<style scoped>
.scenario-config-form {
  padding: 20px;
  background-color: rgba(255, 255, 255, 0.6);
  border-radius: 10px;
}

.el-form-item {
  margin-bottom: 20px;
}

.param-hint {
  display: block;
  width: 100%;
  font-size: 12px;
  color: #909399;
  margin-top: 10px;
  margin-left: 4px;
}

.save-hint {
  display: inline-block;
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

.test-result {
  display: inline-flex;
  align-items: center;
  margin-left: 10px;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 13px;
}

.test-result.success {
  background-color: rgba(103, 194, 58, 0.1);
  color: #67c23a;
}

.test-result.error {
  background-color: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}

.test-result .el-icon {
  margin-right: 5px;
}

/* Transition */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* ============================================
   Form Input Field Polishing
   ============================================ */

/* --- Core input wrapper (shared by el-input, el-select, el-input-number) --- */
:deep(.el-input__wrapper) {
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  background-color: rgba(255, 255, 255, 0.85);
  box-shadow: none;
  transition: border-color 0.25s ease, box-shadow 0.25s ease, background-color 0.25s ease;
}

:deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 0, 0, 0.25);
  background-color: rgba(255, 255, 255, 0.95);
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #0084ff;
  box-shadow: 0 0 0 3px rgba(0, 132, 255, 0.1);
  background-color: #fff;
}

/* --- Inner input text --- */
:deep(.el-input__inner) {
  color: #303133;
  font-size: 14px;
}

:deep(.el-input__inner::placeholder) {
  color: #a8abb2;
}

/* --- Prepend icon area --- */
:deep(.el-input-group__prepend) {
  border-radius: 8px 0 0 8px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-right: none;
  background-color: rgba(0, 0, 0, 0.025);
  padding: 0 12px;
  transition: border-color 0.25s ease, background-color 0.25s ease;
  box-shadow: none;
}

:deep(.el-input-group__prepend .el-icon) {
  color: #909399;
  transition: color 0.25s ease;
}

/* Prepend border matches focus state */
:deep(.el-input-group:focus-within .el-input-group__prepend) {
  border-color: #0084ff;
  background-color: rgba(0, 132, 255, 0.04);
}

:deep(.el-input-group:focus-within .el-input-group__prepend .el-icon) {
  color: #0084ff;
}

/* --- Input wrapper inside a prepend group: left border-radius removed --- */
:deep(.el-input-group .el-input__wrapper) {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

/* --- el-select --- */
:deep(.el-select .el-input__wrapper) {
  cursor: pointer;
}

:deep(.el-select .el-input__inner) {
  cursor: pointer;
}

/* --- el-input-number --- */
:deep(.el-input-number .el-input__wrapper) {
  padding-left: 12px;
  padding-right: 12px;
}

:deep(.el-input-number.is-controls-right .el-input__wrapper) {
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
}

/* --- el-input-number decrease/increase buttons --- */
:deep(.el-input-number__decrease),
:deep(.el-input-number__increase) {
  background-color: rgba(0, 0, 0, 0.025);
  border: 1px solid rgba(0, 0, 0, 0.12);
  color: #606266;
  transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
}

:deep(.el-input-number__decrease:hover),
:deep(.el-input-number__increase:hover) {
  color: #0084ff;
  background-color: rgba(0, 132, 255, 0.06);
}

:deep(.el-input-number__decrease.is-disabled),
:deep(.el-input-number__increase.is-disabled) {
  color: #c0c4cc;
  background-color: rgba(0, 0, 0, 0.015);
}

/* --- el-slider polish (input area) --- */
:deep(.el-slider__input) {
  width: 64px;
}

:deep(.el-slider__input .el-input__wrapper) {
  padding-left: 8px;
  padding-right: 8px;
}

/* --- Ensure el-form-item content wraps properly --- */
:deep(.el-form-item__content) {
  flex-wrap: wrap;
}
</style>