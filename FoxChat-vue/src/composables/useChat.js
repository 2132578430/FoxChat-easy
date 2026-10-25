import { ref, nextTick } from 'vue';
import { useChatStore } from '@/stores/chatStore';
import { useWsStore } from '@/stores/wsStore';
import { useFriendStore } from '@/stores/friendStore';
import { useUserStore } from '@/stores/userStore';
import { useUiStore } from '@/stores/uiStore';
import { useLlmStream } from '@/composables/useLlmStream';
import { fallbackLlmRest } from '@/composables/useLlmFallback';
import { useRag } from '@/composables/useRag';
import * as messageApi from '@/api/message';
import * as groupApi from '@/api/group';
import request from '@/utils/request';
import { encodeProtocol } from '@/utils/protocol';
import snowflake from '@/utils/snowflake';
import { resolveAvatarUrl } from '@/utils/avatar';
import { FoxToast } from '@/components/FoxUI';

// 模块级共享：Home 的 sendMessage 与 useWsConnection 的 handleLlmToken 使用的是不同 useChat()
// 实例，流式状态必须共享，否则 WS token 会被另一个实例的 active=false 直接丢弃
const llmStreamState = ref({
  active: false,
  llmId: null,
  aiPlaceholderId: null,
  blocks: [],
  currentBlockType: null,
  currentBlockContent: '',
  emotion: null,
  requestFriendId: null,
});

