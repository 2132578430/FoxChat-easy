<template>
  <div class="chat-messages" ref="messageContainerRef" @scroll="handleScroll">
    <!-- RAG 界面 -->
    <div v-if="props.showRag" class="rag-container">
      <!-- 文件列表视图 -->
      <div v-if="props.ragFiles && props.ragFiles.length > 0" class="rag-files-list">
        <div class="rag-list-header">
          <div class="header-left">
            <h3><el-icon><Files /></el-icon> {{ props.hasRagSearchResults ? '搜索结果' : '已上传知识库文件' }}</h3>
            <el-tag type="primary" round size="small" effect="plain">{{ props.ragFiles.length }} 个文件</el-tag>
          </div>
          <el-button v-if="props.hasRagSearchResults" type="info" size="small" plain round @click="emit('reset-rag')">
            返回列表
          </el-button>
        </div>
        <div class="rag-files-grid">
          <div v-for="(file, index) in props.ragFiles"
               :key="file.id || index"
               class="rag-file-card"
               :class="{ 'clickable': !!file.filePath }"
               @click="emit('file-click', file)">
            <div class="file-icon-wrapper">
              <el-icon><Document /></el-icon>
            </div>
            <div class="file-info">
              <span class="file-name" :title="file.fileName">{{ file.fileName }}</span>
              <div class="file-meta">
                <span class="file-time">{{ formatDateOnly(file.createTime) }}</span>
                <div class="file-tags">
                  <el-tag v-if="file.score !== undefined && file.score !== null" :type="getScoreTagType(file.score)" size="small" effect="plain" class="score-tag">
                    {{ getScoreLabel(file.score) }} {{ file.score.toFixed(2) }}
                  </el-tag>
                  <el-tag v-if="file.status !== undefined" :type="getFileStatusType(file.status)" size="small" effect="dark" class="status-tag">
                    {{ getFileStatusLabel(file.status) }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- 默认/空状态视图 -->
      <div v-else class="rag-welcome">
        <div class="rag-card">
          <div class="rag-logo-wrapper">
            <el-icon class="rag-logo"><Reading /></el-icon>
          </div>
          <h2>狐狸RAG 知识库</h2>
          <p>上传您的文档，让我为您提供智能知识服务吧~</p>
          <div class="rag-tips">
            <span>支持 PDF, TXT 等格式</span>
            <span>单文件最大 100MB</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else v-for="(msg, index) in props.messages" :key="msg.id || index" class="message-wrapper">
      <!-- 撤回消息的显示 -->
      <div v-if="msg.isWithdrawn" class="message-system">
        <span class="system-text">"{{ msg.isMine ? '你' : (props.currentFriend.nickname || props.currentFriend.username) }}" 撤回了一条消息</span>
      </div>
      <!-- 失败消息（可重试） -->
      <div v-else-if="msg.status === 'failed'" class="message-item-container">
        <div class="message-item">
          <el-avatar :size="38" :src="resolveAvatarUrl(props.currentFriend.faceImage || props.currentFriend.face_image) || defaultUserAvatar" class="msg-avatar"></el-avatar>
          <div class="msg-bubble-wrapper">
            <div class="msg-bubble failed-bubble">
              <div class="bubble-content failed-content">
                <span class="failed-text">回复失败，</span>
                <span class="retry-link" @click="emit('retry', msg)">点击重试</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 正常消息 -->
      <div v-else class="message-item-container" :class="{ 'selection-mode': props.isSelectionMode }">
        <el-checkbox v-if="props.isSelectionMode && msg.isMine" v-model="msg.selected" @change="handleSelectionChange(msg)"></el-checkbox>
        <div class="message-item" :class="{ 'mine': msg.isMine }">
          <el-avatar :size="38" :src="resolveAvatarUrl(msg.isMine ? (props.userInfo.faceImage || props.userInfo.face_image) : (msg.senderAvatar || props.currentFriend.faceImage || props.currentFriend.face_image)) || defaultUserAvatar" class="msg-avatar"></el-avatar>

          <div class="msg-bubble-wrapper">
            <!-- 外部顶部：时间 -->
            <div class="bubble-external-time">
              {{ formatTime(msg.createTime) }}
              <span v-if="msg.emotion && !msg.isMine" class="emotion-emoji">{{ emotionToEmoji(msg.emotion) }}</span>
            </div>

            <!-- 普通文本消息 -->
            <div v-if="!msg.blocks" class="msg-bubble">
              <div class="bubble-content">{{ msg.content || msg.msg }}</div>
            </div>

            <!-- 结构化消息块（AI回复） -->
            <template v-else v-for="(block, blockIndex) in msg.blocks" :key="blockIndex">
              <!-- 动作标签 -->
              <div v-if="block.type === 'action' || block.type === 'action_text'" class="action-tag">
                ○ {{ block.action }}
              </div>
              <!-- 文字内容 -->
              <div v-if="(block.type === 'text' || block.type === 'action_text') && block.text" class="msg-bubble">
                <div class="bubble-content">{{ block.text }}</div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { Files, Document, Reading } from '@element-plus/icons-vue';
import { OSS_BASE_URL } from '@/utils/config';

const props = defineProps({
  messages: Array,
  currentFriend: Object,
  currentGroup: Object,
  currentChatType: String,
  userInfo: Object,
  isSelectionMode: Boolean,
  selectedMessageIds: Array,
  showRag: Boolean,
  ragFiles: Array,
  hasRagSearchResults: Boolean
});

const emit = defineEmits(['select-message', 'load-more', 'scroll-bottom', 'open-upload', 'reset-rag', 'file-click', 'retry']);

const messageContainerRef = ref(null);
const defaultUserAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png';
const isUserScrolling = ref(false);

const emotionEmojiMap = {
  '开心': '😊',
  '快乐': '😊',
  'happy': '😊',
  '悲伤': '😢',
  '难过': '😢',
  'sad': '😢',
  '愤怒': '😠',
  '生气': '😠',
  'anger': '😠',
  'angry': '😠',
  '惊讶': '😲',
  'surprise': '😲',
  'surprised': '😲',
  '恐惧': '😨',
  '害怕': '😨',
  'fear': '😨',
  'fearful': '😨',
  '厌恶': '🤢',
  'disgust': '🤢',
  'disgusted': '🤢',
  'neutral': '😐',
  '平静': '😐'
};

const emotionToEmoji = (emotion) => {
  return emotionEmojiMap[emotion] || emotionEmojiMap[emotion?.toLowerCase()] || '😊';
};
let scrollTimeout = null;

// 辅助函数：处理头像URL
const resolveAvatarUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  const cleanUrl = url.startsWith('/') ? url.substring(1) : url;

  if (cleanUrl.startsWith('oss/')) {
     return `${OSS_BASE_URL.replace('/oss', '')}/${cleanUrl}`;
  }

  return `${OSS_BASE_URL}/${cleanUrl}`;
};

