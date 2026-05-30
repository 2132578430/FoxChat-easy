<template>
  <div class="llm-config-panel">
    <!-- Header -->
    <div class="config-panel-header">
      <el-button :icon="Back" @click="handleClose" circle size="small"></el-button>
      <div class="header-info">
        <el-avatar :size="32" :src="resolveAvatarUrl(selectedFriend?.faceImage || selectedFriend?.face_image) || defaultAvatar"></el-avatar>
        <span class="header-title">{{ selectedFriend?.nickname || '创造物' }} 模型配置</span>
      </div>
      <el-select
        v-model="selectedFriendId"
        class="friend-selector"
        placeholder="选择创造物"
        size="small"
        @change="handleSelectFriendById"
      >
        <el-option
          v-for="friend in friendList"
          :key="friend.userId || friend.id || friend.llmId"
          :label="friend.nickname || friend.username"
          :value="String(friend.userId || friend.id || friend.llmId)"
        />
      </el-select>
    </div>

    <!-- Panel Body -->
    <div class="config-panel-body">
      <!-- Config Form -->
      <div class="config-form-panel" v-loading="isLoadingConfig">
        <el-tabs v-model="activeTab" type="card" class="scenario-tabs">
          <el-tab-pane label="外观" name="appearance">
            <div class="appearance-form">
              <div class="appearance-avatar-section">
                <div class="appearance-avatar-wrapper" @click="handleOpenAvatarCropper">
                  <el-avatar :size="100" :src="resolveAvatarUrl(appearanceForm.faceImage) || defaultAvatar"></el-avatar>
                  <div class="appearance-avatar-mask">
                    <el-icon :size="24"><UploadFilled /></el-icon>
                    <span>修改头像</span>
                  </div>
                </div>
              </div>
              <div class="appearance-nickname">
                <el-form label-position="top">
                  <el-form-item label="昵称">
                    <el-input v-model="appearanceForm.nickname" placeholder="模型昵称" maxlength="30" show-word-limit></el-input>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="isSavingAppearance" @click="handleSaveAppearance">保存外观</el-button>
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </el-tab-pane>

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

        <!-- Save Buttons -->
        <div class="save-all-container">
          <el-button
            type="warning"
            size="large"
            :icon="CopyDocument"
            @click="handleOneClickConfig"
          >
            一键配置
          </el-button>
          <el-button
            type="primary"
            size="large"
            :icon="Finished"
            :loading="isSavingAll"
            @click="handleSaveAll"
          >
            {{ isSavingAll ? '保存中...' : '保存所有配置' }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Back, Finished, CopyDocument, UploadFilled } from '@element-plus/icons-vue';
import ScenarioConfigForm from './ScenarioConfigForm.vue';
import { saveConfigsBatch, getConfigs } from '@/api/llmConfig';
import { updateLlmFriend } from '@/api/friend';

const props = defineProps({
  friendList: {
    type: Array,
    required: true,
    default: () => []
  },
  preselectedFriendId: {
    type: [String, Number],
    default: null
  },
  pendingLlmAvatarUrl: {
    type: String,
    default: null
  }
});

const emit = defineEmits(['close', 'open-avatar-cropper']);

const defaultAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png';

const resolveAvatarUrl = (url) => {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:12000'}${url}`;
};

// State variables
const selectedFriendId = ref(null);
const isLoadingConfig = ref(false);
const activeTab = ref('chat');

// Appearance form state
const appearanceForm = reactive({
  nickname: '',
  faceImage: ''
});
const isSavingAppearance = ref(false);

// Computed properties
const selectedFriend = computed(() => {
  return props.friendList.find(f => 
    String(f.userId || f.id || f.llmId) === String(selectedFriendId.value)
  ) || props.friendList[0] || null;
});

const currentLlmId = computed(() => {
  return selectedFriend.value?.userId || selectedFriend.value?.id || selectedFriend.value?.llmId || '';
});

// Configs state
const configs = reactive({
  chat: {},
  memory: {},
  summary: {},
  extraction: {},
  emotion: {}
});
const testResults = reactive({
  chat: false,
  memory: false,
  summary: false,
  extraction: false,
  emotion: false
});
const pendingConfigs = reactive({
  chat: null,
  memory: null,
  summary: null,
  extraction: null,
  emotion: null
});
const isSavingAll = ref(false);

// Refs for form components
const chatForm = ref(null);
const memoryForm = ref(null);
const summaryForm = ref(null);
const extractionForm = ref(null);
const emotionForm = ref(null);

const scenarioNames = {
  chat: '聊天对话',
  memory: '记忆存储',
  summary: '对话总结',
  extraction: '信息提取',
  emotion: '情绪识别'
};

const canSaveAll = computed(() => {
  return Object.values(testResults).every(result => result === true);
});

const canOneClickConfig = computed(() => {
  // Can use one-click config if we have chat config tested and passed
  return testResults.chat === true;
});

// Helper functions
const hasPendingConfigs = () => {
  return Object.values(pendingConfigs).some(config => config !== null);
};

