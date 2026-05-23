<template>
  <div class="llm-config-page">
    <!-- Header -->
    <div class="config-header">
      <el-button :icon="Back" @click="handleBack" circle></el-button>
      <h2>创造物模型配置</h2>
    </div>

    <!-- Validation Message -->
    <div class="validation-message" :class="validationStatus">
      <el-icon :size="20">
        <WarningFilled v-if="!isConfigComplete" />
        <SuccessFilled v-else />
      </el-icon>
      <span>{{ validationMessage }}</span>
    </div>

    <!-- Tabs for 5 Scenarios -->
    <el-tabs v-model="activeTab" type="card" class="scenario-tabs">
      <el-tab-pane label="聊天对话" name="chat">
        <ScenarioConfigForm
          scenario="chat"
          :initial-config="configs.chat || {}"
          @save="handleSaveConfig"
          @test="handleTestResult"
          ref="chatForm"
        />
      </el-tab-pane>

      <el-tab-pane label="记忆存储" name="memory">
        <ScenarioConfigForm
          scenario="memory"
          :initial-config="configs.memory || {}"
          @save="handleSaveConfig"
          @test="handleTestResult"
          ref="memoryForm"
        />
      </el-tab-pane>

      <el-tab-pane label="对话总结" name="summary">
        <ScenarioConfigForm
          scenario="summary"
          :initial-config="configs.summary || {}"
          @save="handleSaveConfig"
          @test="handleTestResult"
          ref="summaryForm"
        />
      </el-tab-pane>

      <el-tab-pane label="信息提取" name="extraction">
        <ScenarioConfigForm
          scenario="extraction"
          :initial-config="configs.extraction || {}"
          @save="handleSaveConfig"
          @test="handleTestResult"
          ref="extractionForm"
        />
      </el-tab-pane>

      <el-tab-pane label="情绪识别" name="emotion">
        <ScenarioConfigForm
          scenario="emotion"
          :initial-config="configs.emotion || {}"
          @save="handleSaveConfig"
          @test="handleTestResult"
          ref="emotionForm"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- Save All Button -->
    <div class="save-all-container">
      <el-button
        type="warning"
        size="large"
        :icon="CopyDocument"
        @click="handleOneClickConfig"
        :disabled="!canOneClickConfig"
      >
        一键配置
      </el-button>
      <el-button
        type="primary"
        size="large"
        :icon="Finished"
        :loading="isSavingAll"
        :disabled="!canSaveAll"
        @click="handleSaveAll"
      >
        {{ isSavingAll ? '保存中...' : '保存所有配置' }}
      </el-button>
      <span class="save-all-hint" v-if="!canSaveAll">请先测试所有场景连接通过后再批量保存</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import {
  Back,
  Finished,
  WarningFilled,
  SuccessFilled,
  CopyDocument
} from '@element-plus/icons-vue';
import ScenarioConfigForm from '@/components/LlmConfig/ScenarioConfigForm.vue';
import { saveConfigsBatch, getConfigs, validateConfig } from '@/api/llmConfig';

const router = useRouter();
const route = useRoute();

const llmId = ref(route.query.llm_id || route.params.llmId || '');

// Form refs
const chatForm = ref(null);
const memoryForm = ref(null);
const summaryForm = ref(null);
const extractionForm = ref(null);
const emotionForm = ref(null);

// Active tab
const activeTab = ref('chat');

// Configurations state
const configs = reactive({
  chat: {},
  memory: {},
  summary: {},
  extraction: {},
  emotion: {}
});

// Test results state (track which scenarios passed test)
const testResults = reactive({
  chat: false,
  memory: false,
  summary: false,
  extraction: false,
  emotion: false
});

// Pending configs (from child form saves)
const pendingConfigs = reactive({
  chat: null,
  memory: null,
  summary: null,
  extraction: null,
  emotion: null
});

// UI state
const isSavingAll = ref(false);
const isConfigComplete = ref(false);
const validationMessage = ref('');

// Scenario names for display
const scenarioNames = {
  chat: '聊天对话',
  memory: '记忆存储',
  summary: '对话总结',
  extraction: '信息提取',
  emotion: '情绪识别'
};

// Can save all configurations only if all tests passed
const canSaveAll = computed(() => {
  return Object.values(testResults).every(result => result === true);
});

// Can one-click config only if current tab has modelName, apiKey, baseUrl
const canOneClickConfig = computed(() => {
  const currentConfig = configs[activeTab.value];
  return currentConfig?.modelName && currentConfig?.apiKey && currentConfig?.baseUrl;
});

// Validation status class
const validationStatus = computed(() => {
  return isConfigComplete.value ? 'success' : 'warning';
});

// Load existing configurations
const loadConfigs = async () => {
  if (!llmId.value) {
    ElMessage.error('缺少创造物 ID');
    return;
  }

  try {
    const response = await getConfigs(llmId.value);

    if (response.code === 1000 && response.data) {
      // Populate configs from API response
      response.data.forEach(config => {
        configs[config.scenario] = {
          modelName: config.modelName,
          apiKey: config.modelApiKey,
          baseUrl: config.modelBaseUrl,
          temperature: config.modelTemperature,
          maxTokens: config.modelMaxTokens,
          responseFormat: config.modelResponseFormat || 'text'
        };

        // Mark test as passed if config exists (assume existing configs are valid)
        testResults[config.scenario] = true;
      });

      // Update validation status
      checkValidation();
    }
  } catch (error) {
    console.error('加载配置失败:', error);
    ElMessage.error('加载配置失败');
  }
};

