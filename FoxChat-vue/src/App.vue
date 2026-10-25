<script setup>
import { RouterView } from 'vue-router'
import TitleBar from '@/components/TitleBar.vue'

// Detect if running in Electron
const isElectron = typeof window !== 'undefined' && window.electronAPI
</script>

<template>
  <div class="app-container">
    <TitleBar v-if="isElectron" />
    <RouterView />
  </div>
</template>

<style>
html,
body {
  height: 100%;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'JetBrains Mono', 'HarmonyOS Sans', 'Microsoft YaHei', sans-serif;
  overscroll-behavior-y: none;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
}

@media (max-width: 768px) {
  .el-dialog {
    width: calc(100vw - 24px) !important;
    max-width: 560px;
    margin-top: 5vh !important;
  }

  .el-dialog__body {
    max-height: 70vh;
    overflow-y: auto;
  }

  .el-message-box {
    width: calc(100vw - 32px) !important;
  }
}
</style>
