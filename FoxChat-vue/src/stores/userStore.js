import { reactive, ref } from 'vue';
import * as userApi from '@/api/user';
import { FoxToast } from '@/components/FoxUI';

// 用户信息（从 localStorage 恢复，reactive 保证多组件共享同一引用）
const userInfo = reactive(JSON.parse(localStorage.getItem('userInfo') || '{}'));

// 个人资料详情（用于 ProfilePanel 编辑）
const profileInfo = ref({
  faceImage: '',
  nickname: '',
  email: ''
});

/**
 * 获取用户信息
 */
const getUserInfo = async () => {
  try {
    const response = await userApi.getUserInfo();
    const data = response.code === 1000 ? response.data : response;
    profileInfo.value = data;
    if (data.nickname) userInfo.nickname = data.nickname;
    if (data.faceImage) userInfo.faceImage = data.faceImage;
    if (data.email) userInfo.email = data.email;
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
  } catch (error) {
    console.error('获取个人信息失败:', error);
  }
};

/**
 * 更新个人资料
 */
const handleUpdateProfile = async () => {
  if (!profileInfo.value.nickname.trim()) {
    FoxToast.warning('昵称不能为空哦');
    return;
  }
  try {
    await userApi.updateProfile({
      nickname: profileInfo.value.nickname,
      email: profileInfo.value.email
    });
    FoxToast.success('个人信息更新成功啦 ✨');
    userInfo.nickname = profileInfo.value.nickname;
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
  } catch (error) {
    console.error('更新个人信息失败:', error);
  }
};

/**
 * 修改密码（占位）
 */
const handleEditPassword = () => {
  FoxToast.info('修改密码功能开发中...');
};

export function useUserStore() {
  return {
    userInfo,
    profileInfo,
    getUserInfo,
    handleUpdateProfile,
    handleEditPassword
  };
}
