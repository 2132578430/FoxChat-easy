<template>
  <div class="fox-avatar" :class="{ 'fox-avatar--online': online, 'fox-avatar--rounded': shape === 'rounded' }" :style="{ width: size + 'px', height: size + 'px' }">
    <img v-if="src" :src="src" :alt="alt" class="fox-avatar__img" @error="onError" />
    <span v-else class="fox-avatar__fallback">{{ fallback }}</span>
    <span v-if="$slots.badge || online !== undefined" class="fox-avatar__badge" :class="{ 'fox-avatar__badge--online': online, 'fox-avatar__badge--offline': online === false }">
      <slot name="badge" />
    </span>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  size: { type: Number, default: 44 },
  shape: { type: String, default: 'circle' },  // circle | rounded
  fallback: { type: String, default: '🦊' },
  online: { type: Boolean, default: undefined }, // true=在线, false=离线, undefined=不显示
});

const imgError = ref(false);
const onError = () => { imgError.value = true; };
</script>

<style scoped>
.fox-avatar {
  position: relative;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: 2px solid rgba(255,255,255,0.8);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ffe0e8, #ffe8d0);
}

.fox-avatar--rounded { border-radius: 12px; }

.fox-avatar__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.fox-avatar__fallback {
  font-size: calc(var(--avatar-size, 44px) * 0.45);
  line-height: 1;
}

.fox-avatar__badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #fff;
}

.fox-avatar__badge--online  { background: #67c23a; }
.fox-avatar__badge--offline { background: #c0c4cc; }
</style>
