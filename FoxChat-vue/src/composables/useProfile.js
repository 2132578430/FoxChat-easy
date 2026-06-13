import { ref } from 'vue';
import { useUserStore } from '@/stores/userStore';
import { useUiStore } from '@/stores/uiStore';
import * as friendApi from '@/api/friend';
import { ElMessage } from 'element-plus';

const uploadingAvatar = ref(false);

export function useProfile() {
  const { userInfo, profileInfo, getUserInfo, handleUpdateProfile, handleEditPassword } = useUserStore();
  const { showProfile, showFriendList, showGroupList, showAvatarCropper, isAvatarCropperForLlm, pendingLlmAvatarUrl } = useUiStore();

  const toggleProfile = () => {
    showProfile.value = !showProfile.value;
    if (showProfile.value) {
      showFriendList.value = false;
      showGroupList.value = false;
    }
    getUserInfo();
  };

  const handleEditAvatar = () => {
    isAvatarCropperForLlm.value = false;
    showAvatarCropper.value = true;
  };

  const handleOpenLlmAvatarCropper = () => {
    pendingLlmAvatarUrl.value = null;
    isAvatarCropperForLlm.value = true;
    showAvatarCropper.value = true;
  };

  const handleAvatarSuccess = (newAvatarUrl) => {
    if (!newAvatarUrl) return;
    if (isAvatarCropperForLlm.value) {
      pendingLlmAvatarUrl.value = newAvatarUrl;
    } else {
      userInfo.faceImage = newAvatarUrl;
      profileInfo.value.faceImage = newAvatarUrl;
      localStorage.setItem('userInfo', JSON.stringify(userInfo));
    }
  };

  const handleAvatarBlob = async (blob) => {
    if (!blob) return;
    uploadingAvatar.value = true;
    try {
      const formData = new FormData();
      formData.append('file', blob, 'avatar.png');
      const res = await friendApi.uploadLlmAvatar(formData);
      uploadingAvatar.value = false;
      if (res && typeof res === 'string' && res.startsWith('http')) {
        pendingLlmAvatarUrl.value = res;
        ElMessage.success('模型头像上传成功啦 ✨');
      } else if (res && res.data) {
        pendingLlmAvatarUrl.value = res.data;
        ElMessage.success('模型头像上传成功啦 ✨');
      } else {
        ElMessage.error('上传失败');
      }
    } catch (error) {
      uploadingAvatar.value = false;
      console.error('上传模型头像失败:', error);
      ElMessage.error('上传失败，请稍后再试');
    }
  };

  return {
    uploadingAvatar,
    toggleProfile,
    handleEditAvatar,
    handleOpenLlmAvatarCropper,
    handleAvatarSuccess,
    handleAvatarBlob
  };
}
