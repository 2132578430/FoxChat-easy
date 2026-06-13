<template>
  <div class="home-container theme-qq">
    <!-- Sidebar -->
    <AppSidebar />

    <!-- Chat Area -->
    <div class="chat-area" :class="{ 'shrink-right': showFriendList || showGroupList || showProfile || showMemoryPanel }">
      <!-- LLM Config Panel -->
      <LlmConfigPanel
        v-if="showLlmConfigPanel"
        :friend-list="llmFriendList"
        :preselected-friend-id="preselectedLlmFriendId"
        :pending-llm-avatar-url="pendingLlmAvatarUrl"
        @close="showLlmConfigPanel = false"
        @open-avatar-cropper="handleOpenLlmAvatarCropper"
      />

      <!-- Normal Chat Interface -->
      <template v-else>
        <div class="chat-header">
          <span class="chat-title" v-if="showRag">狐狸RAG</span>
          <span class="chat-title" v-else-if="currentChatType === 'group'">{{ currentGroup.groupName || currentGroup.name || '群聊' }}</span>
          <span class="chat-title" v-else>
            {{ currentFriend.nickname || currentFriend.username || '选择好友开始聊天' }}
            <span v-if="currentFriend.emotion && (currentFriend.role === 1 || currentFriend.isOldFriend)" class="emotion-emoji">{{ emotionToEmoji(currentFriend.emotion) }}</span>
            <span v-if="isLlmTyping && (currentFriend.role === 1 || currentFriend.isOldFriend)" class="typing-indicator">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </span>
          </span>
          <!-- 仅私聊显示多选操作 -->
          <div class="chat-actions" v-if="!showRag && currentChatType === 'private' && (currentFriend.userId || currentFriend.id)">
            <transition name="fade-scale" mode="out-in">
              <div v-if="!isSelectionMode" key="normal">
                <el-tooltip content="多选消息" placement="bottom">
                  <el-button circle class="action-btn" @click="toggleSelectionMode">
                    <el-icon><Select /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
              <div class="selection-actions" v-else key="selection">
                <el-button round size="small" @click="cancelSelectionMode">取消</el-button>
                <el-button type="danger" round size="small" @click="handleDeleteMessages" :disabled="selectedMessageIds.length === 0" class="withdraw-btn delete-btn">
                  删除 ({{ selectedMessageIds.length }})
                </el-button>
                <el-button type="warning" round size="small" @click="handleWithdrawMessages" :disabled="selectedMessageIds.length === 0" class="withdraw-btn">
                  撤回 ({{ selectedMessageIds.length }})
                </el-button>
              </div>
            </transition>
          </div>
        </div>

        <!-- Message List -->
        <MessageList
          ref="messageListRef"
          :messages="messageList"
          :current-friend="currentFriend"
          :current-group="currentGroup"
          :current-chat-type="currentChatType"
          :user-info="userInfo"
          :is-selection-mode="isSelectionMode"
          :selected-message-ids="selectedMessageIds"
          :show-rag="showRag"
          :rag-files="ragFiles"
          :has-rag-search-results="hasRagSearchResults"
          @load-more="loadMoreHistory"
          @scroll-bottom="scrollToBottom"
          @open-upload="showUploadDialog = true"
          @reset-rag="resetRagResults"
          @file-click="handleFileClick"
          @retry="retryLlmMessage"
        />

        <!-- Chat Input -->
        <ChatInput
          v-model="inputMessage"
          :show-rag="showRag"
          :is-searching-rag="isSearchingRag"
          @send="sendMessage"
          @open-upload="showUploadDialog = true"
        />
      </template>
    </div>

    <!-- Profile Panel -->
    <ProfilePanel />

    <!-- Group List -->
    <GroupList
      ref="groupListRef"
      v-model="showGroupList"
      :groups="groupList"
      :current-group-id="currentGroup.id"
      :user-info="userInfo"
      :is-group-loading="isGroupLoading"
      @select-group="handleGroupClick"
      @join-group="handleJoinGroup"
      @create-group="showCreateGroupDialog = true"
      @search="(text) => handleGroupSearch(text, groupListRef)"
    />

    <!-- Friend List -->
    <FriendList
      ref="friendListRef"
      v-model="showFriendList"
      v-model:search-text="searchText"
      :friends="friendList"
      :friend-requests="friendRequestList"
      :user-info="userInfo"
      :current-friend-id="currentFriend.userId || currentFriend.id"
      @select-friend="selectFriend"
      @accept-request="handleAcceptFriend"
      @add-friend="handleAddFriend"
      @add-llm-friend="showAddLlmFriendDialog = true"
      @delete-friend="handleDeleteFriend"
      @edit-llm-friend="handleEditLlmFriend"
      @search="(text) => handleFriendSearch(text, friendListRef)"
    />

    <!-- Dialogs -->
    <CreateGroupDialog />
    <AddLlmFriendDialog />
    <UploadDialog />

    <!-- Model Memory Panel -->
    <ModelMemoryPanel
      v-model="showMemoryPanel"
      :llm-id="currentFriend.role === 1 ? currentFriend.userId || currentFriend.id : null"
    />

    <!-- Avatar Cropper -->
    <AvatarCropper
      v-model:visible="showAvatarCropper"
      :type="isAvatarCropperForLlm ? 'llm' : 'user'"
      @success="handleAvatarSuccess"
      @blob="handleAvatarBlob"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { Select } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

