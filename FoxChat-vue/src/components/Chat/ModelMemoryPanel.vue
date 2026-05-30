<template>
  <transition name="slide-fade">
    <div class="memory-panel" v-show="modelValue">
      <div class="panel-header">
        <div class="panel-title">
          <span class="title-icon">🧠</span>
          <span>模型记忆</span>
          <span class="title-sub" v-if="characterName">— {{ characterName }}</span>
        </div>
        <el-button circle size="small" :icon="Close" @click="emit('update:modelValue', false)" />
      </div>

      <!-- Loading -->
      <div class="panel-loading" v-if="loading">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- Empty -->
      <div class="panel-empty" v-else-if="!data">
        <span class="empty-icon">📭</span>
        <span class="empty-text">暂无记忆数据</span>
        <span class="empty-hint">请先激活模型或发送消息</span>
      </div>

      <!-- Content -->
      <template v-else>
        <el-tabs v-model="activeTab" class="memory-tabs">
          <el-tab-pane label="角色卡" name="card">
            <el-scrollbar class="tab-content">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="名字">{{ data.characterName || '未设置' }}</el-descriptions-item>
                <el-descriptions-item label="性格">{{ data.characterPersonality || '未设置' }}</el-descriptions-item>
                <el-descriptions-item label="健谈程度">
                  <el-progress
                    :percentage="Math.round((data.talkativeness || 0.5) * 100)"
                    :stroke-width="8"
                    :color="talkativenessColor"
                  />
                </el-descriptions-item>
                <el-descriptions-item label="动作风格">{{ data.characterActionStyle || '未设置' }}</el-descriptions-item>
                <el-descriptions-item label="常用动作">
                  <el-tag
                    v-for="action in data.characterCommonActions"
                    :key="action"
                    size="small"
                    class="action-tag"
                  >{{ action }}</el-tag>
                  <span v-if="!data.characterCommonActions?.length" class="text-muted">未设置</span>
                </el-descriptions-item>
              </el-descriptions>

              <div class="section-title">核心描述</div>
              <div class="text-block">{{ data.characterDescription || '未设置' }}</div>

              <div class="section-title" v-if="data.roleDeclaration || data.coreAnchorText">核心锚点</div>
              <div class="text-block" v-if="data.roleDeclaration">
                <span class="label">角色声明：</span>{{ data.roleDeclaration }}
              </div>
              <div class="text-block" v-if="data.coreAnchorText">
                <span class="label">核心锚点：</span>{{ data.coreAnchorText }}
              </div>

              <div class="section-title" v-if="data.characterExamples">示例对话</div>
              <div class="text-block example-block" v-if="data.characterExamples">{{ data.characterExamples }}</div>
            </el-scrollbar>
          </el-tab-pane>

          <el-tab-pane label="记忆" name="memory">
            <el-scrollbar class="tab-content">
              <div class="memory-count" v-if="data.memoryEvents?.length">
                共 {{ data.memoryEvents.length }} 条记忆
              </div>
              <div v-if="!data.memoryEvents?.length" class="empty-hint">暂无记忆事件</div>
              <el-timeline v-else>
                <el-timeline-item
                  v-for="event in data.memoryEvents"
                  :key="event.eventId"
                  :timestamp="event.occurredAt"
                  placement="top"
                  size="small"
                  :color="importanceColor(event.importance)"
                >
                  <div class="event-content">{{ event.content }}</div>
                  <div class="event-meta">
                    <el-tag size="small" :type="eventTypeTag(event.eventType)">{{ eventTypeLabel(event.eventType) }}</el-tag>
                    <span v-if="event.importance" class="importance-dot" :style="{ background: importanceColor(event.importance) }"></span>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </el-scrollbar>
          </el-tab-pane>

          <el-tab-pane label="画像" name="profile">
            <el-scrollbar class="tab-content">
              <div v-if="data.userProfile" class="text-block profile-text">{{ data.userProfile }}</div>
              <div v-else class="empty-hint">暂无用户画像</div>
              <div class="section-title" v-if="data.currentEmotion">当前情绪</div>
              <div class="text-block" v-if="data.currentEmotion">{{ data.currentEmotion }}</div>
            </el-scrollbar>
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { Close, Loading } from '@element-plus/icons-vue';
import { getModelMemory } from '@/api/llmConfig';

