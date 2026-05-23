<template>
  <div class="chat-input">
    <el-input
      v-model="localMessage"
      type="textarea"
      :rows="2"
      placeholder="请输入消息..."
      resize="none"
      @keydown.enter="handleInputEnter"
      ref="chatInputRef"
      class="chat-textarea"
    ></el-input>
    <div class="input-actions">
      <el-button
        v-if="showRag"
        type="primary"
        class="fox-btn upload-btn"
        :icon="Upload"
        @click="emit('open-upload')"
      >
        上传
      </el-button>
      <el-button
        type="primary"
        class="fox-btn send-btn"
        @click="handleSend"
        :disabled="!localMessage.trim() || (showRag && isSearchingRag)"
      >
        <template v-if="showRag && isSearchingRag">
          <el-icon class="loading-icon"><Loading /></el-icon>
        </template>
        <template v-else>
          发送
        </template>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import { Upload, Loading } from '@element-plus/icons-vue';

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  showRag: {
    type: Boolean,
    default: false
  },
  isSearchingRag: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue', 'send', 'open-upload']);

const chatInputRef = ref(null);

// 本地代理，保持与 v-model 双向绑定
const localMessage = ref(props.modelValue);

watch(
  () => props.modelValue,
  (val) => {
    if (val !== localMessage.value) {
      localMessage.value = val;
    }
  }
);

watch(localMessage, (val) => {
  emit('update:modelValue', val);
  nextTick(() => autoResizeTextarea());
});

// 处理回车键：Shift+Enter 换行，Enter 发送
const handleInputEnter = (e) => {
  if (e.shiftKey) {
    nextTick(() => autoResizeTextarea());
    return;
  }
  e.preventDefault();
  handleSend();
};

// 触发发送事件
const handleSend = () => {
  emit('send');
};

// 自动调整 textarea 高度
const autoResizeTextarea = () => {
  let textarea = chatInputRef.value?.$el?.querySelector('textarea');
  if (!textarea) {
    textarea = chatInputRef.value?.$refs?.textarea;
  }
  if (!textarea) {
    textarea = chatInputRef.value?.textareas?.[0];
  }

  if (textarea) {
    const content = localMessage.value || '';
    const lineHeight = 22;
    const baseHeight = 36;

    const lines = (content.match(/\n/g) || []).length + 1;
    let newHeight = baseHeight + (lines - 1) * lineHeight;
    newHeight = Math.min(newHeight, 200);

    textarea.style.height = newHeight + 'px';
  }
};
</script>

<style scoped>
.chat-input {
  flex-shrink: 0;
  width: 100%;
  max-width: 700px;
  margin: 0 auto 16px;
  padding: 12px 16px;
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  gap: 24px;
  z-index: 100;
}

.chat-input :deep(.el-textarea) {
  flex: 1;
  overflow: visible !important;
}

.chat-input :deep(.el-textarea__inner) {
  background-color: transparent;
  border-radius: 12px;
  border: none;
  padding: 8px 12px 14px;
  resize: none;
  box-shadow: none !important;
  transition: height 0.2s ease;
  line-height: 22px;
  color: var(--text-primary);
  overflow-y: hidden !important;
}

.chat-input .chat-textarea :deep(textarea) {
  height: 36px;
  min-height: 36px;
  max-height: 200px;
}

.chat-input :deep(.el-textarea__inner:focus) {
  background-color: rgba(255, 255, 255, 0.95);
  border-color: transparent;
  box-shadow: 0 0 0 2px var(--accent-color) !important;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Button styles matching input visual style */
.input-actions .fox-btn,
.input-actions .upload-btn,
.input-actions .send-btn {
  height: 44px;
  min-width: 90px;
  padding: 10px 24px;
  border-radius: 12px;
  font-size: 15px;
  letter-spacing: 1px;
}
</style>