export function useChat() {
  const chatStore = useChatStore();
  const { ws, sendBinaryMessage } = useWsStore();
  const { friendList } = useFriendStore();
  const { userInfo } = useUserStore();
  const { showRag } = useUiStore();
  const { sendStreamMessage } = useLlmStream();

  function flushLlmBlock() {
    const s = llmStreamState.value;
    if (s.currentBlockType && s.currentBlockContent) {
      s.blocks.push({ type: s.currentBlockType, content: s.currentBlockContent });
      s.currentBlockContent = '';
    }
  }

  function handleLlmToken(data) {
    try {
      const token = JSON.parse(data.extend);
      const s = llmStreamState.value;
      if (token.error) {
        console.warn('[LLM WS] 收到错误:', token.error);
        s.active = false;
        chatStore.isLlmTyping.value = false;
        chatStore.llmPendingCount.value--;
        fallbackLlmRest(s.llmId, s.msgContent, chatStore.currentFriend, friendList, chatStore.messageList, s.aiPlaceholderId);
        return;
      }
      if (!s.active) return;
      if (token.isFinal) {
        flushLlmBlock();
        s.emotion = token.emotion || 'neutral';
        const finalBlocks = [...s.blocks];
        const idx = chatStore.messageList.value.findIndex(m => m.id === s.aiPlaceholderId);
        if (idx >= 0) {
          chatStore.messageList.value[idx].blocks = finalBlocks;
          chatStore.messageList.value[idx].emotion = s.emotion;
          chatStore.messageList.value[idx].isStreaming = false;
        }
        if (chatStore.currentFriend.value && (chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id) === s.requestFriendId) {
          chatStore.currentFriend.value.emotion = s.emotion;
          const friend = friendList.value.find(f => String(f.userId || f.id) === String(s.requestFriendId));
          if (friend) friend.emotion = s.emotion;
        }
        s.active = false;
        chatStore.isLlmTyping.value = false;
        chatStore.llmPendingCount.value--;
        return;
      }
      if (token.blockType !== s.currentBlockType) {
        flushLlmBlock();
        s.currentBlockType = token.blockType;
      }
      if (token.content) {
        s.currentBlockContent += token.content;
      }
      const snapshot = [...s.blocks];
      if (s.currentBlockType && s.currentBlockContent) {
        snapshot.push({ type: s.currentBlockType, content: s.currentBlockContent });
      }
      const idx = chatStore.messageList.value.findIndex(m => m.id === s.aiPlaceholderId);
      if (idx >= 0) {
        chatStore.messageList.value[idx].blocks = snapshot;
      }
    } catch (e) {
      console.error('[LLM WS] 解析响应失败:', e, data);
    }
  }

  const scrollToBottom = (force = false) => {
    nextTick(() => {
      // 通过事件通知 MessageList 组件滚动
      // 这里需要 MessageList 的 ref，暂时用 window 事件
      window.dispatchEvent(new CustomEvent('chat-scroll-to-bottom', { detail: { force } }));
    });
  };

  const isLlmConversation = () => {
    const friend = chatStore.currentFriend.value;
    return !!(friend && (friend.role === 1 || friend.isOldFriend));
  };

  const toMillis = (value) => {
    if (value === null || value === undefined || value === '') return NaN;
    if (typeof value === 'number') return value;
    const numeric = Number(value);
    if (!Number.isNaN(numeric) && String(value).trim() !== '') return numeric;
    return new Date(value).getTime();
  };

  const fetchHistoryPage = async (targetId, lastTimestamp, lastId = null) => {
    let data;
    if (isLlmConversation()) {
      const res = await request.post('/llm/history', {
        llmId: targetId,
        lastTime: lastTimestamp,
        lastId
      });
      data = (res && res.code === 1000 && res.data) ? res.data : (res && res.data) ? res.data : (Array.isArray(res) ? res : []);
    } else if (chatStore.currentChatType.value === 'group') {
      const res = await groupApi.getGroupChatHistory({
        groupId: targetId,
        lastTimestamp
      });
      data = (res && res.code === 1000) ? res.data : res;
    } else {
      const res = await messageApi.getChatHistory({
        friendId: targetId,
        lastTimestamp
      });
      data = (res && res.code === 1000) ? res.data : res;
    }
    return Array.isArray(data) ? data : (data?.list || []);
  };

  const formatHistoryItems = (rawList) => {
    const myId = String(userInfo.userId || '');
    return rawList.map(item => {
      const hasHumanFlag = item.isHuman !== undefined && item.isHuman !== null;
      const senderId = hasHumanFlag && !item.isHuman
        ? String(item.llmId || chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id || '')
        : String(item.sendUserId || item.sender?.userId || '');
      const msgId = item.msgId || item.id;
      const msgContent = item.msgContent || item.msg || item.content || item.groupMsg?.msg || '';
      const msgType = item.msgType || '1';
      const isMine = hasHumanFlag ? item.isHuman === true : senderId === myId;

      let matchedNickname = '';
      let matchedAvatar = '';
      if (chatStore.currentChatType.value !== 'group' && !isMine) {
        const friend = friendList.value.find(f => String(f.userId || f.id) === senderId);
        if (friend) {
          matchedNickname = friend.nickname || friend.username;
          matchedAvatar = friend.faceImage || friend.face_image;
        }
      } else if (isMine) {
        matchedNickname = userInfo.nickname || userInfo.username;
        matchedAvatar = userInfo.faceImage || userInfo.face_image;
      }

      let blocks = null;
      let emotion = null;
      let content = msgContent;
      if (msgContent) {
        try {
          const parsed = typeof msgContent === 'string' ? JSON.parse(msgContent) : msgContent;
          if (Array.isArray(parsed)) {
            blocks = parsed;
            content = null;
          } else if (parsed?.blocks && Array.isArray(parsed.blocks)) {
            blocks = parsed.blocks;
            emotion = parsed.emotion || null;
            content = null;
          }
        } catch (e) {}
      }

      return {
        id: msgId,
        content: content,
        blocks: blocks,
        emotion: emotion,
        createTime: item.createTime,
        isMine: isMine,
        type: String(msgType) === '2' ? 'image' : (String(msgType) === '3' ? 'video' : 'text'),
        isVisible: item.status !== false && item.status !== 'false',
        senderId: senderId,
        senderName: item.nickname || item.username || item.sender?.nickname || item.sender?.username || matchedNickname || senderId,
        senderAvatar: item.faceImage || item.sender?.faceImage || matchedAvatar,
        raw: item
      };
    }).filter(msg => msg.isVisible).reverse();
  };

  const getChatHistory = async (targetId, isFirstLoad = false) => {
    if (chatStore.isLoadingHistory.value || (!chatStore.hasMoreHistory.value && !isFirstLoad)) {
      return;
    }
    try {
      chatStore.isLoadingHistory.value = true;
      const rawList = await fetchHistoryPage(targetId, chatStore.lastTimestamp.value, chatStore.lastMsgId.value);
      if (rawList.length < 20) {
        chatStore.hasMoreHistory.value = false;
      }

      const formattedMsgs = formatHistoryItems(rawList);

      if (isFirstLoad) {
        chatStore.messageList.value = formattedMsgs;
        nextTick(() => scrollToBottom(true));
      } else {
        chatStore.messageList.value = [...formattedMsgs, ...chatStore.messageList.value];
      }

      if (formattedMsgs.length > 0) {
        const oldestMsg = formattedMsgs[0];
        const timestamp = toMillis(oldestMsg.createTime);
        if (!Number.isNaN(timestamp)) {
          chatStore.lastTimestamp.value = timestamp;
          chatStore.lastMsgId.value = oldestMsg.id;
        }
      }
    } catch (error) {
      console.error('加载历史记录失败:', error);
    } finally {
      chatStore.isLoadingHistory.value = false;
    }
  };

  const messageSignature = (msg) => {
    if (msg.content) return String(msg.content).trim();
    if (!Array.isArray(msg.blocks)) return '';
    return msg.blocks
      .map(block => block.type === 'action' ? `[${block.action || block.content || ''}]` : (block.text || block.content || ''))
      .filter(Boolean)
      .join('\n')
      .trim();
  };

  const isKnownMessage = (msg, knownMessages, knownIds) => {
    if (knownIds.has(String(msg.id))) return true;
    const signature = messageSignature(msg);
    if (!signature) return false;
    const msgTime = toMillis(msg.createTime);
    return knownMessages.some(existing => {
      if (existing.isMine !== msg.isMine) return false;
      if (messageSignature(existing) !== signature) return false;
      const existingTime = toMillis(existing.createTime);
      if (Number.isNaN(msgTime) || Number.isNaN(existingTime)) return true;
      return Math.abs(msgTime - existingTime) < 300000;
    });
  };

  const finalizeInterruptedStream = (newMessages = []) => {
    const stream = llmStreamState.value;
    if (!stream.active) return;
    const list = chatStore.messageList.value;
    const idx = list.findIndex(m => m.id === stream.aiPlaceholderId);
    if (idx >= 0) {
      const placeholder = list[idx];
      const placeholderTime = toMillis(placeholder.createTime);
      const hasPersistedReply = newMessages.some(msg =>
        !msg.isMine &&
        String(msg.senderId || '') === String(stream.llmId || '') &&
        !Number.isNaN(placeholderTime) &&
        toMillis(msg.createTime) >= placeholderTime
      );
      if (hasPersistedReply) {
        list.splice(idx, 1);
      } else {
        placeholder.isStreaming = false;
        placeholder.status = 'failed';
        placeholder.msgContent = stream.msgContent;
        placeholder.llmId = stream.llmId;
      }
    }
    stream.active = false;
    chatStore.isLlmTyping.value = false;
    chatStore.llmPendingCount.value = Math.max(0, chatStore.llmPendingCount.value - 1);
  };

  const syncLatestMessages = async () => {
    const targetId = chatStore.currentChatType.value === 'group'
      ? (chatStore.currentGroup.value.id || chatStore.currentGroup.value.groupId)
      : (chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id);

    if (!targetId) {
      finalizeInterruptedStream();
      return;
    }
    if (chatStore.isLoadingHistory.value) {
      finalizeInterruptedStream();
      return;
    }

    const collected = [];
    const collectedIds = new Set();
    const existingMessages = chatStore.messageList.value;
    const existingIds = new Set(existingMessages.map(m => String(m.id)));
    let cursorTime = Date.now();
    let cursorId = null;

    try {
      chatStore.isLoadingHistory.value = true;
      for (let page = 0; page < 5; page++) {
        const rawList = await fetchHistoryPage(targetId, cursorTime, cursorId);
        if (!rawList.length) break;

        const formatted = formatHistoryItems(rawList);
        let reachedKnown = false;
        for (const msg of formatted) {
          if (isKnownMessage(msg, existingMessages, existingIds) || collectedIds.has(String(msg.id))) {
            reachedKnown = true;
            continue;
          }
          collectedIds.add(String(msg.id));
          collected.push(msg);
        }

        if (reachedKnown || rawList.length < 20) break;
        const oldest = rawList[rawList.length - 1];
        const oldestTime = toMillis(oldest.createTime || oldest.tempTime);
        if (Number.isNaN(oldestTime)) break;
        cursorTime = oldestTime;
        cursorId = oldest.msgId || oldest.id;
      }

      if (collected.length) {
        const merged = [
          ...existingMessages.map((msg, index) => ({ msg, order: index, time: toMillis(msg.createTime) })),
          ...collected.map((msg, index) => ({ msg, order: existingMessages.length + index, time: toMillis(msg.createTime) }))
        ];
        merged.sort((a, b) => {
          const timeA = Number.isNaN(a.time) ? Infinity : a.time;
          const timeB = Number.isNaN(b.time) ? Infinity : b.time;
          return timeA === timeB ? a.order - b.order : timeA - timeB;
        });
        chatStore.messageList.value = merged.map(item => item.msg);
        nextTick(() => scrollToBottom(true));
      }
    } catch (error) {
      console.error('[WS] 重连后补齐消息失败:', error);
    } finally {
      finalizeInterruptedStream(collected);
      chatStore.isLoadingHistory.value = false;
    }
  };

  const loadMoreHistory = () => {
    const targetId = chatStore.currentChatType.value === 'group'
      ? (chatStore.currentGroup.value.id || chatStore.currentGroup.value.groupId)
      : (chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id);
    if (targetId) {
      getChatHistory(targetId, false);
    }
  };

  const sendMessage = async () => {
    const myId = String(userInfo.userId || '');
    const msgContent = chatStore.inputMessage.value;
    const msgId = snowflake.nextId();
    if (!chatStore.inputMessage.value.trim()) return;

    if (showRag.value) {
      const { searchRagFiles } = useRag();
      await searchRagFiles(chatStore.inputMessage.value);
      chatStore.inputMessage.value = '';
      return;
    }

    if (chatStore.currentFriend.value && (chatStore.currentFriend.value.role === 1 || chatStore.currentFriend.value.isOldFriend)) {
      const llmId = chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id;
      chatStore.messageList.value.push({
        id: msgId,
        content: msgContent,
        isMine: true,
        type: 'text',
        createTime: new Date().toISOString(),
        senderId: myId,
        senderName: userInfo.nickname || userInfo.username,
        senderAvatar: userInfo.faceImage || userInfo.face_image
      });
      chatStore.inputMessage.value = '';
      nextTick(() => scrollToBottom(true));

      chatStore.llmPendingCount.value++;
      chatStore.isLlmTyping.value = true;
      const requestFriendId = llmId;
      let aiPlaceholderId = null;
      let bubblePushed = false;

      const pushBubble = () => {
        if (bubblePushed) return;
        aiPlaceholderId = snowflake.nextId();
        chatStore.messageList.value.push({
          id: aiPlaceholderId,
          content: null,
          blocks: [{ type: 'text', text: '' }],
          emotion: null,
          isMine: false,
          type: 'text',
          isStreaming: true,
          createTime: new Date().toISOString(),
          senderId: llmId,
          senderName: chatStore.currentFriend.value.nickname || chatStore.currentFriend.value.username,
          senderAvatar: resolveAvatarUrl(chatStore.currentFriend.value.faceImage || chatStore.currentFriend.value.face_image)
        });
        bubblePushed = true;
        nextTick(() => scrollToBottom(true));
      };

      let replyBlocks = [{ type: 'text', text: '' }];
      let replyEmotion = null;
      let hasError = false;

      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        pushBubble();
        llmStreamState.value = {
          active: true,
          llmId,
          msgContent,
          aiPlaceholderId,
          blocks: [],
          currentBlockType: null,
          currentBlockContent: '',
          emotion: null,
          requestFriendId: llmId,
        };
        const wsMsg = {
          type: 1108,
          extend: JSON.stringify({ llmId, msgContent }),
        };
        sendBinaryMessage(encodeProtocol(wsMsg));
        return;
      } else {
        await sendStreamMessage(llmId, msgContent, {
          onBlocks: (blocks) => {
            if (chatStore.currentFriend.value && (chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id) !== requestFriendId) return;
            pushBubble();
            replyBlocks = blocks.map(b => {
              if (b.type === 'action') {
                return { type: 'action', action: b.content, text: null };
              } else {
                return { type: 'text', text: b.content };
              }
            });
            const idx = chatStore.messageList.value.findIndex(m => m.id === aiPlaceholderId);
            if (idx >= 0) {
              chatStore.messageList.value[idx].blocks = [...replyBlocks];
            }
            nextTick(() => scrollToBottom(true));
          },
          onEmotion: (emotion) => {
            replyEmotion = emotion;
            chatStore.currentFriend.value.emotion = emotion;
            const friend = friendList.value.find(f => String(f.userId || f.id) === String(requestFriendId));
            if (friend) friend.emotion = emotion;
          },
          onDone: () => {
            const idx = chatStore.messageList.value.findIndex(m => m.id === aiPlaceholderId);
            if (idx >= 0) {
              chatStore.messageList.value[idx].emotion = replyEmotion;
              chatStore.messageList.value[idx].isStreaming = false;
            }
            chatStore.isLlmTyping.value = false;
            chatStore.llmPendingCount.value--;
          },
          onError: (err) => {
            console.warn('[SSE] 流失败，降级 REST:', err);
            hasError = true;
            chatStore.isLlmTyping.value = false;
            chatStore.llmPendingCount.value--;
            fallbackLlmRest(llmId, msgContent, chatStore.currentFriend, friendList, chatStore.messageList, bubblePushed ? aiPlaceholderId : null);
          },
        });
        if (hasError) return;
        return;
      }
    }

    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      FoxToast.error('连接已断开，正在重连，请稍后重试');
      return;
    }

    try {
      if (chatStore.currentChatType.value === 'private') {
        const targetFriend = chatStore.currentFriend.value;
        const targetId = targetFriend.userId || targetFriend.id;
        if (!targetId) {
          FoxToast.warning('请先选择好友');
          return;
        }
        const chatData = {
          type: 1101,
          targetType: 1,
          chatMsg: {
            id: msgId,
            sender: { userId: myId },
            acceptUserId: String(targetId),
            msg: msgContent
          },
          extend: ""
        };
        const binaryData = encodeProtocol(chatData);
        sendBinaryMessage(binaryData);
        chatStore.messageList.value.push({
          id: msgId,
          content: msgContent,
          isMine: true,
          type: 'text',
          createTime: new Date().toISOString(),
          senderId: myId,
          senderName: userInfo.nickname || userInfo.username,
          senderAvatar: userInfo.faceImage || userInfo.face_image
        });
        chatStore.inputMessage.value = '';
        nextTick(() => scrollToBottom(true));
      } else if (chatStore.currentChatType.value === 'group') {
        const targetGroup = chatStore.currentGroup.value;
        const groupId = targetGroup.groupId || targetGroup.id;
        if (!groupId) {
          FoxToast.warning('请先选择群组');
          return;
        }
        const groupData = {
          type: 1201,
          targetType: 2,
          groupMsg: {
            id: msgId,
            groupId: String(targetGroup.id),
            sender: {
              userId: myId,
              username: userInfo.username || '',
              nickname: userInfo.nickname || '',
              faceImage: userInfo.faceImage || userInfo.face_image || ''
            },
            msg: msgContent,
            msgType: '1',
            createTime: String(Date.now())
          }
        };
        const binaryData = encodeProtocol(groupData);
        sendBinaryMessage(binaryData);
        chatStore.messageList.value.push({
          id: msgId,
          content: msgContent,
          isMine: true,
          type: 'text',
          createTime: new Date().toISOString(),
          senderId: myId,
          senderName: userInfo.nickname || userInfo.username,
          senderAvatar: userInfo.faceImage || userInfo.face_image
        });
        chatStore.inputMessage.value = '';
        nextTick(() => scrollToBottom(true));
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      FoxToast.error('发送失败');
    }
  };

  const retryLlmMessage = async (failedMsg) => {
    const originalContent = failedMsg.msgContent;
    const llmId = failedMsg.llmId;
    chatStore.messageList.value = chatStore.messageList.value.filter(m => m.id !== failedMsg.id);
    const placeholderId = 'retry-' + Date.now();
    chatStore.messageList.value.push({
      id: placeholderId,
      content: '思考中...',
      status: 'thinking',
      isMine: false,
      createTime: new Date().toISOString(),
      senderId: llmId,
      senderName: chatStore.currentFriend.value.nickname || chatStore.currentFriend.value.username,
      senderAvatar: resolveAvatarUrl(chatStore.currentFriend.value.faceImage || chatStore.currentFriend.value.face_image)
    });
    nextTick(() => scrollToBottom(true));
    chatStore.isLlmTyping.value = true;
    try {
      const res = await request.post('/llm/chat', {
        llmId: llmId,
        msgContent: originalContent
      }, { silent: true, timeout: 120000 });
      let actualResponse = res;
      if (res && res.code === 1000 && res.data) {
        actualResponse = res.data;
      }
      let replyBlocks = null;
      let replyEmotion = null;
      if (Array.isArray(actualResponse)) {
        const aiMsg = actualResponse.find(m => m.isHuman === false);
        if (aiMsg && aiMsg.msgContent) {
          try {
            const parsed = JSON.parse(aiMsg.msgContent);
            replyBlocks = parsed.blocks || (Array.isArray(parsed) ? parsed : [{ type: 'text', text: aiMsg.msgContent }]);
            replyEmotion = parsed.emotion;
          } catch (e) {
            replyBlocks = [{ type: 'text', text: aiMsg.msgContent }];
          }
        }
      } else if (actualResponse && typeof actualResponse === 'string') {
        replyBlocks = [{ type: 'text', text: actualResponse }];
      } else if (actualResponse && actualResponse.msg) {
        try {
          const parsed = typeof actualResponse.msg === 'string' ? JSON.parse(actualResponse.msg) : actualResponse.msg;
          replyBlocks = parsed?.blocks || (Array.isArray(parsed) ? parsed : [{ type: 'text', text: actualResponse.msg }]);
          replyEmotion = parsed?.emotion;
        } catch (e) {
          replyBlocks = [{ type: 'text', text: actualResponse.msg }];
        }
      }
      chatStore.messageList.value = chatStore.messageList.value.filter(m => m.id !== placeholderId);
      if (chatStore.currentFriend.value && (chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id) === llmId) {
        chatStore.messageList.value.push({
          id: snowflake.nextId(),
          content: null,
          blocks: replyBlocks || [{ type: 'text', text: actualResponse?.msg || '回复成功' }],
          emotion: replyEmotion,
          isMine: false,
          createTime: new Date().toISOString(),
          senderId: llmId,
          senderName: chatStore.currentFriend.value.nickname || chatStore.currentFriend.value.username,
          senderAvatar: resolveAvatarUrl(chatStore.currentFriend.value.faceImage || chatStore.currentFriend.value.face_image)
        });
      }
      nextTick(() => scrollToBottom(true));
    } catch (error) {
      console.error('重试 LLM 请求失败:', error);
      chatStore.messageList.value = chatStore.messageList.value.filter(m => m.id !== placeholderId);
      if (chatStore.currentFriend.value && (chatStore.currentFriend.value.userId || chatStore.currentFriend.value.id) === llmId) {
        chatStore.messageList.value.push({
          id: 'failed-' + Date.now(),
          content: '回复失败，点击重试',
          status: 'failed',
          msgContent: originalContent,
          llmId: llmId,
          isMine: false,
          createTime: new Date().toISOString(),
          senderId: llmId,
          senderName: chatStore.currentFriend.value.nickname || chatStore.currentFriend.value.username,
          senderAvatar: resolveAvatarUrl(chatStore.currentFriend.value.faceImage || chatStore.currentFriend.value.face_image)
        });
      }
    } finally {
      chatStore.isLlmTyping.value = false;
    }
  };

  const handleWithdrawMessages = async () => {
    if (chatStore.selectedMessageIds.value.length === 0) return;
    try {
      await messageApi.withdrawMessages(chatStore.selectedMessageIds.value.map(String));
      FoxToast.success('消息撤回成功');
      chatStore.selectedMessageIds.value.forEach(id => {
        const msg = chatStore.messageList.value.find(m => m.id === id);
        if (msg) {
          msg.isWithdrawn = true;
          msg.type = 'system';
        }
      });
      cancelSelectionMode();
    } catch (error) {
      console.error('撤回消息失败:', error);
    }
  };

  const handleDeleteMessages = async () => {
    if (chatStore.selectedMessageIds.value.length === 0) return;
    try {
      await messageApi.deleteMessages(chatStore.selectedMessageIds.value.map(String));
      FoxToast.success('消息删除成功');
      chatStore.messageList.value = chatStore.messageList.value.filter(msg => !chatStore.selectedMessageIds.value.includes(msg.id));
      cancelSelectionMode();
    } catch (error) {
      console.error('删除消息失败:', error);
    }
  };

  const toggleSelectionMode = () => {
    chatStore.isSelectionMode.value = true;
    chatStore.selectedMessageIds.value = [];
    chatStore.messageList.value.forEach(msg => {
      if (msg.isMine) msg.selected = false;
    });
  };

  const cancelSelectionMode = () => {
    chatStore.isSelectionMode.value = false;
    chatStore.selectedMessageIds.value = [];
    chatStore.messageList.value.forEach(msg => msg.selected = false);
  };

  return {
    llmStreamState,
    handleLlmToken,
    scrollToBottom,
    getChatHistory,
    syncLatestMessages,
    loadMoreHistory,
    sendMessage,
    retryLlmMessage,
    handleWithdrawMessages,
    handleDeleteMessages,
    toggleSelectionMode,
    cancelSelectionMode
  };
}