const props = defineProps({
  modelValue: Boolean,
  llmId: {
    type: [String, Number],
    default: null
  }
});

const emit = defineEmits(['update:modelValue']);

const loading = ref(false);
const data = ref(null);
const activeTab = ref('card');

const characterName = computed(() => data.value?.characterName || '');

const talkativenessColor = computed(() => {
  const t = data.value?.talkativeness || 0.5;
  if (t <= 0.3) return '#909399';
  if (t <= 0.6) return '#67c23a';
  if (t <= 0.8) return '#409eff';
  return '#e6a23c';
});

const EVENT_TYPE_MAP = {
  identity: '身份',
  preference: '偏好',
  boundary: '边界',
  follow_up: '事项',
  share_experience: '经历',
  commitment: '承诺',
  relation_change: '关系',
  express_emotion: '情绪',
  interaction: '互动',
  other: '其他'
};

const eventTypeLabel = (type) => EVENT_TYPE_MAP[type] || type || '其他';

const eventTypeTag = (type) => {
  const map = { identity: '', preference: 'info', boundary: 'danger', follow_up: 'warning', commitment: 'success' };
  return map[type] || '';
};

const importanceColor = (imp) => {
  if (imp >= 0.8) return '#f56c6c';
  if (imp >= 0.6) return '#409eff';
  return '#909399';
};

const fetchMemory = async () => {
  if (!props.llmId) return;
  loading.value = true;
  try {
    const res = await getModelMemory(props.llmId);
    data.value = res.data || res;
  } catch {
    data.value = null;
  } finally {
    loading.value = false;
  }
};

watch(() => props.llmId, (newVal) => {
  if (newVal && props.modelValue) {
    fetchMemory();
  }
});

watch(() => props.modelValue, (show) => {
  if (show && props.llmId) {
    fetchMemory();
  }
});
</script>

<style scoped>
.memory-panel {
  width: 340px;
  background: var(--bg-panel, #fff);
  border-left: 1px solid var(--border-light, rgba(0,0,0,0.08));
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  z-index: 10;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 20px rgba(0,0,0,0.06);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 12px;
  border-bottom: 1px solid var(--border-light, rgba(0,0,0,0.06));
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 18px;
}

.title-sub {
  font-weight: 400;
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

.panel-loading, .panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-secondary, #909399);
  font-size: 14px;
}

.empty-icon {
  font-size: 36px;
}

.empty-text {
  font-weight: 500;
  color: var(--text-primary, #303133);
}

.empty-hint {
  font-size: 12px;
  color: var(--text-secondary, #909399);
}

.memory-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.memory-tabs :deep(.el-tabs__header) {
  margin: 0 16px;
}

.memory-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.tab-content {
  padding: 8px 16px 16px;
  height: 100%;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 16px 0 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light, rgba(0,0,0,0.05));
}

.text-block {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-regular, #606266);
  white-space: pre-wrap;
}

.example-block {
  font-style: italic;
  color: var(--text-secondary, #909399);
}

.label {
  font-weight: 500;
  color: var(--text-secondary, #909399);
}

.action-tag {
  margin: 2px 4px 2px 0;
}

.text-muted {
  color: var(--text-secondary, #909399);
  font-size: 12px;
}

.memory-count {
  font-size: 12px;
  color: var(--text-secondary, #909399);
  margin-bottom: 12px;
}

.event-content {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-regular, #606266);
  margin-bottom: 4px;
}

.event-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.importance-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.profile-text {
  white-space: pre-line;
}

/* Slide animation — reuse project's slide-fade */
.slide-fade-enter-active {
  transition: all 0.25s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
