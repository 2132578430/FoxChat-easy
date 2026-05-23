<template>
  <transition name="slide-fade">
    <div class="group-list" v-show="modelValue">
      <div class="search-box">
        <el-input
          placeholder="搜索狐狸窝"
          prefix-icon="Search"
          :model-value="searchText"
          @input="handleSearchInput"
        ></el-input>
      </div>
      <div class="friend-group">
        <div class="group-header" style="justify-content: flex-end;">
          <el-tooltip content="新建狐狸窝" placement="top">
            <el-button circle size="small" :icon="Plus" @click="emit('create-group')"></el-button>
          </el-tooltip>
        </div>

        <div class="no-result" v-if="groups.length === 0 && !isGroupLoading && !isSearching">
          这里空空如也，快去创建一个吧～
        </div>

        <!-- 搜索模式 -->
        <div v-if="isSearching">
          <div v-if="searchResultList.length === 0" class="no-result">
            未找到相关群组
          </div>
          <div
            v-for="group in searchResultList"
            :key="group.id"
            class="friend-item"
            @click="handleGroupClick(group)"
          >
            <div class="friend-avatar-wrapper">
              <el-avatar :size="40" :src="resolveAvatarUrl(group.faceImage || group.avatar) || defaultGroupAvatar"></el-avatar>
            </div>
            <div class="friend-info">
              <div class="friend-name">{{ group.groupName }}</div>
              <div class="friend-status" v-if="!group.isJoined">未加入</div>
            </div>
            <el-button
              v-if="!group.isJoined"
              type="primary"
              size="small"
              circle
              :icon="Plus"
              :loading="group.isJoining"
              @click.stop="emit('join-group', group)"
            ></el-button>
          </div>
        </div>

        <!-- 正常列表模式 -->
        <div v-else>
          <div
            v-for="group in groups"
            :key="group.id"
            class="friend-item"
            :class="{ 'active': currentGroupId === group.id }"
            @click="handleGroupClick(group)"
          >
            <div class="friend-avatar-wrapper">
              <el-avatar :size="40" :src="resolveAvatarUrl(group.faceImage || group.avatar) || defaultGroupAvatar"></el-avatar>
              <div v-if="group.unreadCount > 0" class="unread-badge">{{ group.unreadCount > 99 ? '99+' : group.unreadCount }}</div>
            </div>
            <div class="friend-info">
              <div class="friend-name">{{ group.groupName }}</div>
            </div>
            <el-tooltip content="我是群主" placement="top" v-if="String(group.ownerUserId) === String(userInfo.userId)">
              <div class="owner-badge">🦊</div>
            </el-tooltip>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref } from 'vue';
import { Plus } from '@element-plus/icons-vue';

const props = defineProps({
  modelValue: Boolean,
  groups: {
    type: Array,
    default: () => []
  },
  currentGroupId: {
    type: [String, Number],
    default: null
  },
  userInfo: {
    type: Object,
    default: () => ({})
  },
  isGroupLoading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits([
  'update:modelValue',
  'select-group',
  'join-group',
  'create-group',
  'search'
]);

const defaultGroupAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png';

const searchText = ref('');
const searchResultList = ref([]);
const isSearching = ref(false);

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

const handleSearchInput = (value) => {
  searchText.value = value;
  emit('search', value);
};

const handleGroupClick = (group) => {
  emit('select-group', group);
};

defineExpose({
  searchResultList,
  isSearching
});
</script>

<style scoped>
.group-list {
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

.friend-info {
  margin-left: 10px;
  flex: 1;
}

.friend-name {
  font-size: 14px;
  color: #000000;
}

.friend-status {
  font-size: 12px;
  color: #999;
}

.owner-badge {
  font-size: 16px;
  margin-left: 8px;
}

.no-result {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 20px;
}

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
