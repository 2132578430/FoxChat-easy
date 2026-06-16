<template>
  <div class="chat-input">
    <textarea
      ref="textareaRef"
      v-model="localMessage"
      class="chat-textarea"
      :rows="2"
      placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
      @keydown.enter="handleInputEnter"
      @input="autoResize"
    ></textarea>
    <div class="input-actions">
      <FoxButton
        v-if="showRag"
        type="ghost"
        size="small"
        @click="emit('open-upload')"
      >上传</FoxButton>
      <FoxButton
        type="primary"
        class="send-btn"
        :disabled="!localMessage.trim() || (showRag && isSearchingRag)"
        :loading="showRag && isSearchingRag"
        @click="handleSend"
      >➤</FoxButton>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import { FoxButton } from '@/components/FoxUI';

const props = defineProps({
  modelValue: { type: String, default: '' },
  showRag: { type: Boolean, default: false },
  isSearchingRag: { type: Boolean, default: false }
});

const emit = defineEmits(['update:modelValue', 'send', 'open-upload']);

const textareaRef = ref(null);
const localMessage = ref(props.modelValue);

watch(() => props.modelValue, (val) => { if (val !== localMessage.value) localMessage.value = val; });
watch(localMessage, (val) => emit('update:modelValue', val));

const autoResize = () => {
  nextTick(() => {
    const el = textareaRef.value;
    if (!el) return;
    el.style.height = 'auto';
    const maxH = 160;
    el.style.height = Math.min(el.scrollHeight, maxH) + 'px';
  });
};

const handleInputEnter = (e) => {
  if (e.shiftKey) return;
  e.preventDefault();
  handleSend();
};

const handleSend = () => {
  if (!localMessage.value.trim()) return;
  emit('send');
};
</script>

<style scoped>
.chat-input {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 700px;
  padding: 10px 14px;
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.6);
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
  display: flex; align-items: flex-end; gap: 10px; z-index: 10;
}

.chat-textarea {
  flex: 1; border: none; outline: none; background: transparent;
  font-family: inherit; font-size: 15px; line-height: 1.6;
  color: #333; resize: none; padding: 10px 4px;
  min-height: 52px; max-height: 160px;
}

.chat-textarea::placeholder { color: #bbb; }

.input-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; padding-bottom: 2px; }

.send-btn {
  width: 38px; height: 38px; padding: 0; border-radius: 50% !important;
  font-size: 18px; display: flex; align-items: center; justify-content: center;
}
</style>