// Stores
import { useUserStore } from '@/stores/userStore';
import { useChatStore } from '@/stores/chatStore';
import { useFriendStore } from '@/stores/friendStore';
import { useGroupStore } from '@/stores/groupStore';
import { useWsStore } from '@/stores/wsStore';
import { useUiStore } from '@/stores/uiStore';

// Composables
import { useWsConnection } from '@/composables/useWsConnection';
import { useFriends } from '@/composables/useFriends';
import { useGroups } from '@/composables/useGroups';
import { useChat } from '@/composables/useChat';
import { useRag } from '@/composables/useRag';
import { useProfile } from '@/composables/useProfile';

// Utils
import { emotionToEmoji } from '@/utils/avatar';

// Components
import AppSidebar from '@/components/Layout/AppSidebar.vue';
import ProfilePanel from '@/components/Profile/ProfilePanel.vue';
import CreateGroupDialog from '@/components/Groups/CreateGroupDialog.vue';
import AddLlmFriendDialog from '@/components/Groups/AddLlmFriendDialog.vue';
import UploadDialog from '@/components/dialogs/UploadDialog.vue';
import MessageList from '@/components/Chat/MessageList.vue';
import ChatInput from '@/components/Chat/ChatInput.vue';
import FriendList from '@/components/Chat/FriendList.vue';
import GroupList from '@/components/Chat/GroupList.vue';
import ModelMemoryPanel from '@/components/Chat/ModelMemoryPanel.vue';
import LlmConfigPanel from '@/components/LlmConfig/LlmConfigPanel.vue';
import AvatarCropper from '@/components/AvatarCropper.vue';

const router = useRouter();

// Stores
const { userInfo } = useUserStore();
const chatStore = useChatStore();
const friendStore = useFriendStore();
const groupStore = useGroupStore();
const { ws, stopHeartbeat } = useWsStore();
const uiStore = useUiStore();

// Destructure for template auto-unwrap
const { currentFriend, currentGroup, currentChatType, messageList, inputMessage, isSelectionMode, selectedMessageIds, isLlmTyping } = chatStore;
const { friendList, friendRequestList, llmFriendList } = friendStore;
const { groupList, isGroupLoading } = groupStore;
const { showFriendList, showGroupList, showProfile, showRag, showLlmConfigPanel, showMemoryPanel, showCreateGroupDialog, showAddLlmFriendDialog, showUploadDialog, showAvatarCropper, preselectedLlmFriendId, pendingLlmAvatarUrl, isAvatarCropperForLlm, searchText } = uiStore;

