<template>
  <div class="llm-config-panel">
    <!-- Header -->
    <div class="config-panel-header">
      <el-button :icon="Back" @click="handleClose" circle size="small"></el-button>
      <div class="header-info">
        <el-avatar :size="32" :src="resolveAvatarUrl(selectedFriend?.faceImage || selectedFriend?.face_image) || defaultAvatar"></el-avatar>
        <span class="header-title">{{ selectedFriend?.nickname || '创造物' }} 模型配置</span>
      </div>
    </div>

    <!-- Split Panel Body -->
    <div class="config-panel-body">
      <!-- Left: Friend List -->
      <div class="friend-list-panel">
        <div class="friend-list-header">
          <span>创造物</span>
        </div>
        <div class="friend-list-content">
          <div v-if="friendList.length === 0" class="empty-friend-tip">
            <el-icon :size="24"><UserFilled /></el-icon>
            <span>暂无创造物</span>
          </div>
          <div 
            v-for="friend in friendList" 
            :key="friend.userId || friend.id || friend.llmId"
            class="friend-item"
            :class="{ active: String(friend.userId || friend.id || friend.llmId) === String(selectedFriendId) }"
            @click="handleSelectFriend(friend)"
          >
            <el-avatar :size="36" :src="resolveAvatarUrl(friend.faceImage || friend.face_image) || defaultAvatar"></el-avatar>
            <div class="friend-item-info">
              <span class="friend-item-name">{{ friend.nickname || friend.username }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Config Form -->
      <div class="config-form-panel" v-loading="isLoadingConfig">
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

        <!-- Save Buttons -->
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
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Back, Finished, UserFilled, CopyDocument } from '@element-plus/icons-vue';
import ScenarioConfigForm from './ScenarioConfigForm.vue';
import { saveConfigsBatch, getConfigs } from '@/api/llmConfig';

const props = defineProps({
  friendList: {
    type: Array,
    required: true,
    default: () => []
  }
});

const emit = defineEmits(['close']);

const defaultAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png';

const resolveAvatarUrl = (url) => {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return `http://localhost:12000${url}`;
};

// State variables
const selectedFriendId = ref(null);
const isLoadingConfig = ref(false);
const activeTab = ref('chat');

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

// Handle friend selection
const handleSelectFriend = async (friend) => {
  const friendId = friend.userId || friend.id || friend.llmId;
  
  // Skip if same friend selected
  if (String(friendId) === String(selectedFriendId.value)) {
    return;
  }
  
  // Auto-save current config before switching (if has pending configs)
  if (selectedFriendId.value && hasPendingConfigs()) {
    await autoSaveCurrentConfig();
  }
  
  // Reset test results when switching
  Object.keys(testResults).forEach(key => {
    testResults[key] = false;
  });
  
  // Clear pending configs
  Object.keys(pendingConfigs).forEach(key => {
    pendingConfigs[key] = null;
  });
  
  // Set new friend
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

// One-click config: copy chat config to all other scenarios
const handleOneClickConfig = () => {
  if (!configs.chat || !configs.chat.modelName) {
    ElMessage.warning('请先配置并测试聊天对话场景');
    return;
  }
  
  const chatConfig = {
    modelName: configs.chat.modelName,
    apiKey: configs.chat.apiKey,
    baseUrl: configs.chat.baseUrl
  };
  
  // Get scenario-specific defaults
  const scenarioDefaults = {
    memory: { temperature: 0.3, maxTokens: 2048, responseFormat: 'text' },
    summary: { temperature: 0.5, maxTokens: 2048, responseFormat: 'text' },
    extraction: { temperature: 0.0, maxTokens: 2048, responseFormat: 'json_object' },
    emotion: { temperature: 0.0, maxTokens: 50, responseFormat: 'text' }
  };
  
  // Apply to all forms
  ['memory', 'summary', 'extraction', 'emotion'].forEach(scenario => {
    const formRef = scenario === 'memory' ? memoryForm.value :
                   scenario === 'summary' ? summaryForm.value :
                   scenario === 'extraction' ? extractionForm.value :
                   emotionForm.value;
    
    if (formRef) {
      const fullConfig = {
        ...chatConfig,
        ...scenarioDefaults[scenario]
      };
      formRef.setConfig(fullConfig);
    }
    
    // Update local configs state
    configs[scenario] = {
      ...chatConfig,
      ...scenarioDefaults[scenario]
    };
  });
  
  ElMessage.success('已将聊天配置复制到其他场景，请逐个测试连接');
};

const handleSaveAll = async () => {
  if (!canSaveAll.value) {
    ElMessage.warning('请先测试所有场景连接通过后再批量保存');
    return;
  }

  isSavingAll.value = true;

  try {
    const allConfigs = [];

    Object.keys(pendingConfigs).forEach(scenario => {
      if (pendingConfigs[scenario]) {
        allConfigs.push({
          scenario,
          ...pendingConfigs[scenario]
        });
      }
    });

    Object.keys(configs).forEach(scenario => {
      if (!pendingConfigs[scenario] && configs[scenario] && configs[scenario].modelName) {
        allConfigs.push({
          scenario,
          ...configs[scenario]
        });
      }
    });

    const response = await saveConfigsBatch(currentLlmId.value, allConfigs);

    if (response.code === 1000) {
      ElMessage.success('所有配置保存成功');
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
</script>

<style scoped>
/* Glass-morphism Design System - Matching Home.vue Profile Panel */
.llm-config-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-gradient, linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%));
  position: relative;
}

/* Header Panel - Flat Design */
.config-panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  margin: 12px;
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
  overflow: hidden;
  padding: 0 12px 12px;
  gap: 12px;
}