const handleScroll = (e) => {
  const container = e.target;
  
  // 清除之前的超时
  if (scrollTimeout) {
    clearTimeout(scrollTimeout);
  }
  
  // 用户在滚动，设置标志
  isUserScrolling.value = true;
  
  // 滚动停止后 500ms 清除标志（给用户足够时间停止滚动）
  scrollTimeout = setTimeout(() => {
    isUserScrolling.value = false;
  }, 500);

  // 当滚动到顶部（scrollTop 为 0）时，加载更多历史消息
  if (container.scrollTop === 0) {
    emit('load-more');
  }
};

const handleSelectionChange = (msg) => {
  emit('select-message', msg);
};

const formatTime = (timeValue) => {
  if (!timeValue) return '';
  try {
    let date;
    if (!isNaN(timeValue) && typeof timeValue !== 'boolean') {
      date = new Date(Number(timeValue));
    } else {
      date = new Date(timeValue);
    }

    if (isNaN(date.getTime())) return String(timeValue);

    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } else {
      return `${date.getMonth() + 1}-${date.getDate()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}`;
    }
  } catch (e) {
    return String(timeValue);
  }
};

// 专门用于 RAG 列表的日期格式化（仅显示年月日）
const formatDateOnly = (timeValue) => {
  if (!timeValue) return '';
  try {
    let date;
    if (!isNaN(timeValue) && typeof timeValue !== 'boolean') {
      date = new Date(Number(timeValue));
    } else {
      date = new Date(timeValue);
    }
    if (isNaN(date.getTime())) return '';

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  } catch (e) {
    return '';
  }
};

// 获取文件状态文本
const getFileStatusLabel = (status) => {
  const statusMap = {
    0: '已创建',
    1: '存入数据库',
    2: '读入RAG'
  };
  return statusMap[status] || '未知状态';
};

// 获取文件状态对应的标签类型
const getFileStatusType = (status) => {
  const typeMap = {
    0: 'info',
    1: 'warning',
    2: 'success'
  };
  return typeMap[status] || 'info';
};

// 获取匹配度标签类型（适配余弦距离：分数越低越相似）
const getScoreTagType = (score) => {
  if (score <= 1.25) return 'success';
  if (score <= 1.45) return 'warning';
  return 'danger';
};

// 获取匹配度文字
const getScoreLabel = (score) => {
  if (score <= 1.25) return '强相关';
  if (score <= 1.45) return '中等相关';
  return '弱相关';
};

// 暴露方法给父组件
defineExpose({
  scrollToBottom: (force = false) => {
    if (messageContainerRef.value) {
      // 如果用户正在滚动且不是强制滚动，则不自动滚动
      if (isUserScrolling.value && !force) {
        return;
      }
      messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight;
    }
  },
  isUserScrolling: isUserScrolling
});
</script>

