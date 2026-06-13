import { ref } from 'vue';
import { encodeProtocol } from '@/utils/protocol';

// WebSocket 实例
const ws = ref(null);

// 心跳定时器
let heartbeatTimer = null;

/**
 * 停止心跳
 */
const stopHeartbeat = () => {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
};

/**
 * 发送二进制消息
 */
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

/**
 * 启动心跳
 */
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

export function useWsStore() {
  return {
    ws,
    stopHeartbeat,
    sendBinaryMessage,
    startHeartbeat
  };
}
