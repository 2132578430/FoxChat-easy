<template>
  <!-- Friend List -->
  <transition name="slide-fade">
    <div class="friend-list" v-show="modelValue">
      <div class="search-box">
        <el-input
          placeholder="搜索好友"
          prefix-icon="Search"
          :model-value="searchText"
          @input="handleSearchInput"
        ></el-input>
      </div>
      <div class="friend-group">
        <div class="group-header" style="justify-content: flex-end;">
          <el-tooltip content="添加陪伴者" placement="top">
            <el-button circle size="small" :icon="Plus" @click="emit('add-llm-friend')"></el-button>
          </el-tooltip>
        </div>

        <div v-if="isSearching && searchResultList.length === 0" class="no-result">
          未找到相关用户
        </div>

        <div
          v-for="friend in (isSearching ? searchResultList : [...friendRequests, ...friends])"
          :key="friend.userId || friend.id"
          class="friend-item"
          :class="{
            'active': currentFriendId === (friend.userId || friend.id),
            'request-item': friend.isRequest
          }"
          @click="handleSelectFriend(friend)"
          @contextmenu.prevent="showFriendContextMenu($event, friend)"
        >
          <div class="friend-avatar-wrapper">
            <el-avatar :size="40" :src="resolveAvatarUrl(friend.faceImage || friend.face_image) || defaultUserAvatar"></el-avatar>
            <div v-if="friend.unreadCount > 0" class="unread-badge">{{ friend.unreadCount > 99 ? '99+' : friend.unreadCount }}</div>
          </div>
          <div class="friend-info">
            <div class="friend-name">
              {{ friend.nickname || friend.username }}
              <span v-if="friend.emotion && (friend.role === 1 || friend.isOldFriend)" class="emotion-emoji">{{ emotionToEmoji(friend.emotion) }}</span>
              <span v-if="friend.username && friend.nickname && friend.username !== friend.nickname" class="friend-username">
                ({{ friend.username }})
              </span>
            </div>
            <div class="friend-status" :class="{ 'online': isFriendOnline(friend) }" v-if="friend.role !== 1">
              {{ friend.isRequest ? '新朋友' : ((isSearching && !friend.isFriend) ? '陌生人' : (isFriendOnline(friend) ? '在线' : '离线')) }}
            </div>
          </div>

          <!-- AI Icon & Director Mode Switch -->
          <div v-if="friend.role === 1" class="ai-features">
            <el-tooltip content="导演模式" placement="top">
              <el-switch
                v-model="friend.directorMode"
                size="small"
                @click.stop
                @change="handleDirectorModeChange(friend)"
              />
            </el-tooltip>
            <span class="ai-tag-icon">🦊</span>
          </div>

          <!-- Add Friend Button (Search Mode) -->
          <el-button
            v-if="isSearching && (friend.userId || friend.id) !== userInfo.userId && !friend.isFriend"
            type="primary"
            size="small"
            circle
            :icon="Plus"
            @click.stop="emit('add-friend', friend)"
          ></el-button>

          <!-- Accept Friend Button (Request List) -->
          <el-button
            v-if="friend.isRequest"
            type="success"
            size="small"
            @click.stop="emit('accept-request', friend)"
          >接受</el-button>
        </div>
      </div>
    </div>
  </transition>

  <!-- Friend Context Menu -->
  <div v-if="friendContextMenu.show"
       class="friend-context-menu"
       @mousedown.stop
       :style="{ top: friendContextMenu.y + 'px', left: friendContextMenu.x + 'px' }">
    <div v-if="friendContextMenu.friend?.role === 1" class="context-menu-item" @click="handleEditLlmFriend">
      <el-icon><Edit /></el-icon>
      <span>修改模型</span>
    </div>
    <div class="context-menu-item delete" @click="handleDeleteFriend">
      <el-icon><Delete /></el-icon>
      <span>删除好友</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { Plus, Edit, Delete } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const props = defineProps({
  modelValue: Boolean,
  friends: {
    type: Array,
    default: () => []
  },
  friendRequests: {
    type: Array,
    default: () => []
  },
  searchText: {
    type: String,
    default: ''
  },
  userInfo: {
    type: Object,
    default: () => ({})
  },
  currentFriendId: {
    type: [String, Number],
    default: null
  }
});

const emit = defineEmits([
  'update:modelValue',
  'update:searchText',
  'select-friend',
  'accept-request',
  'add-friend',
  'add-llm-friend',
  'search',
  'context-menu',
  'delete-friend',
  'edit-llm-friend',
  'director-mode-change'
]);

const defaultUserAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png';

// 情绪到emoji的映射
const emotionEmojiMap = {
  '开心': '😊',
  '快乐': '😊',
  'happy': '😊',
  '悲伤': '😢',
  '难过': '😢',
  'sad': '😢',
  '愤怒': '😠',
  '生气': '😠',
  'angry': '😠',
  '惊讶': '😲',
  'surprise': '😲',
  '恐惧': '😨',
  '害怕': '😨',
  'fear': '😨',
  '厌恶': '🤢',
  'disgust': '🤢',
  'neutral': '😐',
  '平静': '😐',
};

