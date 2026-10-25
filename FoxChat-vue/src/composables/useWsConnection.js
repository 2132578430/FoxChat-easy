import { useWsStore } from '@/stores/wsStore';
import { useUserStore } from '@/stores/userStore';
import { useChatStore } from '@/stores/chatStore';
import { useFriendStore } from '@/stores/friendStore';
import { useChat } from '@/composables/useChat';
import { useFriends } from '@/composables/useFriends';
import { CHAT_SERVICE_URL } from '@/utils/config';
import { encodeProtocol, decodeProtocol } from '@/utils/protocol';
import { resolveAvatarUrl } from '@/utils/avatar';
import { FoxToast } from '@/components/FoxUI';
import { useRouter } from 'vue-router';

const RECONNECT_BASE_DELAY = 1000;
const RECONNECT_MAX_DELAY = 30000;
const RESUME_STALE_MS = 30000;

let teardownActiveConnection = null;

export function disconnectWebSocket() {
  if (teardownActiveConnection) {
    teardownActiveConnection();
    teardownActiveConnection = null;
  }
}

export function useWsConnection() {
  const { ws, startHeartbeat, stopHeartbeat, sendBinaryMessage } = useWsStore();
  const { userInfo } = useUserStore();
  const chatStore = useChatStore();
  const { friendList } = useFriendStore();
  const { handleLlmToken, syncLatestMessages } = useChat();
  const { getFriendRequests, getFriendList } = useFriends();
  const router = useRouter();

  let reconnectTimer = null;
  let reconnectAttempts = 0;
  let manuallyClosed = false;
  let hasConnectedOnce = false;
  let hiddenAt = 0;
  let visibilityHandler = null;
  let onlineHandler = null;
  let pageShowHandler = null;

  const clearReconnectTimer = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const refreshAfterReconnect = async () => {
    await syncLatestMessages();
    await Promise.all([getFriendList(), getFriendRequests()]);
  };

  const openSocket = ({ isReconnect = false } = {}) => {
    if (manuallyClosed || !userInfo?.userId) return;
    clearReconnectTimer();

    const previousSocket = ws.value;
    if (previousSocket) {
      previousSocket.onopen = null;
      previousSocket.onerror = null;
      previousSocket.onmessage = null;
      previousSocket.onclose = null;
      try { previousSocket.close(); } catch (e) {}
    }

    const socket = new WebSocket(CHAT_SERVICE_URL);
    ws.value = socket;
    socket.binaryType = 'arraybuffer';

    socket.onopen = async () => {
      if (ws.value !== socket) return;
      reconnectAttempts = 0;

      const legacyToken = localStorage.getItem('token');
      if (legacyToken) {
        const authMsg = {
          type: 1100,
          chatMsg: {},
          extend: legacyToken
        };
        try {
          const binaryData = encodeProtocol(authMsg);
          sendBinaryMessage(binaryData);
        } catch (e) {
          console.error('[WS] Error sending auth message:', e);
        }
      }
      startHeartbeat();

      const needSync = isReconnect || hasConnectedOnce;
      hasConnectedOnce = true;
      if (needSync) {
        try {
          await refreshAfterReconnect();
        } catch (e) {
          console.error('[WS] 重连后同步失败:', e);
        }
      }
    };

    socket.onerror = (error) => {
      if (ws.value !== socket) return;
      console.error('[WS] WebSocket error:', error);
    };

    socket.onmessage = async (event) => {
      try {
        await handleMessage(event.data);
      } catch (e) {
        console.error('处理消息出错:', e);
      }
    };

    socket.onclose = () => {
      if (ws.value !== socket) return;
      stopHeartbeat();
      ws.value = null;
      scheduleReconnect();
    };
  };

  const scheduleReconnect = () => {
    if (manuallyClosed || reconnectTimer) return;
    if (!userInfo?.userId) return;
    if (document.hidden) return;

    const delay = Math.min(RECONNECT_MAX_DELAY, RECONNECT_BASE_DELAY * 2 ** reconnectAttempts);
    const jitter = Math.floor(Math.random() * delay * 0.5);
    reconnectAttempts += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      if (!document.hidden) {
        openSocket({ isReconnect: true });
      }
    }, delay + jitter);
  };

  const reconnectNow = (reason) => {
    if (manuallyClosed || !userInfo?.userId) return;
    clearReconnectTimer();
    reconnectAttempts = 0;
    console.info(`[WS] ${reason}，重建连接`);
    openSocket({ isReconnect: true });
  };

  const handleVisibilityChange = () => {
    if (document.hidden) {
      hiddenAt = Date.now();
      return;
    }

    const hiddenFor = hiddenAt ? Date.now() - hiddenAt : 0;
    hiddenAt = 0;
    if (manuallyClosed || !userInfo?.userId) return;

    const state = ws.value?.readyState;
    // 长时间挂起后 readyState 可能仍是 OPEN，但底层链路已经断了，直接重建
    if ((state === WebSocket.OPEN || state === WebSocket.CONNECTING) && hiddenFor <= RESUME_STALE_MS) {
      return;
    }
    reconnectNow('页面恢复');
  };

  const handleOnline = () => {
    // 网络恢复时旧连接可能仍显示 OPEN 但实际已失效，直接重建
    reconnectNow('网络恢复');
  };

  const handlePageShow = (event) => {
    if (event.persisted && ws.value?.readyState !== WebSocket.OPEN) {
      reconnectNow('页面缓存恢复');
    }
  };

  const bindLifecycle = () => {
    if (visibilityHandler) return;
    visibilityHandler = handleVisibilityChange;
    onlineHandler = handleOnline;
    pageShowHandler = handlePageShow;
    document.addEventListener('visibilitychange', visibilityHandler);
    window.addEventListener('online', onlineHandler);
    window.addEventListener('pageshow', pageShowHandler);
  };

  const unbindLifecycle = () => {
    if (visibilityHandler) document.removeEventListener('visibilitychange', visibilityHandler);
    if (onlineHandler) window.removeEventListener('online', onlineHandler);
    if (pageShowHandler) window.removeEventListener('pageshow', pageShowHandler);
    visibilityHandler = null;
    onlineHandler = null;
    pageShowHandler = null;
  };

  const initWebSocket = async () => {
    // 登录态由 HTTPOnly Cookie 承载，JS 读不到 token，只用 userInfo 判断
    if (!userInfo?.userId) {
      FoxToast.error('未登录，无法连接服务器');
      router.push('/login');
      return;
    }

    manuallyClosed = false;
    reconnectAttempts = 0;
    hasConnectedOnce = false;
    clearReconnectTimer();
    bindLifecycle();

    teardownActiveConnection = () => {
      manuallyClosed = true;
      clearReconnectTimer();
      unbindLifecycle();
      const socket = ws.value;
      if (socket) {
        socket.onopen = null;
        socket.onerror = null;
        socket.onmessage = null;
        socket.onclose = null;
        try { socket.close(); } catch (e) {}
      }
      ws.value = null;
      stopHeartbeat();
      hasConnectedOnce = false;
    };

    openSocket({ isReconnect: false });
  };

  const handleMessage = async (rawInput) => {
    try {
      let buffer = rawInput;

      if (typeof rawInput === 'string') {
        console.warn('⚠️ [WebSocket] 收到字符串消息，尝试 Base64 解码兼容...');
        try {
          const binaryString = window.atob(rawInput);
          const len = binaryString.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          buffer = bytes.buffer;
        } catch (e) {
          console.error('❌ Base64 解码失败:', rawInput);
          return;
        }
      } else if (!(rawInput instanceof ArrayBuffer)) {
        console.error('❌ [WebSocket] 收到不支持的数据类型:', rawInput);
        return;
      }

      const data = decodeProtocol(buffer);
      if (!data) return;

      if (data.type == '1105') {
        const isForMe = String(data.chatMsg?.acceptUserId) === String(userInfo.userId);
        if (isForMe) {
          FoxToast.info('收到好友申请', 5000);
          getFriendRequests();
        }
      } else if (data.type == '1101') {
        const chatMsg = data.chatMsg;
        const msgId = data.extend;
        const currentFriendId = String(chatStore.currentFriend.value?.userId || chatStore.currentFriend.value?.id || '');
        const senderId = String(chatMsg.sender?.userId || chatMsg.sendUserId || '');
        const myId = String(userInfo.userId || '');

        if (currentFriendId && currentFriendId === senderId) {
          if (msgId && ws.value && ws.value.readyState === WebSocket.OPEN) {
            const signMsg = {
              type: 1102,
              chatMsg: { sender: { userId: senderId } },
              extend: String(msgId)
            };
            await sendBinaryMessage(encodeProtocol(signMsg));
          }

          let blocks = null;
          let emotion = null;
          let content = chatMsg.msg;
          try {
            const parsed = typeof chatMsg.msg === 'string' ? JSON.parse(chatMsg.msg) : chatMsg.msg;
            if (Array.isArray(parsed)) {
              blocks = parsed;
              content = null;
            } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
              blocks = parsed.blocks;
              emotion = parsed.emotion || null;
              content = null;
            }
          } catch (e) {}

          chatStore.messageList.value.push({
            id: msgId || Date.now(),
            content: content,
            blocks: blocks,
            emotion: emotion,
            isMine: false,
            type: 'text',
            createTime: chatMsg.createTime || new Date().toISOString(),
            senderId: senderId,
            senderName: chatMsg.sender?.nickname || chatMsg.sender?.username || senderId,
            senderAvatar: chatMsg.sender?.faceImage
          });
        } else {
          // 不是当前聊天对象，更新未读数
          const friend = friendList.value.find(f => String(f.userId || f.id) === senderId);
          if (friend) {
            friend.unreadCount = (friend.unreadCount || 0) + 1;
          }
        }
      } else if (data.type == '1201') {
        // 群聊消息
        const groupMsg = data.groupMsg;
        const currentGroupId = String(chatStore.currentGroup.value?.id || chatStore.currentGroup.value?.groupId || '');
        const msgGroupId = String(groupMsg?.groupId || '');

        if (currentGroupId && currentGroupId === msgGroupId) {
          let blocks = null;
          let emotion = null;
          let content = groupMsg.msg;
          try {
            const parsed = typeof groupMsg.msg === 'string' ? JSON.parse(groupMsg.msg) : groupMsg.msg;
            if (Array.isArray(parsed)) {
              blocks = parsed;
              content = null;
            } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
              blocks = parsed.blocks;
              emotion = parsed.emotion || null;
              content = null;
            }
          } catch (e) {}

          const senderId = String(groupMsg.sender?.userId || '');
          const isMine = senderId === String(userInfo.userId || '');

          chatStore.messageList.value.push({
            id: groupMsg.id || Date.now(),
            content: content,
            blocks: blocks,
            emotion: emotion,
            isMine: isMine,
            type: 'text',
            createTime: groupMsg.createTime || new Date().toISOString(),
            senderId: senderId,
            senderName: groupMsg.sender?.nickname || groupMsg.sender?.username || senderId,
            senderAvatar: groupMsg.sender?.faceImage
          });
        }
      } else if (data.type == '1108') {
        // LLM 流式 token
        handleLlmToken(data);
      } else if (data.type == '1104') {
        // 好友上线通知
        const onlineUserId = String(data.chatMsg?.sender?.userId || '');
        if (onlineUserId) {
          const friend = friendList.value.find(f => String(f.userId || f.id) === onlineUserId);
          if (friend) {
            friend.online = true;
          }
        }
      } else if (data.type == '1106') {
        // 好友下线通知
        const offlineUserId = String(data.chatMsg?.sender?.userId || '');
        if (offlineUserId) {
          const friend = friendList.value.find(f => String(f.userId || f.id) === offlineUserId);
          if (friend) {
            friend.online = false;
          }
        }
      }
    } catch (e) {
      console.error('处理消息出错:', e);
    }
  };

  return { initWebSocket, handleMessage };
}
