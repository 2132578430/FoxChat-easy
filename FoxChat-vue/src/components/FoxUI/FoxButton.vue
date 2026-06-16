<template>
  <button
    class="fox-btn"
    :class="[
      `fox-btn--${type}`,
      `fox-btn--${size}`,
      { 'fox-btn--round': round, 'fox-btn--loading': loading, 'fox-btn--block': block }
    ]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="fox-btn__spinner"></span>
    <slot />
  </button>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'primary' },   // primary | ghost | danger | text
  size: { type: String, default: 'default' },    // small | default | large
  round: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['click']);
const handleClick = (e) => { emit('click', e); };
</script>

<style scoped>
.fox-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-weight: 500;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  user-select: none;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}

/* Sizes */
.fox-btn--default { height: 36px; padding: 0 20px; font-size: 14px; border-radius: 10px; }
.fox-btn--small   { height: 30px; padding: 0 14px; font-size: 13px; border-radius: 8px; }
.fox-btn--large   { height: 44px; padding: 0 28px; font-size: 16px; border-radius: 12px; }

.fox-btn--round { border-radius: 20px; }

/* Types */
.fox-btn--primary {
  background: #4a90d9;
  color: #fff;
  box-shadow: 0 2px 8px rgba(74, 144, 217, 0.25);
}
.fox-btn--primary:hover:not(:disabled) {
  background: #3a7bc8;
  box-shadow: 0 2px 12px rgba(74, 144, 217, 0.3);
}
.fox-btn--primary:active:not(:disabled) {
  box-shadow: 0 2px 4px rgba(74, 144, 217, 0.2);
}

.fox-btn--ghost {
  background: rgba(255,255,255,0.4);
  color: #555;
  border: 1px solid rgba(0,0,0,0.08);
}
.fox-btn--ghost:hover:not(:disabled) {
  background: rgba(255,255,255,0.7);
  border-color: rgba(0,0,0,0.15);
}

.fox-btn--danger {
  background: #f56c6c;
  color: #fff;
}
.fox-btn--danger:hover:not(:disabled) {
  background: #e04545;
}

.fox-btn--text {
  background: transparent;
  color: #ff6b9d;
}
.fox-btn--text:hover:not(:disabled) {
  background: rgba(255,107,157,0.08);
}

/* States */
.fox-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.fox-btn--loading {
  cursor: wait;
}

.fox-btn--block {
  width: 100%;
}

/* Spinner */
.fox-btn__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: fox-spin 0.6s linear infinite;
}

@keyframes fox-spin {
  to { transform: rotate(360deg); }
}
</style>
