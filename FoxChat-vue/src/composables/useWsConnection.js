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

export function useWsConnection() {
  const { ws, startHeartbeat, stopHeartbeat, sendBinaryMessage } = useWsStore();
  const { userInfo } = useUserStore();
  const chatStore = useChatStore();
  const { friendList } = useFriendStore();
  const { handleLlmToken } = useChat();
  const { getFriendRequests } = useFriends();
  const router = useRouter();

  const initWebSocket = async () => {
    try {
      if (!userInfo?.userId) {
        FoxToast.error('未登录，无法连接服务器');
        router.push('/login');
        return;
      }

      const url = CHAT_SERVICE_URL;
      console.log(`Connecting to WebSocket: ${url}`);

      if (ws.value) {
        ws.value.close();
      }

      ws.value = new WebSocket(url);
      ws.value.binaryType = 'arraybuffer';

      ws.value.onopen = async () => {
        console.log('WebSocket connected successfully!');
        const legacyToken = localStorage.getItem('token');
        if (legacyToken) {
          const authMsg = {
            type: 1100,
            chatMsg: {},
            extend: legacyToken
          };
          try {
            console.log('[WS] Sending legacy auth message for compatibility');
            const binaryData = encodeProtocol(authMsg);
            sendBinaryMessage(binaryData);
          } catch (e) {
            console.error('[WS] Error sending auth message:', e);
          }
        }
        startHeartbeat();
      };

      ws.value.onerror = (error) => {
        console.error('[WS] WebSocket error:', error);
        FoxToast.error('服务器连接发生错误');
      };

      ws.value.onmessage = async (event) => {
        try {
          await handleMessage(event.data);
        } catch (e) {
          console.error('处理消息出错:', e);
        }
      };

      ws.value.onclose = (event) => {
        console.log('WebSocket closed:', event);
        stopHeartbeat();
      };
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      FoxToast.error('连接服务器失败');
    }
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

      console.log('收到解码后的消息:', data);

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
