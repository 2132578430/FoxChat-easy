import { ref, watch } from 'vue';
import { useGroupStore } from '@/stores/groupStore';
import { useChatStore } from '@/stores/chatStore';
import { useUiStore } from '@/stores/uiStore';
import { useChat } from '@/composables/useChat';
import { useFriends } from '@/composables/useFriends';
import * as groupApi from '@/api/group';
import request from '@/utils/request';
import { FoxToast } from '@/components/FoxUI';

export function useGroups() {
  const { groupList, isGroupLoading, createGroupForm, addLlmFriendForm } = useGroupStore();
  const chatStore = useChatStore();
  const { showGroupList, showCreateGroupDialog, showAddLlmFriendDialog, showRag } = useUiStore();

  const isCreatingGroup = ref(false);
  const isAddingLlmFriend = ref(false);

  const getGroupList = async () => {
    try {
      isGroupLoading.value = true;
      const response = await groupApi.getGroupList();
      const data = response.code === 1000 ? response.data : response;
      let list = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && data.list) {
        list = data.list;
      }
      groupList.value = list.map(g => ({
        ...g,
        id: g.id || g.groupId,
        groupName: g.groupName || g.name,
        faceImage: g.faceImage || g.avatar,
        ownerUserId: g.ownerUserId,
        role: g.role,
        isJoined: g.isJoined !== undefined ? g.isJoined : true,
        unreadCount: 0
      }));
    } catch (error) {
      console.error('获取群组列表出错:', error);
    } finally {
      isGroupLoading.value = false;
    }
  };

  const handleGroupSearch = async (text, groupListRef) => {
    if (!groupListRef) return;
    if (!text.trim()) {
      groupListRef.isSearching = false;
      groupListRef.searchResultList = [];
      return;
    }
    groupListRef.isSearching = true;
    groupListRef.searchResultList = [];
    try {
      const localResult = groupList.value
        .filter(g => g.groupName && g.groupName.includes(text))
        .map(g => ({ ...g, isJoined: true, isGroup: true }));
      if (localResult.length > 0) {
        groupListRef.searchResultList = localResult;
      } else {
        const response = await groupApi.searchGroup(text);
        const data = response.code === 1000 ? response.data : response;
        let results = Array.isArray(data) ? data : (data && data.list ? data.list : (data ? [data] : []));
        groupListRef.searchResultList = results.map(g => ({
          ...g,
          id: g.id || g.groupId,
          groupName: g.groupName || g.name,
          faceImage: g.faceImage || g.avatar,
          isJoined: g.isJoined !== undefined ? g.isJoined : false,
          isGroup: true
        }));
      }
    } catch (error) {
      console.error('搜索群组失败:', error);
      groupListRef.searchResultList = [];
    }
  };

  const selectGroup = async (group) => {
    showRag.value = false;
    chatStore.currentChatType.value = 'group';
    chatStore.currentFriend.value = {};
    chatStore.currentGroup.value = group;
    const targetId = group.id || group.groupId;
    chatStore.messageList.value = [];
    chatStore.lastTimestamp.value = Date.now();
    chatStore.hasMoreHistory.value = true;
    chatStore.isLoadingHistory.value = false;

    if (targetId) {
      try {
        const { getChatHistory } = useChat();
        await getChatHistory(targetId, true);
      } catch (e) {
        console.error('群聊历史请求异常:', e);
      }
    } else {
      console.error('无法从群组对象中获取 ID:', group);
      FoxToast.error('获取群组信息失败');
    }
  };

  const handleCreateGroup = async (createGroupFormRef) => {
    if (!createGroupFormRef) return;
    await createGroupFormRef.validate(async (valid) => {
      if (valid) {
        isCreatingGroup.value = true;
        try {
          const groupDto = { groupName: createGroupForm.groupName };
          await groupApi.createGroup(groupDto);
          FoxToast.success('狐狸窝创建成功！');
          showCreateGroupDialog.value = false;
          createGroupForm.groupName = '';
          getGroupList();
        } catch (error) {
          console.error('创建狐狸窝失败:', error);
          FoxToast.error(error.message || '网络错误，创建失败');
        } finally {
          isCreatingGroup.value = false;
        }
      }
    });
  };

  const handleAddLlmFriend = async (addLlmFriendFormRef) => {
    if (!addLlmFriendFormRef) return;
    await addLlmFriendFormRef.validate(async (valid) => {
      if (valid) {
        isAddingLlmFriend.value = true;
        try {
          const dto = {
            nickname: addLlmFriendForm.nickname,
            myName: addLlmFriendForm.myName,
            partnerName: addLlmFriendForm.partnerName,
            experience: addLlmFriendForm.experience
          };
          await request.post('/llm/add', dto);
          FoxToast.success('陪伴者创建成功！请配置模型参数');
          showAddLlmFriendDialog.value = false;
          addLlmFriendForm.nickname = '';
          addLlmFriendForm.myName = '';
          addLlmFriendForm.partnerName = '';
          addLlmFriendForm.experience = '';
          const { getFriendList } = useFriends();
          getFriendList();
        } catch (error) {
          console.error('创建陪伴者失败:', error);
          FoxToast.error(error.message || '创建失败');
        } finally {
          isAddingLlmFriend.value = false;
        }
      }
    });
  };

  const handleJoinGroup = async (group) => {
    if (!group || !group.id) {
      FoxToast.error('群组信息无效');
      return;
    }
    try {
      await groupApi.joinGroup(group.id);
      FoxToast.success('加入群组成功');
      getGroupList();
    } catch (error) {
      console.error('加入群组失败:', error);
      FoxToast.error('加入群组失败');
    }
  };

  const handleGroupClick = async (group) => {
    if (group.isJoined) {
      await selectGroup(group);
    }
  };

  // 监听 showGroupList 变化，自动加载群组列表
  watch(showGroupList, (newVal) => {
    if (newVal) {
      getGroupList();
    }
  });

  return {
    groupList,
    isGroupLoading,
    isCreatingGroup,
    isAddingLlmFriend,
    getGroupList,
    handleGroupSearch,
    selectGroup,
    handleCreateGroup,
    handleAddLlmFriend,
    handleJoinGroup,
    handleGroupClick
  };
}