<style scoped>
.chat-messages {
  flex: 1;
  min-height: 0;
  padding: 15px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.message-item-container {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
}

.message-item-container.selection-mode {
  padding-left: 10px;
}

/* System Message (Withdraw) */
.message-system {
  display: flex;
  justify-content: center;
  margin: 10px 0;
}

.system-text {
  font-size: 12px;
  color: #999;
  background-color: rgba(220, 220, 220, 0.3);
  padding: 4px 12px;
  border-radius: 12px;
}

.message-item {
  display: flex;
  gap: 8px;
  max-width: 70%;
  align-self: flex-start;
}

.message-item.mine {
  align-self: flex-end;
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.message-item-container:has(.message-item.mine) {
  flex-direction: row-reverse;
}

.message-item-container {
  flex-direction: row;
}

.message-item-container .el-checkbox {
  margin-right: 10px;
}

.message-item-container:has(.message-item.mine) .message-item {
  margin-left: auto;
}

/* 消息入场动画 */
@keyframes message-rise-up {
  0% {
    opacity: 0;
    transform: translateY(25px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.message-item-container {
  animation: message-rise-up 0.35s ease-out forwards;
}

.msg-avatar {
  flex-shrink: 0;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.msg-bubble-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 100%;
}

.message-item.mine .msg-bubble-wrapper {
  align-items: flex-end;
}

.message-item:not(.mine) .msg-bubble-wrapper {
  align-items: flex-start;
}

.bubble-external-time {
  font-size: 11px;
  color: #000;
  margin-bottom: 4px;
  padding: 0 4px;
}

.emotion-emoji {
  margin-left: 4px;
  font-size: 14px;
}

/* 新的气泡样式 */
.msg-bubble {
  background-color: rgba(60, 60, 60, 0.9);
  padding: 8px 14px;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
  min-width: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

.message-item.mine .msg-bubble {
  background-color: rgba(100, 100, 100, 0.9);
  border-top-right-radius: 4px;
}

.message-item:not(.mine) .msg-bubble {
  border-top-left-radius: 4px;
}

.action-tag {
  font-size: 12px;
  color: #999;
  font-style: italic;
  margin-bottom: 4px;
  padding: 0 4px;
}

.bubble-content {
  font-size: 14px;
  color: #ffffff;
  line-height: 1.6;
  word-break: break-all;
  text-align: left;
}

/* RAG Styles */
.rag-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.rag-files-list {
  padding: 30px;
  height: 100%;
  overflow-y: auto;
}

.rag-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rag-files-grid {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.rag-files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

.rag-file-card {
  background: rgba(255, 255, 255, 0.7);
  padding: 18px;
  border-radius: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 15px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  cursor: default;
}

.rag-file-card.clickable {
  cursor: pointer;
}

.rag-file-card.clickable:hover {
  transform: translateX(5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  background: #fff;
}

.file-icon-wrapper {
  width: 44px;
  height: 44px;
  background: var(--button-bg);
  border-radius: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 20px;
  opacity: 0.9;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  text-align: left;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  display: block;
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  font-weight: 600;
}

.file-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.file-tags {
  display: flex;
  gap: 5px;
  align-items: center;
}

.score-tag {
  font-size: 10px;
  height: 18px;
  padding: 0 4px;
  border-radius: 4px;
}

.file-time {
  font-size: 12px;
  color: #999;
}

.status-tag {
  font-size: 10px;
  height: 18px;
  padding: 0 6px;
  border-radius: 4px;
}

.rag-welcome {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 20px;
}

.rag-card {
  background: rgba(255, 255, 255, 0.6);
  padding: 40px;
  border-radius: 20px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  max-width: 400px;
  width: 100%;
}

.rag-logo-wrapper {
  width: 80px;
  height: 80px;
  background: var(--button-bg);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 auto 20px;
  box-shadow: 0 4px 12px var(--accent-hover);
}

.rag-logo {
  font-size: 40px;
  color: #fff;
}

.rag-card h2 {
  margin: 0 0 10px;
  color: var(--text-primary);
}

.rag-card p {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.rag-tips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--text-light);
}

/* Failed retry bubble */
.failed-bubble {
  background: rgba(245, 108, 108, 0.08) !important;
  border: 1px solid rgba(245, 108, 108, 0.2) !important;
}

.failed-content {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #909399;
  font-size: 13px;
}

.failed-text {
  color: #909399;
}

.retry-link {
  color: #0084ff;
  cursor: pointer;
  text-decoration: underline;
  font-weight: 500;
  transition: color 0.2s;
}

.retry-link:hover {
  color: #0066cc;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

::-webkit-scrollbar-track {
  background: transparent;
}
</style>