/* Left: Friend List Panel - Flat Design Sidebar */
.friend-list-panel {
  width: 220px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.friend-list-header {
  padding: 16px 20px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #262626);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.5px;
}

.friend-list-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-friend-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  color: var(--text-light, #909399);
  font-size: 13px;
}

.empty-friend-tip .el-icon {
  color: var(--text-secondary, #8e8e8e);
}

/* Friend Item - Flat Design List Style (Matching FriendList.vue) */
.friend-item {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  cursor: pointer;
  border-radius: 8px;
  margin: 0 8px 4px;
  transition: background-color 0.2s ease;
}

.friend-item:hover {
  background-color: var(--accent-hover, rgba(0, 132, 255, 0.08));
}

.friend-item.active {
  background-color: var(--accent-active, rgba(0, 132, 255, 0.12));
}

.friend-item-info {
  flex: 1;
  overflow: hidden;
}

.friend-item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Right: Config Form Panel - Flat Design */
.config-form-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
}

/* Scenario Tabs - Modern Minimalist */
.scenario-tabs {
  flex: 1;
  background: transparent;
  margin: 16px;
  overflow: hidden;
}

.scenario-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.scenario-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0;
}

.scenario-tabs :deep(.el-tabs__nav-scroll) {
  overflow-x: auto;
  overflow-y: hidden;
}

.scenario-tabs :deep(.el-tabs__content) {
  height: calc(100% - 48px);
  overflow-y: auto;
  padding-right: 4px;
}

.scenario-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  padding: 0 16px;
  height: 38px;
  line-height: 38px;
  color: var(--text-secondary, #666);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
  letter-spacing: 0.5px;
}

.scenario-tabs :deep(.el-tabs__item:hover) {
  color: var(--accent-color, #0084ff);
}

.scenario-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-color, #0084ff);
  font-weight: 600;
}

.scenario-tabs :deep(.el-tabs--card > .el-tabs__header .el-tabs__item) {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 8px 8px 0 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
  margin-right: 4px;
}

.scenario-tabs :deep(.el-tabs--card > .el-tabs__header .el-tabs__item.is-active) {
  background: rgba(0, 132, 255, 0.08);
  border-bottom-color: var(--accent-color, #0084ff);
  border-color: rgba(0, 132, 255, 0.15);
}

/* Save Buttons Container - Flat Design Footer */
.save-all-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.4);
  margin: 0 16px 16px;
  border-radius: 12px;
  flex-shrink: 0;
}

.save-all-hint {
  font-size: 12px;
  color: var(--text-light, #909399);
  margin-left: 8px;
}

/* Custom Scrollbar */
.friend-list-content::-webkit-scrollbar,
.scenario-tabs :deep(.el-tabs__content)::-webkit-scrollbar {
  width: 6px;
}

.friend-list-content::-webkit-scrollbar-thumb,
.scenario-tabs :deep(.el-tabs__content)::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
  transition: background 0.3s;
}

.friend-list-content::-webkit-scrollbar-thumb:hover,
.scenario-tabs :deep(.el-tabs__content)::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

.friend-list-content::-webkit-scrollbar-track,
.scenario-tabs :deep(.el-tabs__content)::-webkit-scrollbar-track {
  background: transparent;
}

/* Override Element Plus Button Styles - Modern Minimalist */
:deep(.el-button--primary) {
  background-color: var(--button-bg, #0084ff);
  border-color: var(--button-bg, #0084ff);
  color: var(--button-text, #fff);
  font-weight: 600;
  letter-spacing: 0.5px;
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-button--primary:hover),
:deep(.el-button--primary:focus) {
  background-color: var(--button-hover, #0066cc);
  border-color: var(--button-hover, #0066cc);
}

:deep(.el-button--warning) {
  background-color: #e6a23c;
  border-color: #e6a23c;
  color: #fff;
  font-weight: 600;
  letter-spacing: 0.5px;
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-button--warning:hover),
:deep(.el-button--warning:focus) {
  background-color: #d09a30;
  border-color: #d09a30;
}

:deep(.el-button.is-circle) {
  border-radius: 50%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-button.is-circle:hover) {
  opacity: 0.9;
}
</style>