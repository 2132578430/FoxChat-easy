import { ref } from 'vue';

// 面板开关状态
const showFriendList = ref(false);
const showGroupList = ref(false);
const showProfile = ref(false);
const showRag = ref(false);
const showLlmConfigPanel = ref(false);
const showMemoryPanel = ref(false);

// 弹窗状态
const showCreateGroupDialog = ref(false);
const showAddLlmFriendDialog = ref(false);
const showUploadDialog = ref(false);
const showAvatarCropper = ref(false);

// LLM 头像裁剪
const preselectedLlmFriendId = ref(null);
const pendingLlmAvatarUrl = ref(null);
const isAvatarCropperForLlm = ref(false);

// 搜索文本
const searchText = ref('');

export function useUiStore() {
  return {
    showFriendList,
    showGroupList,
    showProfile,
    showRag,
    showLlmConfigPanel,
    showMemoryPanel,
    showCreateGroupDialog,
    showAddLlmFriendDialog,
    showUploadDialog,
    showAvatarCropper,
    preselectedLlmFriendId,
    pendingLlmAvatarUrl,
    isAvatarCropperForLlm,
    searchText
  };
}
