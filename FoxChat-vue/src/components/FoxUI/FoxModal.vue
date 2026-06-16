<template>
  <Teleport to="body">
    <transition name="fox-modal">
      <div v-if="modelValue" class="fox-modal-overlay" @click.self="onOverlayClick">
        <div class="fox-modal" :style="{ width: width }">
          <div class="fox-modal__header">
            <h3 class="fox-modal__title">{{ title }}</h3>
            <button class="fox-modal__close" @click="close">✕</button>
          </div>
          <div class="fox-modal__body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="fox-modal__footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  width: { type: String, default: '420px' },
  closeOnOverlay: { type: Boolean, default: true },
});

const emit = defineEmits(['update:modelValue']);

const close = () => emit('update:modelValue', false);
const onOverlayClick = () => { if (props.closeOnOverlay) close(); };

const onKeydown = (e) => { if (e.key === 'Escape' && props.modelValue) close(); };
onMounted(() => document.addEventListener('keydown', onKeydown));
onUnmounted(() => document.removeEventListener('keydown', onKeydown));
</script>

<style scoped>
.fox-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.fox-modal {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.14);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fox-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.fox-modal__title {
  font-size: 17px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.fox-modal__close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #999;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.15s;
}
.fox-modal__close:hover { background: #f5f5f5; color: #333; }

.fox-modal__body {
  padding: 20px 24px;
  overflow-y: auto;
}

.fox-modal__footer {
  padding: 16px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #f0f0f0;
}

/* Transition */
.fox-modal-enter-active { transition: all 0.2s ease-out; }
.fox-modal-leave-active { transition: all 0.15s ease-in; }
.fox-modal-enter-from { opacity: 0; }
.fox-modal-enter-from .fox-modal { transform: scale(0.95); }
.fox-modal-leave-to { opacity: 0; }
.fox-modal-leave-to .fox-modal { transform: scale(0.95); }
</style>
