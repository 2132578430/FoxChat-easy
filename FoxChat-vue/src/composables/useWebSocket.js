import { ref, onMounted, onUnmounted } from 'vue';

/**
 * WebSocket Composable
 * @param {Object} options - Configuration options
 * @param {Function} options.onMessage - Message callback for custom handling
 * @param {Function} options.onConnect - Connection success callback
 * @param {Function} options.onError - Error callback
 * @param {Function} options.onFriendRequest - Friend request callback
 * @param {Function} options.onPrivateMessage - Private message callback
 * @param {Function} options.onGroupMessage - Group message callback
 * @param {Function} options.onOnlineStatus - Online/offline status callback
 * @param {Object} options.userInfo - User info object
 * @param {Object} options.currentFriend - Current chat friend ref
 * @param {Object} options.currentGroup - Current chat group ref
 * @param {Function} options.encodeProtocol - Protocol encoder function
 * @param {Function} options.decodeProtocol - Protocol decoder function
 * @param {string} options.CHAT_SERVICE_URL - WebSocket server URL
 */
export function useWebSocket(options = {}) {
  const {
    onMessage,
    onConnect,
    onError,
    onFriendRequest,
    onPrivateMessage,
    onGroupMessage,
    onOnlineStatus,
    userInfo = {},
    currentFriend = ref({}),
    currentGroup = ref({}),
    encodeProtocol,
    decodeProtocol,
    CHAT_SERVICE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:13000'
  } = options;

  const ws = ref(null);
  const isConnected = ref(false);
  let heartbeatTimer = null;

  // Send binary message through WebSocket
  const sendBinaryMessage = (protocolData) => {
    console.log('[WS Send] Preparing to send binary data:', protocolData);
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      try {
        ws.value.send(protocolData);
        console.log('[WS Send] Data sent successfully');
      } catch (error) {
        console.error('[WS Send] Error sending message:', error);
      }
    } else {
      console.error('[WS Send] WebSocket not connected. Current readyState:', ws.value?.readyState);
    }
  };

  // Stop heartbeat timer
  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  };

  // Start heartbeat timer
  const startHeartbeat = () => {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        const heartbeatMsg = {
          type: 1103,
          chatMsg: {},
          extend: 'ping'
        };
        try {
          const binaryData = encodeProtocol(heartbeatMsg);
          sendBinaryMessage(binaryData);
        } catch (e) {
          console.error('发送心跳包失败:', e);
        }
      }
    }, 30000);
  };

  // Initialize WebSocket connection
  const connect = async () => {
    try {
      // Cookie 自动携带 token，无需检查 localStorage
      // 但仍需 userInfo 用于消息处理
      if (!userInfo?.userId) {
        console.error('[WS] No userInfo found, cannot connect');
        return;
      }

      const url = CHAT_SERVICE_URL;
      console.log(`Connecting to WebSocket: ${url}`);

      if (ws.value) {
        ws.value.close();
      }

      ws.value = new WebSocket(url);
      ws.value.binaryType = 'arraybuffer'; // Important: receive binary data

      ws.value.onopen = async () => {
        console.log('WebSocket connected successfully!');
        isConnected.value = true;

        // Cookie 验证在握手时自动完成，无需发送 auth message
        // 但保留兼容逻辑：如果 localStorage 有 token 则发送 auth message
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
        onConnect?.();
      };

      ws.value.onerror = (error) => {
        console.error('[WS] WebSocket error:', error);
        onError?.(error);
      };

      ws.value.onmessage = async (event) => {
        try {
          const data = event.data;
          await handleMessage(data);
        } catch (e) {
          console.error('处理消息出错:', e);
        }
      };

      ws.value.onclose = (event) => {
        console.log('WebSocket closed:', event);
        isConnected.value = false;
        stopHeartbeat();
      };

    } catch (error) {
      console.error('WebSocket connection failed:', error);
      onError?.(error);
    }
  };

  // Handle incoming messages
  const handleMessage = async (rawInput) => {
    try {
      let buffer = rawInput;

      // Debug: check received data type
      if (typeof rawInput === 'string') {
        console.warn('⚠️ [WebSocket] Received string message (TextFrame), expected binary (BinaryFrame). Trying Base64 decode...');
        try {
          const binaryString = window.atob(rawInput);
          const len = binaryString.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          buffer = bytes.buffer;
        } catch (e) {
          console.error('❌ Base64 decode failed:', rawInput);
          return;
        }
      } else if (!(rawInput instanceof ArrayBuffer)) {
        console.error('❌ [WebSocket] Unsupported data type:', rawInput);
        return;
      }

      // Decode binary protocol
      const data = decodeProtocol(buffer);
      if (!data) return;

      console.log('收到解码后的消息:', data);

      // Call custom message handler first
      if (onMessage) {
        const handled = onMessage(data);
        if (handled === false) return; // If handler returns false, skip default handling
      }

      const myId = String(userInfo?.userId || '');

      // Friend request (1105)
      if (data.type == '1105') {
        const isForMe = String(data.chatMsg?.acceptUserId) === String(userInfo?.userId);

        if (isForMe) {
          // Call callback if provided
          if (onFriendRequest) {
            onFriendRequest(data);
          }
        }
      }
      // Private chat message (1101)
      else if (data.type == '1101') {
        const chatMsg = data.chatMsg;
        const msgId = data.extend;
        const currentFriendId = String(currentFriend.value?.userId || currentFriend.value?.id || '');
        const senderId = String(chatMsg.sender?.userId || chatMsg.sendUserId || '');

        // Send receipt if message is from current chat friend
        if (currentFriendId && currentFriendId === senderId) {
          if (msgId && ws.value && ws.value.readyState === WebSocket.OPEN) {
            const signMsg = {
              type: 1102,
              chatMsg: {
                sender: { userId: senderId }
              },
              extend: String(msgId)
            };
            await sendBinaryMessage(encodeProtocol(signMsg));
          }

          // Parse blocks format
          let blocks = null;
          let content = chatMsg.msg;
          try {
            const parsed = typeof chatMsg.msg === 'string' ? JSON.parse(chatMsg.msg) : chatMsg.msg;
            if (Array.isArray(parsed)) {
              blocks = parsed;
              content = null;
            } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
              blocks = parsed.blocks;
              content = null;
            }
          } catch (e) {
            // Keep original content format
          }

          const messageData = {
            id: msgId || Date.now(),
            content: content,
            blocks: blocks,
            isMine: false,
            type: 'text',
            createTime: chatMsg.createTime || new Date().toISOString(),
            senderId: senderId,
            senderName: currentFriend.value?.nickname || currentFriend.value?.username || '好友',
            senderAvatar: currentFriend.value?.faceImage || currentFriend.value?.face_image
          };

          onPrivateMessage?.(messageData, 'current');
        }
        // Self message (multi-device sync or server echo)
        else if (senderId === myId) {
          const messageData = {
            id: msgId || Date.now(),
            content: chatMsg.msg,
            isMine: true,
            type: 'text',
            senderName: userInfo?.nickname || userInfo?.username,
            senderAvatar: userInfo?.faceImage || userInfo?.face_image
          };

          onPrivateMessage?.(messageData, 'self');
        }
        // Message from other friend (not current chat)
        else {
          const messageData = {
            senderId: senderId,
            content: chatMsg.msg,
            senderName: chatMsg.sender?.nickname || chatMsg.sender?.username
          };

          onPrivateMessage?.(messageData, 'other');
        }
      }
      // Online notification (1106)
      else if (data.type == '1106') {
        const onlineUserId = String(data.chatMsg?.sender?.userId || data.chatMsg?.sendUserId || '');

        onOnlineStatus?.({
          userId: onlineUserId,
          online: true
        });
      }
      // Offline notification (1107)
      else if (data.type == '1107') {
        const offlineUserId = String(data.chatMsg?.sender?.userId || data.chatMsg?.sendUserId || '');

        onOnlineStatus?.({
          userId: offlineUserId,
          online: false
        });
      }
      // Group chat message (1201)
      else if (data.type == '1201') {
        const groupMsg = data.groupMsg;

        const msgSenderId = String(groupMsg?.sender?.userId || groupMsg?.sendUserId || '');
        const isFromMe = msgSenderId === String(userInfo?.userId);

        console.log(`%c[群聊消息] ${isFromMe ? '发送成功(同步)' : '收到成员消息'}`, 'color: #1890ff; font-weight: bold; font-size: 12px;');

        if (groupMsg) {
          const currentGroupId = String(currentGroup.value?.groupId || currentGroup.value?.id || '');
          const msgGroupId = String(groupMsg.groupId || '');
          const senderId = String(groupMsg.sender?.userId || groupMsg.sendUserId || '');

          if (currentGroup.value?.type === 'group' && currentGroupId && currentGroupId === msgGroupId) {
            if (senderId !== myId) {
              const messageData = {
                id: groupMsg.id || Date.now(),
                content: groupMsg.msg || groupMsg.content,
                isMine: false,
                type: 'text',
                createTime: groupMsg.createTime || new Date().toISOString(),
                senderId: senderId,
                senderName: groupMsg.sender?.nickname || groupMsg.sender?.username || groupMsg.nickname || groupMsg.username,
                senderAvatar: groupMsg.sender?.faceImage || groupMsg.faceImage
              };

              onGroupMessage?.(messageData, 'current');
            }
          } else {
            const messageData = {
              groupId: msgGroupId,
              senderId: senderId,
              content: groupMsg.msg || groupMsg.content
            };

            onGroupMessage?.(messageData, 'other');
          }
        }
      }
    } catch (error) {
      console.error('处理消息失败:', error);
    }
  };

  // Send a chat message
  const sendMessage = async (message) => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      console.error('[WS] Cannot send message: WebSocket not connected');
      return false;
    }

    try {
      const binaryData = encodeProtocol(message);
      sendBinaryMessage(binaryData);
      return true;
    } catch (error) {
      console.error('[WS] Send message error:', error);
      return false;
    }
  };

  // Disconnect WebSocket
  const disconnect = () => {
    if (ws.value) {
      try {
        ws.value.close();
      } catch (e) {
        console.error('Error closing WebSocket:', e);
      }
    }
    stopHeartbeat();
    isConnected.value = false;
  };

  // Lifecycle: mount
  onMounted(() => {
    connect();
  });

  // Lifecycle: unmount
  onUnmounted(() => {
    disconnect();
  });

  return {
    ws,
    isConnected,
    sendMessage,
    sendBinaryMessage,
    connect,
    disconnect,
    stopHeartbeat,
    startHeartbeat,
    handleMessage
  };
}

export default useWebSocket;