// Composables
const { initWebSocket } = useWsConnection();
const { getFriendList, getFriendRequests, handleFriendSearch, handleAddFriend, handleAcceptFriend, handleDeleteFriend, handleEditLlmFriend, selectFriend } = useFriends();
const { isGroupLoading: _igl, getGroupList, handleGroupSearch, handleCreateGroup, handleAddLlmFriend, handleJoinGroup, handleGroupClick } = useGroups();
const { sendMessage, retryLlmMessage, loadMoreHistory, scrollToBottom, handleWithdrawMessages, handleDeleteMessages, toggleSelectionMode, cancelSelectionMode } = useChat();
const { ragFiles, hasRagSearchResults, isSearchingRag, resetRagResults, handleFileClick } = useRag();
const { handleOpenLlmAvatarCropper, handleAvatarSuccess, handleAvatarBlob } = useProfile();

// Refs for child components
const messageListRef = ref(null);
const friendListRef = ref(null);
const groupListRef = ref(null);

// Lifecycle
onMounted(() => {
  if (!userInfo.username) {
    router.push('/login');
    return;
  }
  getFriendList();
  getFriendRequests();
  initWebSocket();
});

onUnmounted(() => {
  if (ws.value) {
    try { ws.value.close(); } catch (e) { console.error('Error closing WebSocket on unmount:', e); }
  }
  stopHeartbeat();
});
</script>

<style scoped>
/* ============================================
   Global Layout & Theme Variables
   ============================================ */
.home-container {
  --bg-gradient: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  --sidebar-bg: rgba(255, 255, 255, 0.2);
  --sidebar-border: rgba(255, 255, 255, 0.3);
  --text-primary: #333;
  --text-secondary: #666;
  --text-light: #999;
  --accent-color: #0084ff;
  --accent-hover: rgba(0, 132, 255, 0.2);
  --accent-active: rgba(0, 132, 255, 0.1);
  --button-bg: #0084ff;
  --button-text: #fff;
  --button-hover: #0066cc;
  --border-strong: rgba(255, 255, 255, 0.5);
}

.home-container.theme-qq {
  --chat-bg: rgba(255, 255, 255, 0.6);
  --chat-header-bg: rgba(255, 255, 255, 0.3);
  --chat-header-border: rgba(255, 255, 255, 0.3);
  --message-bg-mine: #0084ff;
  --message-text-mine: #fff;
  --message-bg-other: rgba(255, 255, 255, 0.8);
  --message-text-other: #333;
  --panel-bg: rgba(255, 255, 255, 0.4);
  --input-bg: rgba(255, 255, 255, 0.3);
  --input-border: rgba(255, 255, 255, 0.3);
  --input-inner-bg: rgba(255, 255, 255, 0.5);
  --badge-bg: #ff4d4f;
  --menu-icon-color: #666;
  --menu-icon-active: #0084ff;

  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--bg-gradient);
  overflow: hidden;
  transition: background 0.5s ease;
  position: relative;
}

/* ============================================
   Chat Area Layout
   ============================================ */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--chat-bg);
  position: relative;
  min-width: 0;
}

.chat-area.shrink-right {
  flex: 1;
}

.chat-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--chat-header-border);
  background: var(--chat-header-bg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.chat-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.emotion-emoji {
  margin-left: 4px;
  font-size: 14px;
}

.typing-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  gap: 2px;
}

.typing-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--accent-color);
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.chat-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selection-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  border: none;
  background: transparent;
}

.withdraw-btn { font-size: 12px; }
.delete-btn { font-size: 12px; }

/* ============================================
   Upload Dialog Styles
   ============================================ */
.upload-dialog-content {
  padding: 10px 0;
}

.fox-uploader :deep(.el-upload-dragger) {
  border-radius: 16px;
  border: 2px dashed var(--sidebar-border);
  background: rgba(255, 255, 255, 0.4);
  transition: all 0.3s ease;
}

.fox-uploader :deep(.el-upload-dragger):hover {
  border-color: var(--accent-color);
  background: var(--accent-active);
}

.fox-uploader .el-icon--upload {
  font-size: 60px;
  color: var(--accent-color);
  margin-bottom: 10px;
}

.fox-uploader .el-upload__text em {
  color: var(--accent-color);
  font-style: normal;
  font-weight: bold;
}

.fox-uploader .el-upload__tip {
  text-align: center;
  margin-top: 15px;
  color: var(--text-light);
}

/* ============================================
   Transitions
   ============================================ */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  transform: translateX(20px);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}

.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.2s ease;
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>