const emotionToEmoji = (emotion) => {
  return emotionEmojiMap[emotion] || emotionEmojiMap[emotion?.toLowerCase()] || '😊';
};

const searchResultList = ref([]);
const isSearching = ref(false);

// 好友右键菜单状态
const friendContextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  friend: null
});

const OSS_BASE_URL = import.meta.env.VITE_OSS_BASE_URL || '';

const resolveAvatarUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  const cleanUrl = url.startsWith('/') ? url.substring(1) : url;

  if (cleanUrl.startsWith('oss/')) {
    return `${OSS_BASE_URL.replace('/oss', '')}/${cleanUrl}`;
  }

  return `${OSS_BASE_URL}/${cleanUrl}`;
};

const isFriendOnline = (friend) => {
  return friend.online === true || friend.online === 'true' || friend.online === 1 || friend.online === '1';
};

const handleSearchInput = (value) => {
  emit('update:searchText', value);
  emit('search', value);
};

const handleSelectFriend = (friend) => {
  if (friend.isRequest) return;
  emit('select-friend', friend);
};

const handleDirectorModeChange = (friend) => {
  emit('director-mode-change', friend);
};

const showFriendContextMenu = (event, friend) => {
  if (friend.isRequest) return;

  friendContextMenu.show = true;
  friendContextMenu.x = event.clientX;
  friendContextMenu.y = event.clientY;
  friendContextMenu.friend = friend;
  emit('context-menu', { event, friend, menu: friendContextMenu });
};

const handleEditLlmFriend = () => {
  friendContextMenu.show = false;
  emit('edit-llm-friend', friendContextMenu.friend);
};

const handleDeleteFriend = () => {
  if (!friendContextMenu.friend) return;
  friendContextMenu.show = false;
  emit('delete-friend', friendContextMenu.friend);
};

// 监听点击事件关闭右键菜单
const closeFriendContextMenu = () => {
  friendContextMenu.show = false;
};

// 全局点击关闭右键菜单
const handleGlobalClick = (e) => {
  if (friendContextMenu.show && !e.target.closest('.friend-context-menu')) {
    friendContextMenu.show = false;
  }
};

onMounted(() => {
  document.addEventListener('mousedown', handleGlobalClick);
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleGlobalClick);
});

// 暴露方法给父组件
defineExpose({
  closeFriendContextMenu,
  searchResultList,
  isSearching
});
</script>

<style scoped>
/* Friend List */
.friend-list {
  width: 300px;
  background-color: rgba(255, 255, 255, 0.4);
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(255, 255, 255, 0.3);
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  z-index: 9;
  box-shadow: -4px 0 15px rgba(0,0,0,0.05);
}

.search-box {
  padding: 20px;
  background-color: transparent;
}

.search-box :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.5);
  border-radius: 10px;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.friend-group {
  flex: 1;
  overflow-y: auto;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
}

.group-title {
  color: rgba(0, 0, 0, 0.4);
  font-size: 12px;
  font-weight: 600;
}

.friend-avatar-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.unread-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background-color: #ff4d4f;
  color: white;
  font-size: 10px;
  padding: 0 5px;
  border-radius: 10px;
  min-width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  z-index: 1;
}

.friend-item {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  cursor: pointer;
  border-radius: 8px;
  margin: 0 8px 4px;
}

.friend-item:hover {
  background-color: var(--accent-hover);
}

.friend-item.active {
  background-color: var(--accent-active);
}

.ai-tag-icon {
  font-size: 18px;
  margin-left: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-features {
  display: flex;
  align-items: center;
  gap: 6px;
}

.request-item {
  background-color: rgba(240, 249, 235, 0.6);
}

.request-item:hover {
  background-color: rgba(225, 243, 216, 0.8);
}

.friend-info {
  margin-left: 10px;
  flex: 1;
}

.friend-name {
  font-size: 14px;
  color: #000000;
  display: flex;
  align-items: center;
  gap: 5px;
}

.emotion-emoji {
  font-size: 14px;
  margin-left: 4px;
}

.friend-username {
  font-size: 12px;
  color: #999;
  margin-left: 5px;
  font-weight: normal;
}

.friend-status {
  font-size: 12px;
  color: #999;
}

.friend-status.online {
  color: #67c23a;
}

/* 好友右键菜单样式 */
.friend-context-menu {
  position: fixed;
  z-index: 10000;
  background: #ffffff;
  border-radius: 4px;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.15);
  padding: 0;
  min-width: 90px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  overflow: hidden;
}

.friend-context-menu .context-menu-item {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
  box-sizing: border-box;
  width: 100%;
}

.friend-context-menu .context-menu-item .el-icon {
  margin-right: 6px;
  font-size: 14px;
}

.friend-context-menu .context-menu-item:hover {
  background-color: #f5f5f5;
}

.friend-context-menu .context-menu-item.delete {
  color: #ff4d4f;
}

.friend-context-menu .context-menu-item.delete:hover {
  background-color: #fff1f0;
  color: #ff4d4f;
}

/* Transition styles */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.3s ease-in;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
