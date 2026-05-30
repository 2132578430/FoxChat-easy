<template>
  <div class="llm-config-panel">
    <!-- Header -->
    <div class="panel-header">
      <el-button :icon="Back" @click="handleClose" circle size="small" class="back-btn" />
      <span class="header-title">模型配置</span>
    </div>

    <!-- Body: left list + right form -->
    <div class="panel-body">
      <!-- Left: Friend List -->
      <div class="friend-sidebar">
        <div class="sidebar-label">创造物</div>
        <div class="friend-list">
          <div
            v-for="friend in friendList"
            :key="friend.userId || friend.id || friend.llmId"
            class="friend-item"
            :class="{ active: String(friend.userId || friend.id || friend.llmId) === String(selectedFriendId) }"
            @click="handleSelectFriendById(String(friend.userId || friend.id || friend.llmId))"
          >
            <el-avatar :size="36" :src="resolveAvatarUrl(friend.faceImage || friend.face_image) || defaultAvatar" />
            <span class="friend-name">{{ friend.nickname || friend.username }}</span>
          </div>
          <div v-if="friendList.length === 0" class="friend-empty">暂无创造物</div>
        </div>
      </div>

      <!-- Right: Config Form -->
      <div class="config-main" v-loading="isLoadingConfig">
        <el-tabs v-model="activeTab" class="config-tabs">
          <el-tab-pane label="外观" name="appearance">
            <div class="appearance-form">
              <div class="avatar-upload" @click="handleOpenAvatarCropper">
                <el-avatar :size="80" :src="resolveAvatarUrl(appearanceForm.faceImage) || defaultAvatar" />
                <div class="avatar-overlay"><el-icon :size="20"><UploadFilled /></el-icon></div>
              </div>
              <el-form label-position="top" class="nickname-form">
                <el-form-item label="昵称">
                  <el-input v-model="appearanceForm.nickname" placeholder="模型昵称" maxlength="30" show-word-limit />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="isSavingAppearance" @click="handleSaveAppearance">保存外观</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <el-tab-pane label="聊天对话" name="chat">
            <ScenarioConfigForm scenario="chat" :initial-config="configs.chat || {}" @save="handleSaveConfig" @test="handleTestResult" ref="chatForm" />
          </el-tab-pane>
          <el-tab-pane label="记忆存储" name="memory">
            <ScenarioConfigForm scenario="memory" :initial-config="configs.memory || {}" @save="handleSaveConfig" @test="handleTestResult" ref="memoryForm" />
          </el-tab-pane>
          <el-tab-pane label="对话总结" name="summary">
            <ScenarioConfigForm scenario="summary" :initial-config="configs.summary || {}" @save="handleSaveConfig" @test="handleTestResult" ref="summaryForm" />
          </el-tab-pane>
          <el-tab-pane label="信息提取" name="extraction">
            <ScenarioConfigForm scenario="extraction" :initial-config="configs.extraction || {}" @save="handleSaveConfig" @test="handleTestResult" ref="extractionForm" />
          </el-tab-pane>
          <el-tab-pane label="情绪识别" name="emotion">
            <ScenarioConfigForm scenario="emotion" :initial-config="configs.emotion || {}" @save="handleSaveConfig" @test="handleTestResult" ref="emotionForm" />
          </el-tab-pane>
        </el-tabs>

        <div class="form-footer">
          <el-button :icon="CopyDocument" @click="handleOneClickConfig">一键配置</el-button>
          <el-button type="primary" :icon="Finished" :loading="isSavingAll" @click="handleSaveAll">
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

  // Update selection
  selectedFriendId.value = friendId;
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
  background: var(--bg-panel, #f8f9fa);
}

/* Header */
.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-light, #eee);
  flex-shrink: 0;
}
.back-btn { flex-shrink: 0; }
.header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #303133);
}

/* Body: split pane */
.panel-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Left sidebar */
.friend-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--bg-sidebar, #fafbfc);
  border-right: 1px solid var(--border-light, #eee);
  display: flex;
  flex-direction: column;
}
.sidebar-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #909399);
  text-transform: uppercase;
  padding: 16px 16px 8px;
}
.friend-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}
.friend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.friend-item:hover { background: var(--accent-hover, rgba(0,132,255,0.06)); }
.friend-item.active { background: var(--accent-active, rgba(0,132,255,0.1)); }
.friend-name {
  font-size: 14px;
  color: var(--text-primary, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.friend-empty {
  padding: 32px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

/* Right main */
.config-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-card, #fff);
}

/* Tabs */
.config-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.config-tabs :deep(.el-tabs__header) {
  margin: 0 20px;
  border-bottom: 1px solid var(--border-light, #eee);
}
.config-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  padding: 10px 16px;
  color: var(--text-secondary, #606266);
}
.config-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-color, #0084ff);
  font-weight: 600;
}
.config-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--accent-color, #0084ff);
}
.config-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px;
}

/* Footer */
.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border-light, #eee);
  background: var(--bg-card, #fff);
  flex-shrink: 0;
}

/* Appearance tab */
.appearance-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  gap: 24px;
}
.avatar-upload {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
}
.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  opacity: 0;
  transition: opacity 0.2s;
}
.avatar-upload:hover .avatar-overlay { opacity: 1; }
.nickname-form {
  width: 100%;
  max-width: 320px;
}

/* Buttons */
:deep(.el-button--primary) {
  background-color: var(--accent-color, #0084ff);
  border-color: var(--accent-color, #0084ff);
}
:deep(.el-button--primary:hover) {
  background-color: var(--accent-hover, #0066cc);
  border-color: var(--accent-hover, #0066cc);
}
</style>