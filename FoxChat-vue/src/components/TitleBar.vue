<template>
  <div class="title-bar">
    <div class="title-bar-left">
      <img src="/fox.svg" alt="FoxChat" class="title-bar-icon" />
      <span class="title-bar-title">FoxChat</span>
    </div>
    <div class="title-bar-controls">
      <button class="title-bar-btn minimize" @click="minimize">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect y="5" width="12" height="2" fill="currentColor"/>
        </svg>
      </button>
      <button class="title-bar-btn maximize" @click="maximize">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect x="1" y="1" width="10" height="10" stroke="currentColor" stroke-width="2" fill="none"/>
        </svg>
      </button>
      <button class="title-bar-btn close" @click="close">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M1 1L11 11M11 1L1 11" stroke="currentColor" stroke-width="2"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
const minimize = () => {
  if (window.electronAPI) {
    window.electronAPI.minimizeWindow();
  }
};

const maximize = () => {
  if (window.electronAPI) {
    window.electronAPI.maximizeWindow();
  }
};

const close = () => {
  if (window.electronAPI) {
    window.electronAPI.closeWindow();
  }
};
</script>

<style scoped>
.title-bar {
  height: 32px;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  -webkit-app-region: drag;
  user-select: none;
}

.title-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  -webkit-app-region: no-drag;
}

.title-bar-icon {
  width: 20px;
  height: 20px;
}

.title-bar-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.title-bar-controls {
  display: flex;
  gap: 0;
  -webkit-app-region: no-drag;
}

.title-bar-btn {
  width: 36px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #666;
  transition: background-color 0.15s;
}

.title-bar-btn:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.title-bar-btn.close:hover {
  background-color: #e81123;
  color: #fff;
}
</style>