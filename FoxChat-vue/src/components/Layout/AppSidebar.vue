<template>
  <div class="sidebar">
    <div class="avatar-container" @click="toggleProfile">
      <div class="avatar-wrapper">
        <el-avatar :size="50" :src="resolveAvatarUrl(userInfo.faceImage || userInfo.face_image) || defaultUserAvatar"></el-avatar>
      </div>
      <div class="username">{{ userInfo.nickname || '未设置昵称' }}</div>
    </div>
    <div class="menu-items">
      <div class="menu-item" :class="{ active: !showFriendList && !showGroupList && !showProfile && !showRag && !showMemoryPanel }" @click="closeAllPanels">
        <el-icon><ChatDotRound /></el-icon>
      </div>
      <div class="menu-item" :class="{ active: showFriendList }" @click="togglePanel('friendList')">
        <el-icon><User /></el-icon>
      </div>
      <div class="menu-item" :class="{ active: showGroupList }" @click="togglePanel('groupList')">
        <el-icon><ChatSquare /></el-icon>
      </div>
      <div class="menu-item" :class="{ active: showRag }" @click="toggleRag">
        <el-icon><Reading /></el-icon>
      </div>
      <div class="menu-item" :class="{ active: showLlmConfigPanel }" @click="toggleLlmConfigPanel">
        <el-icon><Setting /></el-icon>
      </div>
      <div class="menu-item" :class="{ active: showMemoryPanel }" @click="toggleMemoryPanel">
        <el-icon><Opportunity /></el-icon>
      </div>
      <div class="menu-item" @click="handleLogout">
        <el-icon><SwitchButton /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ChatDotRound, User, SwitchButton, ChatSquare, Reading, Setting, Opportunity } from '@element-plus/icons-vue';
import { useUserStore } from '@/stores/userStore';
import { useUiStore } from '@/stores/uiStore';
import { useProfile } from '@/composables/useProfile';
import { useRag } from '@/composables/useRag';
import { useChatStore } from '@/stores/chatStore';
import { useWsStore } from '@/stores/wsStore';
import { useRouter } from 'vue-router';
import { resolveAvatarUrl, defaultUserAvatar } from '@/utils/avatar';

const router = useRouter();
const { userInfo } = useUserStore();
const { ws, stopHeartbeat } = useWsStore();
const {
  showFriendList, showGroupList, showProfile, showRag,
  showLlmConfigPanel, showMemoryPanel, preselectedLlmFriendId
} = useUiStore();
const { toggleProfile } = useProfile();
const { fetchRagFiles } = useRag();
const chatStore = useChatStore();

const closeAllPanels = () => {
  showFriendList.value = false;
  showGroupList.value = false;
  showProfile.value = false;
  showRag.value = false;
  showMemoryPanel.value = false;
};

const togglePanel = (panel) => {
  if (panel === 'friendList') {
    showFriendList.value = !showFriendList.value;
    showGroupList.value = false;
    showProfile.value = false;
    showMemoryPanel.value = false;
  } else if (panel === 'groupList') {
    showGroupList.value = !showGroupList.value;
    showFriendList.value = false;
    showProfile.value = false;
    showMemoryPanel.value = false;
  }
};

const toggleRag = () => {
  showRag.value = !showRag.value;
  if (showRag.value) {
    showLlmConfigPanel.value = false;
    showMemoryPanel.value = false;
    chatStore.currentFriend.value = {};
    chatStore.currentGroup.value = {};
    fetchRagFiles();
  }
};

const toggleLlmConfigPanel = () => {
  showLlmConfigPanel.value = !showLlmConfigPanel.value;
  if (showLlmConfigPanel.value) {
    preselectedLlmFriendId.value = null;
    showFriendList.value = false;
    showGroupList.value = false;
    showProfile.value = false;
    showRag.value = false;
    showMemoryPanel.value = false;
  }
};

const toggleMemoryPanel = () => {
  showMemoryPanel.value = !showMemoryPanel.value;
  if (showMemoryPanel.value) {
    showLlmConfigPanel.value = false;
    showFriendList.value = false;
    showGroupList.value = false;
    showProfile.value = false;
  }
};

const handleLogout = () => {
  if (ws.value) {
    try { ws.value.close(); } catch (e) { console.error('Error closing WebSocket:', e); }
  }
  stopHeartbeat();
  localStorage.removeItem('token');
  localStorage.removeItem('userInfo');
  router.push('/login');
};
</script>

<style scoped>
.sidebar {
  width: 60px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.avatar-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
  cursor: pointer;
}

.avatar-wrapper {
  margin-bottom: 4px;
}

.username {
  font-size: 10px;
  color: var(--text-secondary);
  text-align: center;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-items {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-grow: 1;
}

.menu-item {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.menu-item:hover {
  background: var(--accent-hover);
  color: var(--accent-color);
}

.menu-item.active {
  background: var(--accent-active);
  color: var(--accent-color);
}

.menu-item:last-child {
  margin-top: auto;
  color: var(--text-light);
}

.menu-item:last-child:hover {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}
</style>
