import { useFriendStore } from '@/stores/friendStore';
import { useChatStore } from '@/stores/chatStore';
import { useUserStore } from '@/stores/userStore';
import { useWsStore } from '@/stores/wsStore';
import { useUiStore } from '@/stores/uiStore';
import * as friendApi from '@/api/friend';
import * as messageApi from '@/api/message';
import request from '@/utils/request';
import { encodeProtocol } from '@/utils/protocol';
import { resolveAvatarUrl } from '@/utils/avatar';
import { ElMessage } from 'element-plus';
import { nextTick } from 'vue';

export function useFriends() {
  const { friendList, friendRequestList } = useFriendStore();
  const chatStore = useChatStore();
  const { userInfo } = useUserStore();
  const { ws, sendBinaryMessage } = useWsStore();
  const { showRag } = useUiStore();

  const getUnreadCounts = async () => {
    try {
      const response = await messageApi.getUnreadCounts();
      const countsMap = response.code === 1000 ? response.data : response;
      if (countsMap) {
        friendList.value.forEach(friend => {
          const fid = String(friend.userId || friend.id);
          if (countsMap[fid]) {
            friend.unreadCount = countsMap[fid];
          }
        });
      }
    } catch (error) {
      console.error('获取未读数失败:', error);
    }
  };

  const getFriendList = async () => {
    try {
      const response = await friendApi.getFriendList();
      let list = [];
      if (response.code === 1000 && response.data) {
        list = response.data;
      } else if (Array.isArray(response)) {
        list = response;
      } else if (response && response.list) {
        list = response.list;
      } else if (response && (response.userId || response.id)) {
        list = [response];
      }
      friendList.value = list.map(f => ({
        ...f,
        online: f.online !== undefined ? f.online : false,
        unreadCount: 0
      }));
      getUnreadCounts();
    } catch (error) {
      console.error('获取好友列表出错:', error);
    }
  };

  const getFriendRequests = async () => {
    try {
      const res = await friendApi.getFriendRequests();
      let list = [];
      if (Array.isArray(res)) {
        list = res;
      } else if (res && Array.isArray(res.data)) {
        list = res.data;
      } else if (res && res.list) {
        list = res.list;
      }
      friendRequestList.value = list.map(item => ({
        ...item,
        userId: item.sendUserId || item.userId || item.id,
        username: item.sendNickname || item.sendUsername || item.nickname || item.username || ('用户' + (item.sendUserId || item.userId)),
        faceImage: item.sendFaceImage || item.faceImage || item.face_image,
        isRequest: true
      }));
    } catch (error) {
      console.error('获取好友申请失败:', error);
    }
  };

  const handleFriendSearch = async (text, friendListRef) => {
    if (!friendListRef) return;
    if (!text.trim()) {
      friendListRef.isSearching = false;
      friendListRef.searchResultList = [];
      return;
    }
    friendListRef.isSearching = true;
    friendListRef.searchResultList = [];
    try {
      const localResult = friendList.value
        .filter(f =>
          (f.nickname && f.nickname.includes(text)) ||
          (f.username && f.username.includes(text))
        )
        .map(f => ({ ...f, isFriend: true, isGroup: false }));
      if (localResult.length > 0) {
        friendListRef.searchResultList = localResult;
      } else {
        const response = await friendApi.searchFriend(text);
        const data = response.code === 1000 ? response.data : response;
        let results = Array.isArray(data) ? data : (data && data.list ? data.list : (data ? [data] : []));
        friendListRef.searchResultList = results.map(user => {
          const targetId = String(user.userId || user.id);
          const isAlreadyFriend = friendList.value.some(f => String(f.userId || f.id) === targetId);
          return { ...user, isFriend: isAlreadyFriend, isGroup: false };
        });
      }
    } catch (error) {
      console.error('搜索好友失败:', error);
      friendListRef.searchResultList = [];
    }
  };

  const handleAddFriend = async (friend) => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      ElMessage.error('服务器连接已断开');
      return;
    }
    const addFriendMsg = {
      type: 1104,
      chatMsg: {
        sender: { userId: userInfo.userId },
        acceptUserId: friend.userId || friend.id
      },
      extend: ''
    };
    try {
      await sendBinaryMessage(encodeProtocol(addFriendMsg));
      ElMessage.success('好友申请已发送');
    } catch (error) {
      console.error(error);
      ElMessage.error('发送失败');
    }
  };

  const handleAcceptFriend = async (friend) => {
    const targetId = friend.userId || friend.sendUserId || friend.id;
    if (!targetId) {
      ElMessage.error('无法获取用户ID');
      return;
    }
    try {
      const res = await friendApi.acceptFriend(targetId);
      if (res.code === 1000 || res.code === 200) {
        ElMessage.success('已添加好友');
        getFriendList();
        getFriendRequests();
      } else {
        ElMessage.error(res.msg || '操作失败');
      }
    } catch (error) {
      console.error(error);
      ElMessage.error('操作失败');
    }
  };

  const handleDeleteFriend = async (friend) => {
    if (!friend) return;
    const friendId = friend.userId || friend.id || friend.llmId;
    const role = friend.role || 0;
    try {
      await friendApi.deleteFriend(friendId, role);
      ElMessage.success('好友已删除');
      getFriendList();
      const currentId = chatStore.currentFriend.value?.userId || chatStore.currentFriend.value?.id;
      if (currentId && String(currentId) === String(friendId)) {
        chatStore.currentFriend.value = {};
        chatStore.messageList.value = [];
      }
    } catch (error) {
      console.error('删除好友失败:', error);
      ElMessage.error('删除好友失败');
    }
  };

  const handleEditLlmFriend = (friend) => {
    if (!friend) return;
    const { preselectedLlmFriendId, showFriendList, showGroupList, showProfile, showRag: showRagRef, showLlmConfigPanel } = useUiStore();
    const friendId = friend.userId || friend.id || friend.llmId;
    preselectedLlmFriendId.value = friendId;
    showFriendList.value = false;
    showGroupList.value = false;
    showProfile.value = false;
    showRagRef.value = false;
    showLlmConfigPanel.value = true;
  };

  const selectFriend = async (friend) => {
    if (friend.isRequest) return;
    showRag.value = false;
    chatStore.currentChatType.value = 'private';
    chatStore.currentGroup.value = {};
    chatStore.currentFriend.value = friend;
    const targetId = friend.userId || friend.id;
    friend.unreadCount = 0;
    chatStore.messageList.value = [];
    chatStore.lastTimestamp.value = Date.now();
    chatStore.lastMsgId.value = null;
    chatStore.hasMoreHistory.value = true;

    if (targetId) {
      if (friend.role === 1 || friend.isOldFriend) {
        try {
          const res = await request.post('/llm/history', {
            llmId: targetId,
            lastTime: Date.now(),
            lastId: null
          });
          let historyList = [];
          if (res && res.data && Array.isArray(res.data)) {
            historyList = res.data;
          } else if (Array.isArray(res)) {
            historyList = res;
          }
          const mapped = historyList.map(msg => {
            let blocks = null;
            let emotion = null;
            let content = msg.msgContent;
            try {
              const parsed = typeof msg.msgContent === 'string' ? JSON.parse(msg.msgContent) : msg.msgContent;
              if (Array.isArray(parsed)) {
                blocks = parsed;
                content = null;
              } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
                blocks = parsed.blocks;
                emotion = parsed.emotion || null;
                content = null;
              }
            } catch (e) {}
            return {
              id: msg.id,
              content: content,
              blocks: blocks,
              emotion: emotion,
              status: msg.status === 4 ? 'failed' : undefined,
              isMine: msg.isHuman,
              type: 'text',
              createTime: msg.createTime,
              senderId: msg.isHuman ? msg.sendUserId : msg.llmId,
              senderName: msg.isHuman ? (userInfo.nickname || userInfo.username) : (friend.nickname || friend.username),
              senderAvatar: msg.isHuman ? resolveAvatarUrl(userInfo.faceImage || userInfo.face_image) : resolveAvatarUrl(friend.faceImage || friend.face_image)
            };
          }).reverse();
          chatStore.messageList.value = mapped;
          if (mapped.length > 0) {
            chatStore.lastMsgId.value = mapped[0].id;
            const timeValue = mapped[0].createTime;
            chatStore.lastTimestamp.value = !isNaN(timeValue) && typeof timeValue !== 'boolean'
              ? Number(timeValue) : new Date(timeValue).getTime();
          }
          nextTick(() => {
            const { scrollToBottom } = useChat();
            scrollToBottom(true);
          });
        } catch (error) {
          console.error('获取 LLM 历史记录失败:', error);
        }
      } else {
        const { getChatHistory } = useChat();
        await getChatHistory(targetId, true);
        await signUnreadMessages(targetId);
      }
    } else {
      console.error('无法从好友对象中获取 ID:', friend);
      ElMessage.error('获取好友信息失败');
    }
  };

  const signUnreadMessages = async (friendId) => {
    try {
      const res = await messageApi.getUnsignedMessages(friendId);
      let msgIds = null;
      if (res && res.code === 1000 && res.data) {
        msgIds = typeof res.data === 'object' ? res.data.msgId : res.data;
      } else if (typeof res === 'string') {
        msgIds = res;
      } else if (res && typeof res === 'object' && res.msgId) {
        msgIds = res.msgId;
      }
      if (msgIds && ws.value && ws.value.readyState === WebSocket.OPEN) {
        const signMsg = {
          type: 1102,
          chatMsg: {
            sender: { userId: String(friendId) }
          },
          extend: String(msgIds)
        };
        await sendBinaryMessage(encodeProtocol(signMsg));
      }
    } catch (error) {
      console.error('批量签收未读消息失败:', error);
    }
  };

  return {
    getFriendList,
    getFriendRequests,
    handleFriendSearch,
    handleAddFriend,
    handleAcceptFriend,
    handleDeleteFriend,
    handleEditLlmFriend,
    selectFriend,
    signUnreadMessages,
    getUnreadCounts
  };
}
