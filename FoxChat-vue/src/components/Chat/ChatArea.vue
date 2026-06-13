<template>
  <div class="chat-area-inner">
    <div class="chat-header">
      <span class="chat-title" v-if="showRag">狐狸RAG</span>
      <span class="chat-title" v-else-if="chatStore.currentChatType.value === 'group'">{{ chatStore.currentGroup.value.groupName || chatStore.currentGroup.value.name || '群聊' }}</span>
      <span class="chat-title" v-else>
        {{ chatStore.currentFriend.value.nickname || chatStore.currentFriend.value.username || '选择好友开始聊天' }}
        <span v-if="chatStore.currentFriend.value.emotion && (chatStore.currentFriend.value.role === 1 || chatStore.currentFriend.value.isOldFriend)" class="emotion-emoji">{{ emotionToEmoji(chatStore.currentFriend.value.emotion) }}</span>
        <span v-if="chatStore.isLlmTyping.value && (chatStore.currentFriend.value.role === 1 || chatStore.currentFriend.value.isOldFriend)" class="typing-indicator">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </span>
      </span>
      <!-- 仅私聊显示多选操作 -->
      <div class="chat-actions" v-if="!showRag && chatStore.currentChatType.value === 'private' && (chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id)">
        <transition name="fade-scale" mode="out-in">
          <div v-if="!chatStore.isSelectionMode.value" key="normal">
            <el-tooltip content="多选消息" placement="bottom">
              <el-button circle class="action-btn" @click="toggleSelectionMode">
                <el-icon><Select /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
          <div class="selection-actions" v-else key="selection">
            <el-button round size="small" @click="cancelSelectionMode">取消</el-button>
            <el-button 
              type="danger" 
              round 
              size="small" 
              @click="handleDeleteMessages" 
              :disabled="chatStore.selectedMessageIds.value.length === 0"
              class="withdraw-btn delete-btn"
            >
              删除 ({{ chatStore.selectedMessageIds.value.length }})
            </el-button>
            <el-button 
              type="warning" 
              round 
              size="small" 
              @click="handleWithdrawMessages" 
              :disabled="chatStore.selectedMessageIds.value.length === 0"
              class="withdraw-btn"
            >
              撤回 ({{ chatStore.selectedMessageIds.value.length }})
            </el-button>
          </div>
        </transition>
      </div>
    </div>

    <!-- Message List -->
    <MessageList
      ref="messageListRef"
      :messages="chatStore.messageList.value"
      :current-friend="chatStore.currentFriend.value"
      :current-group="chatStore.currentGroup.value"
      :current-chat-type="chatStore.currentChatType.value"
      :user-info="userInfo"
      :is-selection-mode="chatStore.isSelectionMode.value"
      :selected-message-ids="chatStore.selectedMessageIds.value"
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
      v-model="chatStore.inputMessage.value"
      :show-rag="showRag"
      :is-searching-rag="isSearchingRag"
      @send="sendMessage"
      @open-upload="showUploadDialog = true"
    />
  </div>
</template>

<script setup>
import { Select } from '@element-plus/icons-vue';
import { useChatStore } from '@/stores/chatStore';
import { useUserStore } from '@/stores/userStore';
import { useUiStore } from '@/stores/uiStore';
import { useChat } from '@/composables/useChat';
import { useRag } from '@/composables/useRag';
import { emotionToEmoji } from '@/utils/avatar';
import MessageList from '@/components/Chat/MessageList.vue';
import ChatInput from '@/components/Chat/ChatInput.vue';

const chatStore = useChatStore();
const { userInfo } = useUserStore();
const { showRag, showUploadDialog } = useUiStore();
const { ragFiles, hasRagSearchResults, isSearchingRag, resetRagResults, handleFileClick } = useRag();
const {
  sendMessage, retryLlmMessage, loadMoreHistory, scrollToBottom,
  handleWithdrawMessages, handleDeleteMessages,
  toggleSelectionMode, cancelSelectionMode
} = useChat();
</script>

<style scoped>
.chat-area-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--sidebar-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--sidebar-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
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

.withdraw-btn {
  font-size: 12px;
}

.delete-btn {
  font-size: 12px;
}
</style>
