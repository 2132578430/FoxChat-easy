import { ref, reactive } from 'vue';

// 群组列表
const groupList = ref([]);
const isGroupLoading = ref(false);

// 创建群组表单
const createGroupForm = reactive({
  groupName: ''
});

// 添加 LLM 好友表单
const addLlmFriendForm = reactive({
  nickname: '',
  myName: '',
  partnerName: '',
  experience: ''
});

export function useGroupStore() {
  return {
    groupList,
    isGroupLoading,
    createGroupForm,
    addLlmFriendForm
  };
}
