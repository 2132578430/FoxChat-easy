<template>
  <div class="fox-select" :class="{ 'fox-select--open': open, 'fox-select--disabled': disabled }" ref="selectRef">
    <div class="fox-select__trigger" @click="toggle" :style="{ height: height }">
      <span class="fox-select__value" :class="{ placeholder: !displayText }">{{ displayText || placeholder }}</span>
      <span class="fox-select__arrow">▾</span>
    </div>
    <transition name="fox-select-drop">
      <div v-if="open" class="fox-select__dropdown">
        <div
          v-for="option in options"
          :key="option.value"
          class="fox-select__option"
          :class="{ active: modelValue === option.value }"
          @click="select(option.value)"
        >{{ option.label }}</div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },  // [{label, value}]
  placeholder: { type: String, default: '请选择' },
  disabled: { type: Boolean, default: false },
  height: { type: String, default: '36px' },
});

const emit = defineEmits(['update:modelValue', 'change']);
const open = ref(false);
const selectRef = ref(null);

const displayText = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue);
  return opt ? opt.label : '';
});

const toggle = () => {
  if (props.disabled) return;
  open.value = !open.value;
};

const select = (value) => {
  emit('update:modelValue', value);
  emit('change', value);
  open.value = false;
};

const closeOnClickOutside = (e) => {
  if (selectRef.value && !selectRef.value.contains(e.target)) open.value = false;
};
onMounted(() => document.addEventListener('click', closeOnClickOutside));
onUnmounted(() => document.removeEventListener('click', closeOnClickOutside));
</script>

<style scoped>
.fox-select { position: relative; user-select: none; }
.fox-select--disabled { opacity: 0.45; }

.fox-select__trigger {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid rgba(0,0,0,0.12); background: rgba(255,255,255,0.85);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.fox-select__trigger:hover { border-color: rgba(0,0,0,0.25); }
.fox-select--open .fox-select__trigger {
  border-color: #4a90d9; box-shadow: 0 0 0 3px rgba(74,144,217,0.1);
}
.fox-select__value { font-size: 14px; color: #333; }
.fox-select__value.placeholder { color: #aaa; }
.fox-select__arrow {
  font-size: 12px; color: #999; transition: transform 0.2s;
}
.fox-select--open .fox-select__arrow { transform: rotate(180deg); }

.fox-select__dropdown {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 100;
  background: #fff; border-radius: 8px; border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden; max-height: 220px;
  overflow-y: auto;
}
.fox-select__option {
  padding: 9px 14px; font-size: 14px; color: #333; cursor: pointer;
  transition: background 0.12s;
}
.fox-select__option:hover { background: rgba(74,144,217,0.06); }
.fox-select__option.active { color: #4a90d9; background: rgba(74,144,217,0.08); font-weight: 500; }

/* Dropdown animation */
.fox-select-drop-enter-active { transition: all 0.2s ease-out; }
.fox-select-drop-leave-active { transition: all 0.15s ease-in; }
.fox-select-drop-enter-from { opacity: 0; transform: translateY(-8px); }
.fox-select-drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