const autoSaveCurrentConfig = async () => {
  const oldLlmId = currentLlmId.value;
  if (!oldLlmId) return;
  
  const allConfigs = [];
  Object.keys(pendingConfigs).forEach(scenario => {
    if (pendingConfigs[scenario]) {
      allConfigs.push({
        scenario,
        ...pendingConfigs[scenario]
      });
    }
  });
  
  // Also include configs that exist but weren't modified
  Object.keys(configs).forEach(scenario => {
    if (!pendingConfigs[scenario] && configs[scenario] && configs[scenario].modelName) {
      allConfigs.push({
        scenario,
        ...configs[scenario]
      });
    }
  });
  
  if (allConfigs.length > 0) {
    try {
      await saveConfigsBatch(oldLlmId, allConfigs);
      ElMessage.success('配置已自动保存');
    } catch (error) {
      console.error('自动保存失败:', error);
    }
  }
};

// Load configs for current LLM
const loadConfigs = async (llmId) => {
  if (!llmId) {
    return;
  }

  isLoadingConfig.value = true;
  
  // Reset test results and configs
  Object.keys(testResults).forEach(key => {
    testResults[key] = false;
  });
  Object.keys(configs).forEach(key => {
    configs[key] = {};
  });
  Object.keys(pendingConfigs).forEach(key => {
    pendingConfigs[key] = null;
  });

  try {
    const response = await getConfigs(llmId);

    if (response.code === 1000 && response.data) {
      response.data.forEach(config => {
        configs[config.scenario] = {
          modelName: config.modelName,
          apiKey: config.modelApiKey,
          baseUrl: config.modelBaseUrl,
          temperature: config.modelTemperature,
          maxTokens: config.modelMaxTokens,
          responseFormat: config.modelResponseFormat || 'text'
        };
        testResults[config.scenario] = true;
      });
    }
  } catch (error) {
    console.error('加载配置失败:', error);
    ElMessage.error('加载配置失败');
  } finally {
    isLoadingConfig.value = false;
  }
};

// Handle friend selection (from dropdown)
const handleSelectFriendById = async (friendId) => {
  if (!friendId) return;
  
  // Skip if same friend selected
  if (String(friendId) === String(selectedFriendId.value)) {
    return;
  }
  
  // Auto-save current config before switching
  if (selectedFriendId.value && hasPendingConfigs()) {
    await autoSaveCurrentConfig();
  }
  
  // Reset test results and pending configs
  Object.keys(testResults).forEach(key => { testResults[key] = false; });
  Object.keys(pendingConfigs).forEach(key => { pendingConfigs[key] = null; });
};

const handleSaveConfig = ({ scenario, config }) => {
  pendingConfigs[scenario] = config;
};

const handleTestResult = ({ scenario, success, error }) => {
  testResults[scenario] = success;

  if (success) {
    ElMessage.success(`${scenarioNames[scenario]} 测试连接成功`);
  } else {
    ElMessage.error(`${scenarioNames[scenario]} 测试连接失败: ${error || '未知错误'}`);
  }
};

// One-click config: copy current tab's config to all other scenarios
const handleOneClickConfig = () => {
  // 从当前活动的 tab 获取配置
  const currentFormRef = activeTab.value === 'chat' ? chatForm.value :
                        activeTab.value === 'memory' ? memoryForm.value :
                        activeTab.value === 'summary' ? summaryForm.value :
                        activeTab.value === 'extraction' ? extractionForm.value :
                        emotionForm.value;

  const currentConfig = currentFormRef?.getConfig?.();
  
  if (!currentConfig || !currentConfig.modelName) {
    ElMessage.warning('请先在当前场景填写配置');
    return;
  }
  
  const configToCopy = {
    modelName: currentConfig.modelName,
    apiKey: currentConfig.apiKey,
    baseUrl: currentConfig.baseUrl
  };
  
  // Get scenario-specific defaults
  const scenarioDefaults = {
    chat: { temperature: 0.8, maxTokens: 4096, responseFormat: 'text' },
    memory: { temperature: 0.3, maxTokens: 2048, responseFormat: 'text' },
    summary: { temperature: 0.5, maxTokens: 2048, responseFormat: 'text' },
    extraction: { temperature: 0.0, maxTokens: 2048, responseFormat: 'json_object' },
    emotion: { temperature: 0.0, maxTokens: 50, responseFormat: 'text' }
  };
  
  // Apply to all forms
  ['chat', 'memory', 'summary', 'extraction', 'emotion'].forEach(scenario => {
    const formRef = scenario === 'chat' ? chatForm.value :
                   scenario === 'memory' ? memoryForm.value :
                   scenario === 'summary' ? summaryForm.value :
                   scenario === 'extraction' ? extractionForm.value :
                   emotionForm.value;
    
    if (formRef) {
      const fullConfig = {
        ...configToCopy,
        ...scenarioDefaults[scenario]
      };
      formRef.setConfig(fullConfig);
    }
    
    // Update local configs state
    configs[scenario] = {
      ...configToCopy,
      ...scenarioDefaults[scenario]
    };
  });
  
  ElMessage.success('已将当前配置复制到所有场景');
};

