<template>
  <transition name="slide-fade">
    <div class="profile-detail" v-show="showProfile">
      <div class="profile-header">
        <h3>个人信息</h3>
      </div>
      <div class="profile-content">
        <div class="profile-avatar-section">
          <FoxAvatar :src="resolveAvatarUrl(profileInfo.faceImage) || defaultUserAvatar" :size="100" />
          <FoxButton size="small" type="ghost" @click="handleEditAvatar">修改头像</FoxButton>
        </div>

        <div class="info-list">
          <div class="info-item">
            <label>昵称</label>
            <FoxInput v-model="profileInfo.nickname" placeholder="请输入昵称" />
          </div>
          <div class="info-item">
            <label>邮箱</label>
            <FoxInput v-model="profileInfo.email" placeholder="请输入邮箱" />
          </div>
        </div>

        <div class="profile-actions">
          <FoxButton type="primary" block @click="handleUpdateProfile">修改信息</FoxButton>
          <FoxButton type="ghost" block @click="handleEditPassword">修改密码</FoxButton>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { FoxAvatar, FoxButton, FoxInput } from '@/components/FoxUI';
import { useUserStore } from '@/stores/userStore';
import { useUiStore } from '@/stores/uiStore';
import { useProfile } from '@/composables/useProfile';
import { resolveAvatarUrl, defaultUserAvatar } from '@/utils/avatar';

const { profileInfo, handleUpdateProfile, handleEditPassword } = useUserStore();
const { showProfile } = useUiStore();
const { handleEditAvatar } = useProfile();
</script>

<style scoped>
.profile-detail {
  width: 300px;
  background: var(--sidebar-bg);
  border-left: 1px solid var(--sidebar-border);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  display: flex;
  flex-direction: column;
}
.profile-header { padding: 16px; border-bottom: 1px solid var(--sidebar-border); }
.profile-header h3 { margin: 0; font-size: 16px; color: var(--text-primary); }
.profile-content { padding: 16px; display: flex; flex-direction: column; gap: 16px; }
.profile-avatar-section { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.info-list { display: flex; flex-direction: column; gap: 12px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-item label { font-size: 12px; color: var(--text-secondary); }
.profile-actions { display: flex; flex-direction: column; gap: 8px; }
</style>
