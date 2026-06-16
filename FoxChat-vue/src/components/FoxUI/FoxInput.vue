<template>
  <div class="fox-input-wrapper" :class="{ 'fox-input--focused': focused, 'fox-input--disabled': disabled }">
    <textarea
      v-if="type === 'textarea'"
      ref="inputRef"
      class="fox-input fox-textarea"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :rows="rows"
      @input="onInput"
      @focus="focused = true"
      @blur="focused = false"
    ></textarea>
    <div v-else class="fox-input-inner">
      <input
        ref="inputRef"
        class="fox-input"
        :type="showPassword ? 'text' : type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        @input="onInput"
        @focus="focused = true"
        @blur="focused = false"
      />
      <button
        v-if="type === 'password'"
        type="button"
        class="fox-input__toggle"
        @click="showPassword = !showPassword"
      >{{ showPassword ? '🙈' : '👁' }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  rows: { type: Number, default: 3 },
});

const emit = defineEmits(['update:modelValue']);
const focused = ref(false);
const showPassword = ref(false);
const inputRef = ref(null);

const onInput = (e) => {
  emit('update:modelValue', e.target.value);
};
</script>

<style scoped>
.fox-input-wrapper {
  position: relative;
  border-radius: 10px;
  background: rgba(255,255,255,0.5);
  border: 1.5px solid rgba(0,0,0,0.08);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.fox-input--focused {
  border-color: #4a90d9;
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.12);
  background: rgba(255,255,255,0.8);
}

.fox-input--disabled {
  opacity: 0.45;
}

.fox-input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  color: #333;
  padding: 8px 12px;
  line-height: 1.5;
  resize: none;
}

.fox-input::placeholder {
  color: #bbb;
}

.fox-textarea {
  min-height: 80px;
}

.fox-input-inner {
  display: flex;
  align-items: center;
}

.fox-input__toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0 12px;
  font-size: 16px;
  opacity: 0.5;
}
.fox-input__toggle:hover { opacity: 1; }
</style>