const handleSaveAll = async () => {
  isSavingAll.value = true;

  try {
    const allConfigs = [];
    const scenarios = ['chat', 'memory', 'summary', 'extraction', 'emotion'];

    scenarios.forEach(scenario => {
      const pending = pendingConfigs[scenario];
      const existing = configs[scenario];
      const config = pending || existing;

      if (config && config.modelName && config.apiKey && config.baseUrl) {
        allConfigs.push({
          scenario,
          modelName: config.modelName,
          modelApiKey: config.apiKey,
          modelBaseUrl: config.baseUrl,
          modelTemperature: config.temperature || 0.5,
          modelMaxTokens: config.maxTokens || 2048,
          modelResponseFormat: config.responseFormat || 'text'
        });
      }
    });

    if (allConfigs.length === 0) {
      ElMessage.warning('没有可保存的配置');
      return;
    }

    const response = await saveConfigsBatch(currentLlmId.value, allConfigs);

    if (response.code === 1000) {
      ElMessage.success('配置保存成功');

      scenarios.forEach(scenario => {
        if (pendingConfigs[scenario]) {
          configs[scenario] = { ...pendingConfigs[scenario] };
          pendingConfigs[scenario] = null;
        }
      });
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

const handleClose = () => {
  emit('close');
};

// Initialize on mount
onMounted(() => {
  if (props.friendList.length > 0) {
    selectedFriendId.value = props.friendList[0].userId || props.friendList[0].id || props.friendList[0].llmId;
  }
});

// Watch friendList changes
watch(() => props.friendList, (newList) => {
  if (newList.length > 0 && !selectedFriendId.value) {
    selectedFriendId.value = newList[0].userId || newList[0].id || newList[0].llmId;
  }
}, { immediate: true });

// Watch currentLlmId to load configs
watch(currentLlmId, (newLlmId) => {
  if (newLlmId) {
    loadConfigs(newLlmId);
  }
}, { immediate: true });

// Watch preselectedFriendId to auto-select
watch(() => props.preselectedFriendId, (newId) => {
  if (newId && props.friendList.length > 0) {
    const friend = props.friendList.find(f =>
      String(f.userId || f.id || f.llmId) === String(newId)
    );
    if (friend) {
      selectedFriendId.value = newId;
    }
  }
}, { immediate: true });

// Watch selectedFriend to populate appearance form
watch(selectedFriend, (friend) => {
  if (friend) {
    appearanceForm.nickname = friend.nickname || '';
    appearanceForm.faceImage = friend.faceImage || friend.face_image || '';
  }
}, { immediate: true });

// Watch pendingLlmAvatarUrl to update faceImage in appearance form
watch(() => props.pendingLlmAvatarUrl, (newUrl) => {
  if (newUrl) {
    appearanceForm.faceImage = newUrl;
  }
});

// Open avatar cropper (emit to parent)
const handleOpenAvatarCropper = () => {
  emit('open-avatar-cropper');
};

// Save appearance
const handleSaveAppearance = async () => {
  if (!currentLlmId.value) return;
  isSavingAppearance.value = true;
  try {
    await updateLlmFriend({
      llmId: currentLlmId.value,
      nickname: appearanceForm.nickname,
      faceImage: appearanceForm.faceImage
    });
    ElMessage.success('外观已保存');
  } catch (error) {
    console.error('保存外观失败:', error);
    ElMessage.error('保存外观失败');
  } finally {
    isSavingAppearance.value = false;
  }
};
</script>

<style scoped>
.llm-config-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-panel, #f5f7fa);
  position: relative;
}

.config-panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-light, rgba(0,0,0,0.06));
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #262626);
  letter-spacing: 0.5px;
}

.config-panel-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Friend selector dropdown in header */
.friend-selector {
  margin-left: auto;
  width: 200px;
}

.config-form-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 16px 16px;
}

/* Scenario Tabs — clean default style */
.scenario-tabs {
  flex: 1;
  overflow: hidden;
  margin: 12px 0 0;
}

.scenario-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border-light, rgba(0,0,0,0.06));
}

.scenario-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  padding: 8px 16px;
}

.scenario-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-color, #0084ff);
  font-weight: 600;
}

.scenario-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--accent-color, #0084ff);
}

.scenario-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}

.save-all-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid var(--border-light, rgba(0,0,0,0.06));
  flex-shrink: 0;
}

.save-all-hint {
  font-size: 12px;
  color: var(--text-light, #909399);
  margin-left: 8px;
}

/* Appearance Form */
.appearance-form {
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.appearance-avatar-section {
  display: flex;
  justify-content: center;
}

.appearance-avatar-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
}

.appearance-avatar-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.3s;
  border-radius: 50%;
}

.appearance-avatar-wrapper:hover .appearance-avatar-mask {
  opacity: 1;
}

.appearance-nickname {
  width: 100%;
  max-width: 320px;
}

/* Buttons — use project CSS variables */
:deep(.el-button--primary) {
  background-color: var(--accent-color, #0084ff);
  border-color: var(--accent-color, #0084ff);
}

:deep(.el-button--primary:hover) {
  background-color: var(--accent-hover, #0066cc);
  border-color: var(--accent-hover, #0066cc);
}
</style>