// Check validation
const checkValidation = async () => {
  try {
    const response = await validateConfig(llmId.value);

    if (response.code === 1000) {
      isConfigComplete.value = response.data.isValid;
      validationMessage.value = isConfigComplete.value
        ? '配置完成 ✓'
        : `请完成所有模型配置后开始聊天（已配置 ${response.data.configured}/${response.data.total} 个场景）`;
    } else {
      isConfigComplete.value = false;
      validationMessage.value = response.msg || '未完成所有模型配置';
    }
  } catch (error) {
    console.error('验证失败:', error);
    isConfigComplete.value = false;
    validationMessage.value = '验证配置失败';
  }
};

// Handle individual config save (from child form)
const handleSaveConfig = ({ scenario, config }) => {
  pendingConfigs[scenario] = config;
};

// Handle test result (from child form)
const handleTestResult = ({ scenario, success, error }) => {
  testResults[scenario] = success;

  if (success) {
    ElMessage.success(`${scenarioNames[scenario]} 测试连接成功`);
  } else {
    ElMessage.error(`${scenarioNames[scenario]} 测试连接失败: ${error || '未知错误'}`);
  }
};

// Save all configurations
const handleSaveAll = async () => {
  if (!canSaveAll.value) {
    ElMessage.warning('请先测试所有场景连接通过后再批量保存');
    return;
  }

  isSavingAll.value = true;

  try {
    // Collect all configs from pending state
    const allConfigs = [];

    Object.keys(pendingConfigs).forEach(scenario => {
      if (pendingConfigs[scenario]) {
        allConfigs.push({
          scenario,
          ...pendingConfigs[scenario]
        });
      }
    });

    // Also include configs that exist but weren't modified (from initial load)
    Object.keys(configs).forEach(scenario => {
      if (!pendingConfigs[scenario] && configs[scenario] && configs[scenario].modelName) {
        allConfigs.push({
          scenario,
          ...configs[scenario]
        });
      }
    });

    const response = await saveConfigsBatch(llmId.value, allConfigs);

    if (response.code === 1000) {
      ElMessage.success('所有配置保存成功');
      isConfigComplete.value = true;
      validationMessage.value = '配置完成 ✓';

      // Redirect back to home after successful save
      setTimeout(() => {
        router.push('/');
      }, 1500);
    } else {
      ElMessage.error(response.msg || '保存失败');
    }
  } catch (error) {
    console.error('批量保存失败:', error);
    ElMessage.error('保存配置失败: ' + (error.message || '网络错误'));
  } finally {
    isSavingAll.value = false;
  }
};

// Handle back button
const handleBack = () => {
  router.push('/');
};

// One-click config: copy current config to all scenarios
const handleOneClickConfig = () => {
  const formRefs = {
    chat: chatForm,
    memory: memoryForm,
    summary: summaryForm,
    extraction: extractionForm,
    emotion: emotionForm
  };

  // Get current tab's config
  const currentForm = formRefs[activeTab.value];
  if (!currentForm?.value?.getConfig) {
    ElMessage.warning('请先在当前场景填写配置');
    return;
  }

  const sourceConfig = currentForm.value.getConfig();

  if (!sourceConfig.modelName || !sourceConfig.apiKey || !sourceConfig.baseUrl) {
    ElMessage.warning('请先填写模型名称、API Key 和 Base URL');
    return;
  }

  // Copy to all other scenarios
  const targetScenarios = ['chat', 'memory', 'summary', 'extraction', 'emotion'].filter(s => s !== activeTab.value);

  targetScenarios.forEach(scenario => {
    const targetForm = formRefs[scenario];
    if (targetForm?.value?.setConfig) {
      targetForm.value.setConfig(sourceConfig);
      // Update configs state
      configs[scenario] = {
        ...configs[scenario],
        modelName: sourceConfig.modelName,
        apiKey: sourceConfig.apiKey,
        baseUrl: sourceConfig.baseUrl
      };
    }
  });

  ElMessage.success(`已将配置同步到 ${targetScenarios.map(s => scenarioNames[s]).join('、')}`);
};

// Initialize on mount
onMounted(async () => {
  if (llmId.value) {
    await loadConfigs();
  } else {
    validationMessage.value = '请完成所有模型配置后开始聊天（已配置 0/5 个场景）';
  }
});
</script>

<style scoped>
.llm-config-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background-color: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  margin-bottom: 20px;
}

.config-header h2 {
  margin: 0;
  color: #303133;
}

.validation-message {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 20px;
  background-color: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  margin-bottom: 20px;
  font-size: 14px;
}

.validation-message.success {
  background-color: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.3);
  color: #67c23a;
}

.validation-message.warning {
  background-color: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  color: #e6a23c;
}

.scenario-tabs {
  background-color: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  padding: 20px;
  min-height: 600px;
}

.save-all-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  padding: 20px;
  background-color: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  margin-top: 20px;
}

.save-all-hint {
  font-size: 12px;
  color: #909399;
}

/* Element Plus Tabs Override */
.el-tabs__item {
  font-weight: 500;
}

.el-tabs__content {
  padding-top: 10px;
}
</style>