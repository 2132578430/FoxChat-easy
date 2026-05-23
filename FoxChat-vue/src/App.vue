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
body {
  margin: 0;
  padding: 0;
  font-family: 'JetBrains Mono', 'HarmonyOS Sans', 'Microsoft YaHei', sans-serif;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
</style>
